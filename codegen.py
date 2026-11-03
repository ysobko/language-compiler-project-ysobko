from ast_nodes import InlineBlockNode
from llvmlite import ir

from ast_nodes import (
    ProgramNode,
    FunctionDeclNode,
    MutableDeclNode,
    ImmutableDeclNode,
    ConstantDeclNode,
    ReturnNode,
    IntegerNode,
    BinaryOpNode,
    BooleanNode,
    IdentifierNode,
    AssignmentNode,
    FunctionCallNode,
    ComparisonNode,
    IfNode,
    ObjectCreationNode,
    FieldAccessNode,
    MemberCallNode,
    StructDeclNode,
    ExpressionStmtNode,
    ScanNode,
    PrintNode,
    StringNode,
)
from symbols import SymbolTable


I32 = "🟢"
I64 = "🛣️"
BOOL = "🚦"


class LLVMCodeGenerator:
    def __init__(self, symbols: SymbolTable):
        self.symbols = symbols
        self.module = ir.Module(name="traffica", context=ir.Context())
        import subprocess
        self.module.triple = subprocess.check_output(
            ["llvm-config", "--host-target"],
            text=True
        ).strip()

        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i1 = ir.IntType(1)
        self.i8 = ir.IntType(8)
        self.i8p = self.i8.as_pointer()

        self.struct_types = {}
        self.functions = {}
        self.member_functions = {}
        self.global_variables = {}

        self.scanf = None
        self.printf = None

        self.fmt_int = None
        self.fmt_print_i32 = None
        self.fmt_print_i64 = None
        self.fmt_print_string = None
        self.fmt_raw_string = None
        self.fmt_raw_i32 = None
        self.fmt_raw_i64 = None
        self.bool_true_string = None
        self.bool_false_string = None
        self.string_counter = 0

        self.builder = None
        self.local_variables = {}
        self.local_variable_types = {}
        self.current_result_type = None
        self.current_structure = None
        self.current_object_pointer = None

    def llvm_type(self, type_name: str):
        if type_name == I32:
            return self.i32

        if type_name == I64:
            return self.i64

        if type_name == BOOL:
            return self.i1

        structure = self.symbols.get_structure(type_name)

        if structure is not None:
            return self.module.context.get_identified_type(
                f"traffica.struct.{type_name}"
            )

        raise ValueError(f"unknown type: {type_name}")

    def declare_structures(self):
        # First create every identified type by name.
        # This allows a field to refer to a structure declared later.
        for structure in self.symbols.structures.values():
            self.struct_types[structure.name] = (
                self.module.context.get_identified_type(
                    f"traffica.struct.{structure.name}"
                )
            )

        # Then give each structure its ordered field layout.
        for structure in self.symbols.structures.values():
            llvm_struct = self.struct_types[structure.name]

            field_types = [
                self.llvm_type(field.type_name)
                for field in structure.fields
            ]

            llvm_struct.set_body(*field_types)

    def create_c_string(self, name, value: bytes):
        data = bytearray(value + b"\x00")
        array_type = ir.ArrayType(self.i8, len(data))

        global_string = ir.GlobalVariable(
            self.module,
            array_type,
            name=name
        )

        global_string.linkage = "internal"
        global_string.global_constant = True
        global_string.initializer = ir.Constant(
            array_type,
            data
        )

        zero = ir.Constant(self.i32, 0)

        return global_string.gep(
            [zero, zero]
        )

    def declare_runtime(self):
        # int scanf(const char *fmt, ...)
        c_function_type = ir.FunctionType(
            self.i32,
            [self.i8p],
            var_arg=True
        )

        self.scanf = ir.Function(
            self.module,
            c_function_type,
            name="scanf"
        )

        # Global C string "%d\0".
        format_bytes = bytearray(b"%d\x00")

        format_type = ir.ArrayType(
            self.i8,
            len(format_bytes)
        )

        format_global = ir.GlobalVariable(
            self.module,
            format_type,
            name="traffica_fmt_int"
        )

        format_global.linkage = "internal"
        format_global.global_constant = True
        format_global.initializer = ir.Constant(
            format_type,
            format_bytes
        )

        zero = ir.Constant(self.i32, 0)

        self.fmt_int = format_global.gep(
            [zero, zero]
        )

        # int printf(const char *fmt, ...)
        self.printf = ir.Function(
            self.module,
            c_function_type,
            name="printf"
        )

        # Integer output formats include exactly one newline.
        self.fmt_print_i32 = self.create_c_string(
            "traffica_fmt_print_i32",
            b"%d\n"
        )

        self.fmt_print_i64 = self.create_c_string(
            "traffica_fmt_print_i64",
            b"%lld\n"
        )

        self.fmt_print_string = self.create_c_string(
            "traffica_fmt_print_string",
            b"%s\n"
        )

        # Formats without a newline are used while building
        # one complete object representation.
        self.fmt_raw_string = self.create_c_string(
            "traffica_fmt_raw_string",
            b"%s"
        )

        self.fmt_raw_i32 = self.create_c_string(
            "traffica_fmt_raw_i32",
            b"%d"
        )

        self.fmt_raw_i64 = self.create_c_string(
            "traffica_fmt_raw_i64",
            b"%lld"
        )

        self.bool_true_string = self.create_c_string(
            "traffica_bool_true",
            b"true"
        )

        self.bool_false_string = self.create_c_string(
            "traffica_bool_false",
            b"false"
        )

    def declare_global_variables(self):
        for symbol in self.symbols.global_scope.variables.values():
            llvm_type = self.llvm_type(symbol.type_name)

            global_variable = ir.GlobalVariable(
                self.module,
                llvm_type,
                name=f"traffica_global_{symbol.name}"
            )

            # Initial values are assigned at runtime in main.
            global_variable.initializer = ir.Constant(
                llvm_type,
                None
            )

            self.global_variables[symbol.name] = global_variable

    def declare_functions(self):
        for function in self.symbols.functions.values():
            parameter_types = [
                self.llvm_type(type_name)
                for type_name in function.parameter_types
            ]

            result_type = self.llvm_type(function.result_type)

            function_type = ir.FunctionType(
                result_type,
                parameter_types
            )

            llvm_function = ir.Function(
                self.module,
                function_type,
                name=f"traffica_{function.name}"
            )

            self.functions[function.name] = llvm_function

    def declare_member_functions(self):
        for structure in self.symbols.structures.values():
            object_type = self.struct_types[structure.name]

            for member in structure.member_functions.values():
                parameter_types = [
                    object_type.as_pointer()
                ]

                parameter_types.extend(
                    self.llvm_type(type_name)
                    for type_name in member.parameter_types
                )

                result_type = self.llvm_type(member.result_type)

                function_type = ir.FunctionType(
                    result_type,
                    parameter_types
                )

                llvm_function = ir.Function(
                    self.module,
                    function_type,
                    name=f"traffica_{structure.name}_{member.name}"
                )

                self.member_functions[
                    (structure.name, member.name)
                ] = llvm_function

    def current_field(self, name):
        if self.current_structure is None:
            return None

        return self.current_structure.get_field(name)

    def current_field_pointer(self, field):
        zero = ir.Constant(self.i32, 0)
        index = ir.Constant(self.i32, field.index)

        return self.builder.gep(
            self.current_object_pointer,
            [zero, index],
            inbounds=True,
            name=f"self.{field.name}.ptr"
        )

    def expression_type_name(self, node):
        if isinstance(node, IntegerNode):
            if -(2 ** 31) <= node.value <= 2 ** 31 - 1:
                return I32
            return I64

        if isinstance(node, BinaryOpNode):
            left_type = self.expression_type_name(node.left)
            right_type = self.expression_type_name(node.right)

            # An expression containing an i64 operand
            # must use i64 arithmetic.
            if left_type == I64 or right_type == I64:
                return I64

            # Constant arithmetic may produce a value
            # that does not fit in i32.
            def constant_value(expr):
                if isinstance(expr, IntegerNode):
                    return expr.value

                if isinstance(expr, BinaryOpNode):
                    left = constant_value(expr.left)
                    right = constant_value(expr.right)

                    if left is None or right is None:
                        return None

                    if expr.operator == "+":
                        return left + right
                    if expr.operator == "-":
                        return left - right
                    if expr.operator == "*":
                        return left * right

                return None

            result = constant_value(node)

            if result is not None and not (
                -(2 ** 31) <= result <= 2 ** 31 - 1
            ):
                return I64

            return I32

        if isinstance(node, BooleanNode):
            return BOOL

        if isinstance(node, IdentifierNode):
            # 1. Locals and parameters.
            if node.name in self.local_variable_types:
                return self.local_variable_types[node.name]

            # 2. Fields inside a member function.
            field = self.current_field(node.name)

            if field is not None:
                return field.type_name

            # 3. Global variables.
            global_symbol = (
                self.symbols.global_scope.variables.get(
                    node.name
                )
            )

            if global_symbol is not None:
                return global_symbol.type_name

            raise KeyError(
                f"no type found for name '{node.name}'"
            )

        if isinstance(node, FunctionCallNode):
            # Inside a member function, bare member functions
            # have priority over global functions.
            if self.current_structure is not None:
                member = self.current_structure.member_functions.get(
                    node.name
                )

                if member is not None:
                    return member.result_type

            function = self.symbols.get_function(node.name)

            if function is None:
                raise KeyError(
                    f"function '{node.name}' was not found"
                )

            return function.result_type

        if isinstance(node, ObjectCreationNode):
            return node.type_name

        if isinstance(node, FieldAccessNode):
            object_type = self.expression_type_name(node.object)
            structure = self.symbols.get_structure(object_type)

            if structure is None:
                raise KeyError(
                    f"type '{object_type}' is not a structure"
                )

            field = structure.get_field(node.field_name)

            if field is None:
                raise KeyError(
                    f"field '{node.field_name}' was not found"
                )

            return field.type_name

        if isinstance(node, MemberCallNode):
            object_type = self.expression_type_name(node.object)
            structure = self.symbols.get_structure(object_type)

            if structure is None:
                raise KeyError(
                    f"type '{object_type}' is not a structure"
                )

            member = structure.member_functions.get(
                node.member_name
            )

            if member is None:
                raise KeyError(
                    f"member function '{node.member_name}' "
                    f"was not found"
                )

            return member.result_type

        if isinstance(node, ComparisonNode):
            return BOOL

        if isinstance(node, ScanNode):
            return I32

        raise NotImplementedError(
            f"type lookup for {type(node).__name__} "
            f"is not implemented"
        )

    def generate_field_pointer(self, node: FieldAccessNode):
        if isinstance(node.object, IdentifierNode):
            # Local/parameter object.
            if node.object.name in self.local_variables:
                object_pointer = self.local_variables[
                    node.object.name
                ]
                object_type_name = self.local_variable_types[
                    node.object.name
                ]

            elif node.object.name in self.global_variables:
                object_pointer = self.global_variables[
                    node.object.name
                ]
                object_type_name = self.symbols.global_scope.variables[
                    node.object.name
                ].type_name

            else:
                field = self.current_field(node.object.name)

                if field is None:
                    raise KeyError(
                        f"no object storage found for "
                        f"'{node.object.name}'"
                    )

                object_pointer = self.current_field_pointer(field)
                object_type_name = field.type_name

        elif isinstance(node.object, FieldAccessNode):
            object_pointer = self.generate_field_pointer(
                node.object
            )
            object_type_name = self.expression_type_name(
                node.object
            )

        else:
            raise NotImplementedError(
                "field access currently requires an "
                "addressable object"
            )

        structure = self.symbols.get_structure(
            object_type_name
        )

        if structure is None:
            raise KeyError(
                f"type '{object_type_name}' is not a structure"
            )

        field = structure.get_field(node.field_name)

        if field is None:
            raise KeyError(
                f"field '{node.field_name}' was not found"
            )

        zero = ir.Constant(self.i32, 0)
        field_index = ir.Constant(self.i32, field.index)

        return self.builder.gep(
            object_pointer,
            [zero, field_index],
            inbounds=True,
            name=f"field.{node.field_name}.ptr"
        )

    def generate_binary_operation(self, node, expected_type=None):
        if expected_type in (I32, I64):
            result_type = expected_type
        else:
            result_type = self.expression_type_name(node)

        llvm_type = self.llvm_type(result_type)

        left = self.generate_expression(
            node.left,
            expected_type=result_type
        )

        right = self.generate_expression(
            node.right,
            expected_type=result_type
        )

        operations = {
            "+": "sadd",
            "-": "ssub",
            "*": "smul",
        }

        operation = operations[node.operator]
        width = llvm_type.width

        intrinsic_name = (
            f"llvm.{operation}.with.overflow.i{width}"
        )

        intrinsic = self.module.globals.get(intrinsic_name)

        if intrinsic is None:
            result_struct = ir.LiteralStructType([
                llvm_type,
                self.i1
            ])

            intrinsic_type = ir.FunctionType(
                result_struct,
                [llvm_type, llvm_type]
            )

            intrinsic = ir.Function(
                self.module,
                intrinsic_type,
                name=intrinsic_name
            )

        pair = self.builder.call(
            intrinsic,
            [left, right],
            name="arithmetic.checked"
        )

        result = self.builder.extract_value(
            pair,
            0,
            name="arithmetic.result"
        )

        overflow = self.builder.extract_value(
            pair,
            1,
            name="arithmetic.overflow"
        )

        function = self.builder.function

        error_block = function.append_basic_block(
            "arithmetic.overflow.error"
        )

        continue_block = function.append_basic_block(
            "arithmetic.continue"
        )

        self.builder.cbranch(
            overflow,
            error_block,
            continue_block
        )

        self.builder.position_at_end(error_block)

        abort_function = self.module.globals.get("abort")

        if abort_function is None:
            abort_function = ir.Function(
                self.module,
                ir.FunctionType(ir.VoidType(), []),
                name="abort"
            )

        self.builder.call(abort_function, [])
        self.builder.unreachable()

        self.builder.position_at_end(continue_block)

        return result

    def generate_expression(self, node, expected_type=None):
        if isinstance(node, BinaryOpNode):
            return self.generate_binary_operation(
                node,
                expected_type
            )

        if isinstance(node, IntegerNode):
            if expected_type == I64:
                return ir.Constant(self.i64, node.value)

            return ir.Constant(self.i32, node.value)

        if isinstance(node, BooleanNode):
            return ir.Constant(
                self.i1,
                int(node.value)
            )

        if isinstance(node, IdentifierNode):
            # Locals/parameters first.
            if node.name in self.local_variables:
                pointer = self.local_variables[node.name]

                return self.builder.load(
                    pointer,
                    name=f"{node.name}.value"
                )

            # Then fields of the current object.
            field = self.current_field(node.name)

            if field is not None:
                pointer = self.current_field_pointer(field)

                return self.builder.load(
                    pointer,
                    name=f"self.{node.name}.value"
                )

            # Finally global variables.
            if node.name in self.global_variables:
                pointer = self.global_variables[node.name]

                return self.builder.load(
                    pointer,
                    name=f"{node.name}.global.value"
                )

            raise KeyError(
                f"no storage found for name '{node.name}'"
            )

        if isinstance(node, FunctionCallNode):
            # Inside a member function, a bare call first
            # resolves to a member of the same structure.
            if self.current_structure is not None:
                member = (
                    self.current_structure.member_functions.get(
                        node.name
                    )
                )

                if member is not None:
                    llvm_function = self.member_functions[
                        (
                            self.current_structure.name,
                            node.name
                        )
                    ]

                    # Hidden first argument is self.
                    arguments = [
                        self.current_object_pointer
                    ]

                    for argument, parameter_type in zip(
                        node.arguments,
                        member.parameter_types
                    ):
                        arguments.append(
                            self.generate_expression(
                                argument,
                                expected_type=parameter_type
                            )
                        )

                    return self.builder.call(
                        llvm_function,
                        arguments,
                        name=f"call.member.{node.name}"
                    )

            # Otherwise it is a global function.
            function_symbol = self.symbols.get_function(
                node.name
            )

            llvm_function = self.functions[node.name]

            arguments = []

            for argument, parameter_type in zip(
                node.arguments,
                function_symbol.parameter_types
            ):
                arguments.append(
                    self.generate_expression(
                        argument,
                        expected_type=parameter_type
                    )
                )

            return self.builder.call(
                llvm_function,
                arguments,
                name=f"call.{node.name}"
            )

        if isinstance(node, ComparisonNode):
            left_type = self.expression_type_name(
                node.left
            )
            right_type = self.expression_type_name(
                node.right
            )

            left_expected = None
            right_expected = None

            # Preserve i64 width when one side gives us
            # the contextual integer type.
            if left_type == I64 or right_type == I64:
                left_expected = I64
                right_expected = I64

            left = self.generate_expression(
                node.left,
                expected_type=left_expected
            )

            right = self.generate_expression(
                node.right,
                expected_type=right_expected
            )

            if node.operator == "≡":
                return self.builder.icmp_signed(
                    "==",
                    left,
                    right,
                    name="compare.eq"
                )

            if node.operator == "≠":
                return self.builder.icmp_signed(
                    "!=",
                    left,
                    right,
                    name="compare.ne"
                )

            raise ValueError(
                f"unknown comparison operator: "
                f"{node.operator}"
            )

        if isinstance(node, ObjectCreationNode):
            structure = self.symbols.get_structure(
                node.type_name
            )

            llvm_struct_type = self.struct_types[
                node.type_name
            ]

            object_pointer = self.builder.alloca(
                llvm_struct_type,
                name=f"{node.type_name}.object"
            )

            zero = ir.Constant(self.i32, 0)

            for field, value_node in zip(
                structure.fields,
                node.values
            ):
                field_pointer = self.builder.gep(
                    object_pointer,
                    [
                        zero,
                        ir.Constant(
                            self.i32,
                            field.index
                        )
                    ],
                    inbounds=True,
                    name=(
                        f"{node.type_name}."
                        f"{field.name}.ptr"
                    )
                )

                value = self.generate_expression(
                    value_node,
                    expected_type=field.type_name
                )

                self.builder.store(
                    value,
                    field_pointer
                )

            return self.builder.load(
                object_pointer,
                name=f"{node.type_name}.value"
            )

        if isinstance(node, FieldAccessNode):
            pointer = self.generate_field_pointer(node)

            return self.builder.load(
                pointer,
                name=f"field.{node.field_name}.value"
            )

        if isinstance(node, MemberCallNode):
            object_type = self.expression_type_name(
                node.object
            )

            structure = self.symbols.get_structure(
                object_type
            )

            member = structure.member_functions[
                node.member_name
            ]

            if isinstance(node.object, IdentifierNode):
                if node.object.name in self.local_variables:
                    object_pointer = self.local_variables[
                        node.object.name
                    ]
                elif node.object.name in self.global_variables:
                    object_pointer = self.global_variables[
                        node.object.name
                    ]

                else:
                    field = self.current_field(
                        node.object.name
                    )

                    if field is None:
                        raise KeyError(
                            f"no object storage found for "
                            f"'{node.object.name}'"
                        )

                    object_pointer = (
                        self.current_field_pointer(field)
                    )

            elif isinstance(node.object, FieldAccessNode):
                object_pointer = self.generate_field_pointer(
                    node.object
                )

            else:
                raise NotImplementedError(
                    "member call currently requires an "
                    "addressable object"
                )

            llvm_function = self.member_functions[
                (
                    structure.name,
                    node.member_name
                )
            ]

            arguments = [object_pointer]

            for argument, parameter_type in zip(
                node.arguments,
                member.parameter_types
            ):
                arguments.append(
                    self.generate_expression(
                        argument,
                        expected_type=parameter_type
                    )
                )

            return self.builder.call(
                llvm_function,
                arguments,
                name=(
                    f"call.{structure.name}."
                    f"{node.member_name}"
                )
            )

        if isinstance(node, ScanNode):
            # scanf needs an address where it can write the integer.
            slot = self.builder.alloca(
                self.i32,
                name="scan.slot"
            )

            self.builder.call(
                self.scanf,
                [
                    self.fmt_int,
                    slot
                ]
            )

            return self.builder.load(
                slot,
                name="scan.value"
            )

        raise NotImplementedError(
            f"code generation for expression "
            f"{type(node).__name__} is not implemented"
        )

    def generate_local_declaration(self, node):
        llvm_type = self.llvm_type(node.type_name)

        pointer = self.builder.alloca(
            llvm_type,
            name=node.name
        )

        value = self.generate_expression(
            node.value,
            expected_type=node.type_name
        )

        self.builder.store(value, pointer)
        self.local_variables[node.name] = pointer
        self.local_variable_types[node.name] = node.type_name

    def generate_if(self, node: IfNode):
        condition = self.generate_expression(node.condition)
        function = self.builder.function

        then_block = function.append_basic_block("check.then")

        if node.else_body is not None:
            else_block = function.append_basic_block("check.detour")
            end_block = function.append_basic_block("check.end")

            self.builder.cbranch(
                condition,
                then_block,
                else_block
            )

            # Save the variables visible before entering either branch.
            outer_variables = self.local_variables.copy()
            outer_types = self.local_variable_types.copy()

            # Then branch has its own scope.
            self.builder.position_at_end(then_block)
            self.local_variables = outer_variables.copy()
            self.local_variable_types = outer_types.copy()

            for statement in node.then_body:
                if self.builder.block.is_terminated:
                    break
                self.generate_statement(statement)

            then_terminated = self.builder.block.is_terminated

            if not then_terminated:
                self.builder.branch(end_block)

            # Detour branch has a separate scope.
            self.builder.position_at_end(else_block)
            self.local_variables = outer_variables.copy()
            self.local_variable_types = outer_types.copy()

            for statement in node.else_body:
                if self.builder.block.is_terminated:
                    break
                self.generate_statement(statement)

            else_terminated = self.builder.block.is_terminated

            if not else_terminated:
                self.builder.branch(end_block)

            # Restore the outer scope.
            self.local_variables = outer_variables
            self.local_variable_types = outer_types

            if then_terminated and else_terminated:
                self.builder.position_at_end(end_block)
                self.builder.unreachable()
            else:
                self.builder.position_at_end(end_block)

            return

        # A check without detour still needs a continuation.
        end_block = function.append_basic_block("check.end")

        self.builder.cbranch(
            condition,
            then_block,
            end_block
        )

        outer_variables = self.local_variables.copy()
        outer_types = self.local_variable_types.copy()

        self.builder.position_at_end(then_block)

        for statement in node.then_body:
            if self.builder.block.is_terminated:
                break
            self.generate_statement(statement)

        if not self.builder.block.is_terminated:
            self.builder.branch(end_block)

        # Variables declared inside the branch are no longer visible.
        self.local_variables = outer_variables
        self.local_variable_types = outer_types

        self.builder.position_at_end(end_block)

    def print_text_fragment(self, text: str):
        name = (
            f"traffica_string_{self.string_counter}"
        )
        self.string_counter += 1

        pointer = self.create_c_string(
            name,
            text.encode("utf-8")
        )

        self.builder.call(
            self.printf,
            [
                self.fmt_raw_string,
                pointer
            ]
        )

    def generate_object_print(self, node, type_name):
        structure = self.symbols.get_structure(type_name)

        if structure is None:
            raise KeyError(
                f"type '{type_name}' is not a structure"
            )

        # Materialize the object in memory so every field
        # can be reached by GEP using its symbol-table index.
        object_value = self.generate_expression(
            node,
            expected_type=type_name
        )

        object_pointer = self.builder.alloca(
            self.llvm_type(type_name),
            name=f"print.{type_name}.object"
        )

        self.builder.store(
            object_value,
            object_pointer
        )

        self.print_text_fragment(
            f"{type_name}{{"
        )

        zero = ir.Constant(self.i32, 0)

        for position, field in enumerate(structure.fields):
            if position > 0:
                self.print_text_fragment(", ")

            self.print_text_fragment(
                f"{field.name}="
            )

            field_index = ir.Constant(
                self.i32,
                field.index
            )

            field_pointer = self.builder.gep(
                object_pointer,
                [zero, field_index],
                inbounds=True,
                name=f"print.{field.name}.ptr"
            )

            field_value = self.builder.load(
                field_pointer,
                name=f"print.{field.name}.value"
            )

            if field.type_name == I32:
                self.builder.call(
                    self.printf,
                    [
                        self.fmt_raw_i32,
                        field_value
                    ]
                )

            elif field.type_name == I64:
                self.builder.call(
                    self.printf,
                    [
                        self.fmt_raw_i64,
                        field_value
                    ]
                )

            elif field.type_name == BOOL:
                text_pointer = self.builder.select(
                    field_value,
                    self.bool_true_string,
                    self.bool_false_string,
                    name=f"print.{field.name}.bool"
                )

                self.builder.call(
                    self.printf,
                    [
                        self.fmt_raw_string,
                        text_pointer
                    ]
                )

            else:
                raise NotImplementedError(
                    f"printing nested field type "
                    f"'{field.type_name}' is not implemented yet"
                )

        # Only the end of the whole object gets a newline.
        self.print_text_fragment("}")

        newline = self.create_c_string(
            f"traffica_string_{self.string_counter}",
            b"\n"
        )
        self.string_counter += 1

        self.builder.call(
            self.printf,
            [
                self.fmt_raw_string,
                newline
            ]
        )

    def generate_print(self, node: PrintNode):
        # String literals are allowed specifically by print.
        # The language does not have a general string type.
        if isinstance(node.value, StringNode):
            name = (
                f"traffica_string_{self.string_counter}"
            )
            self.string_counter += 1

            string_pointer = self.create_c_string(
                name,
                node.value.value.encode("utf-8")
            )

            self.builder.call(
                self.printf,
                [
                    self.fmt_print_string,
                    string_pointer
                ]
            )
            return

        value_type = self.expression_type_name(
            node.value
        )

        if value_type == I32:
            value = self.generate_expression(
                node.value,
                expected_type=I32
            )

            self.builder.call(
                self.printf,
                [
                    self.fmt_print_i32,
                    value
                ]
            )
            return

        if value_type == I64:
            value = self.generate_expression(
                node.value,
                expected_type=I64
            )

            self.builder.call(
                self.printf,
                [
                    self.fmt_print_i64,
                    value
                ]
            )
            return

        if value_type == BOOL:
            value = self.generate_expression(
                node.value,
                expected_type=BOOL
            )

            # Choose "true" or "false" from the i1 value.
            text_pointer = self.builder.select(
                value,
                self.bool_true_string,
                self.bool_false_string,
                name="bool.text"
            )

            self.builder.call(
                self.printf,
                [
                    self.fmt_print_string,
                    text_pointer
                ]
            )
            return

        if self.symbols.get_structure(value_type) is not None:
            self.generate_object_print(
                node.value,
                value_type
            )
            return

        raise NotImplementedError(
            f"printing type '{value_type}' "
            f"is not implemented yet"
        )

    def generate_statement(self, node):
        if isinstance(node, InlineBlockNode):
            previous_variables = self.local_variables.copy()
            previous_types = self.local_variable_types.copy()

            try:
                for statement in node.statements:
                    if self.builder.block.is_terminated:
                        break
                    self.generate_statement(statement)
            finally:
                self.local_variables = previous_variables
                self.local_variable_types = previous_types

            return
        if isinstance(node, PrintNode):
            self.generate_print(node)
            return

        if isinstance(
            node,
            (MutableDeclNode, ImmutableDeclNode, ConstantDeclNode)
        ):
            self.generate_local_declaration(node)
            return

        if isinstance(node, ReturnNode):
            value = self.generate_expression(
                node.value,
                expected_type=self.current_result_type
            )
            self.builder.ret(value)
            return

        if isinstance(node, AssignmentNode):
            if isinstance(node.target, IdentifierNode):
                if node.target.name in self.local_variables:
                    pointer = self.local_variables[node.target.name]
                else:
                    field = self.current_field(node.target.name)

                    if field is not None:
                        pointer = self.current_field_pointer(field)

                    elif node.target.name in self.global_variables:
                        pointer = self.global_variables[
                            node.target.name
                        ]

                    else:
                        raise KeyError(
                            f"no storage found for name "
                            f"'{node.target.name}'"
                        )

                expected_type = None
                pointee_type = pointer.type.pointee

                if pointee_type == self.i32:
                    expected_type = I32
                elif pointee_type == self.i64:
                    expected_type = I64
                elif pointee_type == self.i1:
                    expected_type = BOOL

                value = self.generate_expression(
                    node.value,
                    expected_type=expected_type
                )

                self.builder.store(value, pointer)
                return

            if isinstance(node.target, FieldAccessNode):
                pointer = self.generate_field_pointer(node.target)
                target_type = self.expression_type_name(node.target)

                value = self.generate_expression(
                    node.value,
                    expected_type=target_type
                )

                self.builder.store(value, pointer)
                return

        if isinstance(node, IfNode):
            self.generate_if(node)
            return

        if isinstance(node, ExpressionStmtNode):
            self.generate_expression(node.expression)
            return

        raise NotImplementedError(
            f"code generation for statement "
            f"{type(node).__name__} is not implemented"
        )

    def generate_global_initialization(self, node):
        pointer = self.global_variables[node.name]

        value = self.generate_expression(
            node.value,
            expected_type=node.type_name
        )

        self.builder.store(value, pointer)

    def generate_main(self, program: ProgramNode):
        main_type = ir.FunctionType(
            self.i32,
            []
        )

        main_function = ir.Function(
            self.module,
            main_type,
            name="main"
        )

        entry = main_function.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)

        self.local_variables = {}
        self.local_variable_types = {}
        self.current_result_type = None
        self.current_structure = None
        self.current_object_pointer = None

        for statement in program.statements:
            if self.builder.block.is_terminated:
                break

            # Declarations at top level initialize LLVM globals.
            if isinstance(
                statement,
                (
                    MutableDeclNode,
                    ImmutableDeclNode,
                    ConstantDeclNode
                )
            ):
                self.generate_global_initialization(statement)
                continue

            # Declarations of functions and structures do not
            # execute inside main.
            if isinstance(
                statement,
                (FunctionDeclNode, StructDeclNode)
            ):
                continue

            self.generate_statement(statement)

        if not self.builder.block.is_terminated:
            self.builder.ret(
                ir.Constant(self.i32, 0)
            )

    def generate_member_function_body(
        self,
        structure_node: StructDeclNode,
        node: FunctionDeclNode
    ):
        structure = self.symbols.get_structure(structure_node.name)

        llvm_function = self.member_functions[
            (structure.name, node.name)
        ]

        entry = llvm_function.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)

        self.local_variables = {}
        self.local_variable_types = {}
        self.current_result_type = node.result_type
        self.current_structure = structure

        # First hidden parameter is the object's address.
        self.current_object_pointer = llvm_function.args[0]
        self.current_object_pointer.name = "self"

        # Remaining LLVM arguments are source-level parameters.
        for parameter, llvm_argument in zip(
            node.parameters,
            llvm_function.args[1:]
        ):
            llvm_argument.name = parameter.name

            pointer = self.builder.alloca(
                self.llvm_type(parameter.type_name),
                name=f"{parameter.name}.addr"
            )

            self.builder.store(llvm_argument, pointer)
            self.local_variables[parameter.name] = pointer
            self.local_variable_types[
                parameter.name
            ] = parameter.type_name

        for statement in node.body:
            if self.builder.block.is_terminated:
                break

            self.generate_statement(statement)

        self.current_structure = None
        self.current_object_pointer = None

    def generate_function_body(self, node: FunctionDeclNode):
        llvm_function = self.functions[node.name]

        entry = llvm_function.append_basic_block("entry")
        self.builder = ir.IRBuilder(entry)
        self.local_variables = {}
        self.local_variable_types = {}
        self.current_result_type = node.result_type

        # Store every parameter in a local stack slot.
        for parameter, llvm_argument in zip(
            node.parameters,
            llvm_function.args
        ):
            llvm_argument.name = parameter.name

            pointer = self.builder.alloca(
                self.llvm_type(parameter.type_name),
                name=f"{parameter.name}.addr"
            )

            self.builder.store(llvm_argument, pointer)
            self.local_variables[parameter.name] = pointer
            self.local_variable_types[parameter.name] = parameter.type_name

        for statement in node.body:
            if self.builder.block.is_terminated:
                break

            self.generate_statement(statement)

    def generate(self, program: ProgramNode):
        # Declarations first.
        self.declare_structures()
        self.declare_runtime()
        self.declare_global_variables()
        self.declare_functions()
        self.declare_member_functions()

        # Generate global function bodies.
        for statement in program.statements:
            if isinstance(statement, FunctionDeclNode):
                self.generate_function_body(statement)

        # Generate member function bodies.
        for statement in program.statements:
            if isinstance(statement, StructDeclNode):
                for member in statement.member_functions:
                    self.generate_member_function_body(
                        statement,
                        member
                    )

        # Top-level executable code becomes C-compatible main.
        self.generate_main(program)

        return self.module

    def ir_text(self, program: ProgramNode):
        self.generate(program)
        return str(self.module)
