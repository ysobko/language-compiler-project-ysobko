from ast_nodes import (
    ProgramNode,
    IntegerNode,
    BinaryOpNode,
    BooleanNode,
    IdentifierNode,
    MutableDeclNode,
    ImmutableDeclNode,
    ConstantDeclNode,
    AssignmentNode,
    IfNode,
    FunctionDeclNode,
    ReturnNode,
    FunctionCallNode,
    StructDeclNode,
    ObjectCreationNode,
    FieldAccessNode,
    MemberCallNode,
    ExpressionStmtNode,
    ScanNode,
    PrintNode,
    StringNode,
)
from errors import CompilationError
from symbols import (
    SymbolTable,
    Scope,
    VariableSymbol,
    FunctionSymbol,
    StructSymbol,
    FieldSymbol,
)


I32 = "🟢"
I64 = "🛣️"
BOOL = "🚦"

I32_MIN = -(2 ** 31)
I32_MAX = 2 ** 31 - 1

I64_MIN = -(2 ** 63)
I64_MAX = 2 ** 63 - 1


class SemanticAnalyzer:
    def __init__(self):
        self.symbols = SymbolTable()
        self.scope = self.symbols.global_scope
        self.current_structure = None
        self.current_member = None
        self.current_result_type = None

    def analyze(self, program: ProgramNode):
        # Pass 1: register all structure names.
        # This allows named structure types to be referenced
        # from declarations that appear earlier in the file.
        for statement in program.statements:
            if isinstance(statement, StructDeclNode):
                if statement.name in self.symbols.structures:
                    self.error(
                        statement,
                        f"structure '{statement.name}' "
                        "is already declared"
                    )

                self.symbols.structures[statement.name] = (
                    StructSymbol(name=statement.name)
                )

        # Pass 2: collect structure fields and member signatures.
        for statement in program.statements:
            if isinstance(statement, StructDeclNode):
                self.declare_structure_contents(statement)

        # Pass 3: collect all global function signatures.
        # All functions are known before any body is analyzed,
        # enabling recursion and forward calls.
        for statement in program.statements:
            if isinstance(statement, FunctionDeclNode):
                self.declare_function(statement)

        # Pass 4: analyze executable statements and bodies.
        for statement in program.statements:
            self.analyze_statement(statement)

        return self.symbols

    def is_known_type(self, type_name: str):
        return (
            type_name in (I32, I64, BOOL)
            or self.symbols.get_structure(type_name) is not None
        )

    def declare_function(self, node: FunctionDeclNode):
        if node.name in self.symbols.functions:
            self.error(
                node,
                f"function '{node.name}' is already declared"
            )

        for parameter in node.parameters:
            if not self.is_known_type(parameter.type_name):
                self.error(
                    parameter,
                    f"unknown type '{parameter.type_name}'"
                )

        if not self.is_known_type(node.result_type):
            self.error(
                node,
                f"unknown result type '{node.result_type}'"
            )

        self.symbols.functions[node.name] = FunctionSymbol(
            name=node.name,
            parameter_types=[
                parameter.type_name
                for parameter in node.parameters
            ],
            result_type=node.result_type
        )


    def error(self, node, message: str):
        raise CompilationError(
            node.line,
            node.column,
            message
        )

    def analyze_statement(self, node):
        if isinstance(node, MutableDeclNode):
            self.analyze_declaration(node, mutable=True)
            return

        if isinstance(node, ImmutableDeclNode):
            self.analyze_declaration(node, mutable=False)
            return

        if isinstance(node, ConstantDeclNode):
            self.analyze_declaration(node, mutable=False)
            return

        if isinstance(node, AssignmentNode):
            self.analyze_assignment(node)
            return

        if isinstance(node, IfNode):
            self.analyze_if(node)
            return

        if isinstance(node, FunctionDeclNode):
            self.analyze_function(node)
            return

        if isinstance(node, StructDeclNode):
            self.analyze_structure(node)
            return

        if isinstance(node, ReturnNode):
            self.analyze_return(node)
            return

        if isinstance(node, ExpressionStmtNode):
            self.expression_type(node.expression)
            return

        if isinstance(node, PrintNode):
            self.analyze_print(node)
            return

        self.error(
            node,
            f"semantic analysis is not implemented for {type(node).__name__}"
        )

    def declare_structure_contents(self, node: StructDeclNode):
        structure = self.symbols.get_structure(node.name)

        field_names = set()

        for index, field in enumerate(node.fields):
            if field.name in field_names:
                self.error(
                    field,
                    f"field '{field.name}' is already declared "
                    f"in structure '{node.name}'"
                )

            if not self.is_known_type(field.type_name):
                self.error(
                    field,
                    f"unknown type '{field.type_name}'"
                )

            field_names.add(field.name)

            structure.fields.append(
                FieldSymbol(
                    name=field.name,
                    index=index,
                    type_name=field.type_name,
                    mutable=field.mutable
                )
            )

        for member in node.member_functions:
            if member.name in structure.member_functions:
                self.error(
                    member,
                    f"member function '{member.name}' is already "
                    f"declared in structure '{node.name}'"
                )

            for parameter in member.parameters:
                if not self.is_known_type(parameter.type_name):
                    self.error(
                        parameter,
                        f"unknown type '{parameter.type_name}'"
                    )

            if not self.is_known_type(member.result_type):
                self.error(
                    member,
                    f"unknown result type '{member.result_type}'"
                )

            structure.member_functions[member.name] = FunctionSymbol(
                name=member.name,
                parameter_types=[
                    parameter.type_name
                    for parameter in member.parameters
                ],
                result_type=member.result_type
            )

    def member_directly_assigns_field(
        self,
        member: FunctionDeclNode,
        structure: StructSymbol
    ):
        parameter_names = {
            parameter.name
            for parameter in member.parameters
        }

        def statement_assigns(statement):
            if isinstance(statement, AssignmentNode):
                target = statement.target

                # Bare name: it is a field only if a parameter/local
                # does not shadow it.
                if isinstance(target, IdentifierNode):
                    if target.name in parameter_names:
                        return False

                    return (
                        structure.get_field(target.name)
                        is not None
                    )

                # A chain beginning with a field of the current
                # structure mutates the current object.
                if isinstance(target, FieldAccessNode):
                    current = target

                    while isinstance(current, FieldAccessNode):
                        current = current.object

                    if isinstance(current, IdentifierNode):
                        if current.name in parameter_names:
                            return False

                        return (
                            structure.get_field(current.name)
                            is not None
                        )

            if isinstance(statement, IfNode):
                for child in statement.then_body:
                    if statement_assigns(child):
                        return True

                if statement.else_body is not None:
                    for child in statement.else_body:
                        if statement_assigns(child):
                            return True

            return False

        for statement in member.body:
            if statement_assigns(statement):
                return True

        return False

    def member_calls_mutating_member(
        self,
        member: FunctionDeclNode,
        structure: StructSymbol
    ):
        def expression_calls(expression):
            if isinstance(expression, FunctionCallNode):
                called = structure.member_functions.get(
                    expression.name
                )

                if called is not None and called.assigns_field:
                    return True

                for argument in expression.arguments:
                    if expression_calls(argument):
                        return True

            if isinstance(expression, MemberCallNode):
                if expression_calls(expression.object):
                    return True

                for argument in expression.arguments:
                    if expression_calls(argument):
                        return True

            if isinstance(expression, FieldAccessNode):
                return expression_calls(expression.object)

            if isinstance(expression, ObjectCreationNode):
                for value in expression.values:
                    if expression_calls(value):
                        return True

            return False

        def statement_calls(statement):
            if isinstance(statement, ReturnNode):
                return expression_calls(statement.value)

            if isinstance(statement, AssignmentNode):
                return expression_calls(statement.value)

            if isinstance(statement, ExpressionStmtNode):
                return expression_calls(statement.expression)

            if isinstance(statement, IfNode):
                if expression_calls(statement.condition):
                    return True

                for child in statement.then_body:
                    if statement_calls(child):
                        return True

                if statement.else_body is not None:
                    for child in statement.else_body:
                        if statement_calls(child):
                            return True

            return False

        for statement in member.body:
            if statement_calls(statement):
                return True

        return False

    def analyze_structure(self, node: StructDeclNode):
        structure = self.symbols.get_structure(node.name)

        # First find members that directly assign a field.
        for member in node.member_functions:
            symbol = structure.member_functions[member.name]

            if self.member_directly_assigns_field(
                member,
                structure
            ):
                symbol.assigns_field = True

        # Then propagate mutation through bare member calls.
        # Repeat until no new mutating member is discovered.
        changed = True

        while changed:
            changed = False

            for member in node.member_functions:
                symbol = structure.member_functions[member.name]

                if symbol.assigns_field:
                    continue

                if self.member_calls_mutating_member(
                    member,
                    structure
                ):
                    symbol.assigns_field = True
                    changed = True

        # Now analyze the member bodies with complete
        # mutating-member information.
        for member in node.member_functions:
            previous_scope = self.scope
            previous_structure = self.current_structure
            previous_member = self.current_member
            previous_result_type = self.current_result_type

            self.scope = Scope(parent=self.symbols.global_scope)
            self.current_structure = structure
            self.current_member = structure.member_functions[member.name]
            self.current_result_type = member.result_type

            for parameter in member.parameters:
                if (
                    parameter.type_name not in (I32, I64, BOOL)
                    and self.symbols.get_structure(
                        parameter.type_name
                    ) is None
                ):
                    self.error(
                        parameter,
                        f"unknown type '{parameter.type_name}'"
                    )

                symbol = VariableSymbol(
                    name=parameter.name,
                    type_name=parameter.type_name,
                    mutable=True
                )

                if not self.scope.declare(symbol):
                    self.error(
                        parameter,
                        f"name '{parameter.name}' is already "
                        "declared in this scope"
                    )

            for statement in member.body:
                self.analyze_statement(statement)

            if not self.block_guarantees_return(member.body):
                self.error(
                    member,
                    f"member function '{member.name}' "
                    "may finish without arrive"
                )

            self.scope = previous_scope
            self.current_structure = previous_structure
            self.current_member = previous_member
            self.current_result_type = previous_result_type

    def lookup_name(self, name: str):
        # First: parameters and local variables of the current scope.
        local = self.scope.variables.get(name)

        if local is not None:
            return ("variable", local)

        # Second: fields of the current object when inside
        # a member function.
        if self.current_structure is not None:
            field = self.current_structure.get_field(name)

            if field is not None:
                return ("field", field)

        # Third: enclosing/global variables.
        scope = self.scope.parent

        while scope is not None:
            symbol = scope.variables.get(name)

            if symbol is not None:
                return ("variable", symbol)

            scope = scope.parent

        return (None, None)

    def statement_guarantees_return(self, statement):
        if isinstance(statement, ReturnNode):
            return True

        if isinstance(statement, IfNode):
            if statement.else_body is None:
                return False

            return (
                self.block_guarantees_return(statement.then_body)
                and self.block_guarantees_return(statement.else_body)
            )

        return False

    def block_guarantees_return(self, statements):
        for statement in statements:
            if self.statement_guarantees_return(statement):
                return True

        return False

    def analyze_function(self, node: FunctionDeclNode):
        previous_scope = self.scope
        previous_result_type = getattr(
            self,
            "current_result_type",
            None
        )

        self.scope = Scope(parent=self.symbols.global_scope)
        self.current_result_type = node.result_type

        for parameter in node.parameters:
            if not self.is_known_type(parameter.type_name):
                self.error(
                    parameter,
                    f"unknown type '{parameter.type_name}'"
                )

            symbol = VariableSymbol(
                name=parameter.name,
                type_name=parameter.type_name,
                mutable=True
            )

            if not self.scope.declare(symbol):
                self.error(
                    parameter,
                    f"name '{parameter.name}' is already declared "
                    "in this scope"
                )

        for statement in node.body:
            self.analyze_statement(statement)

        if not self.block_guarantees_return(node.body):
            self.error(
                node,
                f"function '{node.name}' may finish without arrive"
            )

        self.scope = previous_scope
        self.current_result_type = previous_result_type

    def analyze_return(self, node: ReturnNode):
        if getattr(self, "current_result_type", None) is None:
            self.error(
                node,
                "arrive may only be used inside a function"
            )

        value_type = self.expression_type(node.value)

        if isinstance(node.value, IntegerNode):
            if self.current_result_type not in (I32, I64):
                self.error(
                    node.value,
                    f"function must return {self.current_result_type}"
                )

            self.check_integer_literal_range(
                node.value,
                self.current_result_type
            )

        elif value_type != self.current_result_type:
            self.error(
                node.value,
                f"function must return {self.current_result_type}, "
                f"got {value_type}"
            )

    def analyze_declaration(self, node, mutable: bool):
        # Check the initializer before declaring the name.
        # Therefore a variable cannot use itself in its own initializer.
        value_type = self.expression_type(node.value)

        if (
            node.type_name not in (I32, I64, BOOL)
            and self.symbols.get_structure(node.type_name) is None
        ):
            self.error(
                node,
                f"unknown type '{node.type_name}'"
            )

        if isinstance(node.value, IntegerNode):
            if node.type_name not in (I32, I64):
                self.error(
                    node.value,
                    f"cannot initialize '{node.name}' of type "
                    f"{node.type_name} with an integer value"
                )

            self.check_integer_literal_range(
                node.value,
                node.type_name
            )

        elif value_type != node.type_name:
            self.error(
                node.value,
                f"cannot initialize '{node.name}' of type "
                f"{node.type_name} with value of type {value_type}"
            )

        symbol = VariableSymbol(
            name=node.name,
            type_name=node.type_name,
            mutable=mutable
        )

        if not self.scope.declare(symbol):
            self.error(
                node,
                f"name '{node.name}' is already declared in this scope"
            )

    def analyze_assignment(self, node):
        if isinstance(node.target, IdentifierNode):
            kind, symbol = self.lookup_name(node.target.name)

            if symbol is None:
                self.error(
                    node.target,
                    f"name '{node.target.name}' is not declared"
                )

            if not symbol.mutable:
                if kind == "field":
                    self.error(
                        node.target,
                        f"field '{node.target.name}' is immutable"
                    )

                self.error(
                    node.target,
                    f"name '{node.target.name}' is immutable"
                )

            if kind == "field":
                if self.current_member is None:
                    self.error(
                        node.target,
                        "field assignment is only valid "
                        "inside a member function"
                    )

                self.current_member.assigns_field = True

            target_type = symbol.type_name

        elif isinstance(node.target, FieldAccessNode):
            target_type = self.analyze_mutable_field_chain(
                node.target
            )

        else:
            self.error(
                node.target,
                "invalid assignment target"
            )

        value_type = self.expression_type(node.value)

        if isinstance(node.value, IntegerNode):
            if target_type not in (I32, I64):
                self.error(
                    node.value,
                    f"cannot assign an integer value "
                    f"to value of type {target_type}"
                )

            self.check_integer_literal_range(
                node.value,
                target_type
            )

        elif value_type != target_type:
            self.error(
                node.value,
                f"cannot assign value of type {value_type} "
                f"to value of type {target_type}"
            )

    def analyze_mutable_field_chain(self, node: FieldAccessNode):
        fields = []
        current = node

        while isinstance(current, FieldAccessNode):
            fields.append(current)
            current = current.object

        if not isinstance(current, IdentifierNode):
            self.error(
                node,
                "field assignment must start from a named object"
            )

        root = self.scope.lookup(current.name)

        if root is None:
            self.error(
                current,
                f"name '{current.name}' is not declared"
            )

        if not root.mutable:
            self.error(
                current,
                f"name '{current.name}' is immutable"
            )

        current_type = root.type_name

        for field_access in reversed(fields):
            structure = self.symbols.get_structure(current_type)

            if structure is None:
                self.error(
                    field_access,
                    f"type '{current_type}' has no fields"
                )

            field = structure.get_field(
                field_access.field_name
            )

            if field is None:
                self.error(
                    field_access,
                    f"structure '{structure.name}' has no field "
                    f"'{field_access.field_name}'"
                )

            if not field.mutable:
                self.error(
                    field_access,
                    f"field '{field.name}' of structure "
                    f"'{structure.name}' is immutable"
                )

            current_type = field.type_name

        return current_type

    def analyze_if(self, node):
        left_type = self.expression_type(node.condition.left)
        right_type = self.expression_type(node.condition.right)

        if left_type != right_type:
            self.error(
                node.condition,
                "comparison operands must have the same type"
            )

        previous_scope = self.scope

        self.scope = Scope(parent=previous_scope)
        for statement in node.then_body:
            self.analyze_statement(statement)
        self.scope = previous_scope

        if node.else_body is not None:
            self.scope = Scope(parent=previous_scope)
            for statement in node.else_body:
                self.analyze_statement(statement)
            self.scope = previous_scope

    def evaluate_constant_integer(self, node):
        if isinstance(node, IntegerNode):
            return node.value

        if isinstance(node, BinaryOpNode):
            left = self.evaluate_constant_integer(node.left)
            right = self.evaluate_constant_integer(node.right)

            if left is None or right is None:
                return None

            if node.operator == "+":
                return left + right

            if node.operator == "-":
                return left - right

            if node.operator == "*":
                return left * right

        return None

    def analyze_binary_operation(self, node):
        left_type = self.expression_type(node.left)
        right_type = self.expression_type(node.right)

        if left_type not in (I32, I64):
            self.error(
                node.left,
                "arithmetic operands must be integers"
            )

        if right_type not in (I32, I64):
            self.error(
                node.right,
                "arithmetic operands must be integers"
            )

        if left_type != right_type:
            if (
                isinstance(node.left, IntegerNode)
                and right_type == I64
            ):
                result_type = I64
            elif (
                isinstance(node.right, IntegerNode)
                and left_type == I64
            ):
                result_type = I64
            else:
                self.error(
                    node,
                    "arithmetic operands must have the same type"
                )
        else:
            result_type = left_type

        constant_value = self.evaluate_constant_integer(node)

        if constant_value is not None:
            if not I64_MIN <= constant_value <= I64_MAX:
                self.error(
                    node,
                    "arithmetic result is outside the i64 range"
                )

            if not I32_MIN <= constant_value <= I32_MAX:
                result_type = I64

        return result_type

    def expression_type(self, node):
        if isinstance(node, BinaryOpNode):
            return self.analyze_binary_operation(node)

        if isinstance(node, IntegerNode):
            # Integer literals do not have a final width by themselves.
            # Use i32 when possible and i64 otherwise.
            if I32_MIN <= node.value <= I32_MAX:
                return I32

            if I64_MIN <= node.value <= I64_MAX:
                return I64

            self.error(node, "integer literal is outside the i64 range")

        if isinstance(node, BooleanNode):
            return BOOL

        if isinstance(node, IdentifierNode):
            kind, symbol = self.lookup_name(node.name)

            if symbol is None:
                self.error(
                    node,
                    f"name '{node.name}' is not declared"
                )

            return symbol.type_name

        if isinstance(node, ScanNode):
            return I32

        if isinstance(node, FunctionCallNode):
            return self.analyze_function_call(node)

        if isinstance(node, ObjectCreationNode):
            return self.analyze_object_creation(node)

        if isinstance(node, FieldAccessNode):
            return self.analyze_field_access(node)

        if isinstance(node, MemberCallNode):
            return self.analyze_member_call(node)

        self.error(
            node,
            f"expression type analysis is not implemented for "
            f"{type(node).__name__}"
        )

    def analyze_object_creation(self, node: ObjectCreationNode):
        structure = self.symbols.get_structure(node.type_name)

        if structure is None:
            self.error(
                node,
                f"structure '{node.type_name}' is not declared"
            )

        if len(node.values) != len(structure.fields):
            self.error(
                node,
                f"structure '{node.type_name}' expects "
                f"{len(structure.fields)} field value(s), "
                f"got {len(node.values)}"
            )

        for index, (value, field) in enumerate(
            zip(node.values, structure.fields),
            start=1
        ):
            value_type = self.expression_type(value)

            if isinstance(value, IntegerNode):
                if field.type_name not in (I32, I64):
                    self.error(
                        value,
                        f"value {index} for field '{field.name}' "
                        f"must have type {field.type_name}"
                    )

                self.check_integer_literal_range(
                    value,
                    field.type_name
                )

            elif value_type != field.type_name:
                self.error(
                    value,
                    f"value {index} for field '{field.name}' "
                    f"must have type {field.type_name}, "
                    f"got {value_type}"
                )

        return structure.name

    def analyze_field_access(self, node: FieldAccessNode):
        object_type = self.expression_type(node.object)
        structure = self.symbols.get_structure(object_type)

        if structure is None:
            self.error(
                node,
                f"type '{object_type}' has no fields"
            )

        field = structure.get_field(node.field_name)

        if field is None:
            self.error(
                node,
                f"structure '{structure.name}' has no field "
                f"'{node.field_name}'"
            )

        return field.type_name

    def analyze_print(self, node: PrintNode):
        if isinstance(node.value, StringNode):
            return

        value_type = self.expression_type(node.value)

        if value_type in (I32, I64, BOOL):
            return

        if self.symbols.get_structure(value_type) is not None:
            return

        self.error(
            node.value,
            f"print does not support values of type {value_type}"
        )

    def analyze_member_call(self, node: MemberCallNode):
        object_type = self.expression_type(node.object)
        structure = self.symbols.get_structure(object_type)

        if structure is None:
            self.error(
                node,
                f"type '{object_type}' has no member functions"
            )

        member = structure.member_functions.get(
            node.member_name
        )

        if member is None:
            self.error(
                node,
                f"structure '{structure.name}' has no member "
                f"function '{node.member_name}'"
            )

        if len(node.arguments) != len(member.parameter_types):
            self.error(
                node,
                f"member function '{node.member_name}' expects "
                f"{len(member.parameter_types)} argument(s), "
                f"got {len(node.arguments)}"
            )

        for index, (argument, parameter_type) in enumerate(
            zip(node.arguments, member.parameter_types),
            start=1
        ):
            argument_type = self.expression_type(argument)

            if isinstance(argument, IntegerNode):
                if parameter_type not in (I32, I64):
                    self.error(
                        argument,
                        f"argument {index} of member function "
                        f"'{node.member_name}' must have type "
                        f"{parameter_type}"
                    )

                self.check_integer_literal_range(
                    argument,
                    parameter_type
                )

            elif argument_type != parameter_type:
                self.error(
                    argument,
                    f"argument {index} of member function "
                    f"'{node.member_name}' must have type "
                    f"{parameter_type}, got {argument_type}"
                )

        if member.assigns_field:
            self.check_mutable_object(node.object)

        return member.result_type

    def check_mutable_object(self, node):
        if isinstance(node, IdentifierNode):
            kind, symbol = self.lookup_name(node.name)

            if symbol is None:
                self.error(
                    node,
                    f"name '{node.name}' is not declared"
                )

            if not symbol.mutable:
                if kind == "field":
                    self.error(
                        node,
                        f"field '{node.name}' is immutable"
                    )

                self.error(
                    node,
                    f"name '{node.name}' is immutable"
                )

            return

        if isinstance(node, FieldAccessNode):
            self.analyze_mutable_field_chain(node)
            return

        self.error(
            node,
            "mutating member function requires a mutable object"
        )

    def analyze_function_call(self, node: FunctionCallNode):
        function = None
        is_member = False

        # Inside a member function, other member functions of the
        # same structure are visible by bare name.
        if self.current_structure is not None:
            function = self.current_structure.member_functions.get(
                node.name
            )

            if function is not None:
                is_member = True

        # If there is no member with this name, look for a
        # normal/global function.
        if function is None:
            function = self.symbols.get_function(node.name)

        if function is None:
            self.error(
                node,
                f"function '{node.name}' is not declared"
            )

        if len(node.arguments) != len(function.parameter_types):
            self.error(
                node,
                f"function '{node.name}' expects "
                f"{len(function.parameter_types)} argument(s), "
                f"got {len(node.arguments)}"
            )

        for index, (argument, parameter_type) in enumerate(
            zip(node.arguments, function.parameter_types),
            start=1
        ):
            argument_type = self.expression_type(argument)

            if isinstance(argument, IntegerNode):
                if parameter_type not in (I32, I64):
                    self.error(
                        argument,
                        f"argument {index} of function '{node.name}' "
                        f"must have type {parameter_type}"
                    )

                self.check_integer_literal_range(
                    argument,
                    parameter_type
                )

            elif argument_type != parameter_type:
                self.error(
                    argument,
                    f"argument {index} of function '{node.name}' "
                    f"must have type {parameter_type}, "
                    f"got {argument_type}"
                )

        # A bare member call uses the current object ("this").
        # If the called member mutates a field, the current member
        # is mutating as well.
        if (
            is_member
            and function.assigns_field
            and self.current_member is not None
        ):
            self.current_member.assigns_field = True

        return function.result_type

    def check_integer_literal_range(self, node, target_type: str):
        if not isinstance(node, IntegerNode):
            return

        if target_type == I32:
            if not I32_MIN <= node.value <= I32_MAX:
                self.error(
                    node,
                    "integer value does not fit in 🟢"
                )

        elif target_type == I64:
            if not I64_MIN <= node.value <= I64_MAX:
                self.error(
                    node,
                    "integer value does not fit in 🛣️"
                )
