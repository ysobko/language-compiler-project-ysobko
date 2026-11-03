from dataclasses import fields, is_dataclass

from ast_nodes import (
    ProgramNode,
    ExprNode,
    FunctionCallNode,
    MemberCallNode,
    ScanNode,
)


class ASTOptimizer:
    def optimize(self, program: ProgramNode) -> ProgramNode:
        self.remove_unused_variables(program)
        self.remove_unused_functions(program)
        self.remove_unused_variables(program)
        self.inline_functions(program)
        self.remove_unused_functions(program)
        self.remove_unused_variables(program)
        return program

    def has_side_effects(self, expression: ExprNode) -> bool:
        if isinstance(
            expression,
            (FunctionCallNode, MemberCallNode, ScanNode)
        ):
            return True

        if not is_dataclass(expression):
            return False

        for field in fields(expression):
            value = getattr(expression, field.name)

            if isinstance(value, ExprNode):
                if self.has_side_effects(value):
                    return True

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, ExprNode):
                        if self.has_side_effects(item):
                            return True

        return False

    def collect_used_variables(self, program: ProgramNode) -> set[int]:
        from ast_nodes import (
            IdentifierNode,
            MutableDeclNode,
            ImmutableDeclNode,
            ConstantDeclNode,
            AssignmentNode,
            FunctionDeclNode,
            StructDeclNode,
            IfNode,
        )

        declarations = (
            MutableDeclNode,
            ImmutableDeclNode,
            ConstantDeclNode,
        )

        used = set()
        scopes = [{}]
        current_fields = set()

        def resolve(name):
            # Current local scope and its enclosing local scopes.
            for scope in reversed(scopes[1:]):
                if name in scope:
                    return scope[name]

            # Fields take priority over global variables.
            if name in current_fields:
                return None

            # Global scope.
            return scopes[0].get(name)

        def visit_expression(expression):
            if isinstance(expression, IdentifierNode):
                declaration = resolve(expression.name)

                if declaration is not None:
                    used.add(id(declaration))
                return

            if not is_dataclass(expression):
                return

            for field in fields(expression):
                value = getattr(expression, field.name)

                if isinstance(value, ExprNode):
                    visit_expression(value)

                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, ExprNode):
                            visit_expression(item)

        def visit_block(statements):
            for statement in statements:
                if isinstance(statement, declarations):
                    visit_expression(statement.value)
                    scopes[-1][statement.name] = statement

                elif isinstance(statement, AssignmentNode):
                    if not isinstance(statement.target, IdentifierNode):
                        visit_expression(statement.target)

                    visit_expression(statement.value)

                elif isinstance(statement, IfNode):
                    visit_expression(statement.condition)

                    scopes.append({})
                    visit_block(statement.then_body)
                    scopes.pop()

                    if statement.else_body is not None:
                        scopes.append({})
                        visit_block(statement.else_body)
                        scopes.pop()

                elif isinstance(statement, (FunctionDeclNode, StructDeclNode)):
                    continue

                else:
                    for field in fields(statement):
                        value = getattr(statement, field.name)

                        if isinstance(value, ExprNode):
                            visit_expression(value)

        # Register global declarations.
        for statement in program.statements:
            if isinstance(statement, declarations):
                scopes[0][statement.name] = statement

        # Analyze top-level executable statements.
        visit_block(program.statements)

        # Analyze ordinary functions.
        for statement in program.statements:
            if isinstance(statement, FunctionDeclNode):
                scopes.append({
                    parameter.name: parameter
                    for parameter in statement.parameters
                })

                visit_block(statement.body)
                scopes.pop()

            elif isinstance(statement, StructDeclNode):
                # Analyze each member function with its structure fields.
                current_fields = {
                    field.name for field in statement.fields
                }

                for method in statement.member_functions:
                    scopes.append({
                        parameter.name: parameter
                        for parameter in method.parameters
                    })

                    visit_block(method.body)
                    scopes.pop()

                current_fields = set()

        return used

    def remove_unused_variables(self, program: ProgramNode) -> ProgramNode:
        from ast_nodes import (
            MutableDeclNode, ImmutableDeclNode, ConstantDeclNode,
            AssignmentNode, IdentifierNode, FunctionDeclNode,
            StructDeclNode, IfNode, ExpressionStmtNode,
        )

        declarations = (MutableDeclNode, ImmutableDeclNode, ConstantDeclNode)

        def optimize_pass():
            used = self.collect_used_variables(program)
            scopes = [{}]
            current_fields = set()
            changed = False

            # Global declarations are visible inside functions.
            for statement in program.statements:
                if isinstance(statement, declarations):
                    scopes[0][statement.name] = statement

            def resolve(name):
                for scope in reversed(scopes[1:]):
                    if name in scope:
                        return scope[name]
                if name in current_fields:
                    return None
                return scopes[0].get(name)

            def preserve_effect(expression, original):
                if self.has_side_effects(expression):
                    return ExpressionStmtNode(
                        line=original.line,
                        column=original.column,
                        expression=expression,
                    )
                return None

            def visit_block(statements):
                nonlocal changed
                result = []

                for statement in statements:
                    if isinstance(statement, declarations):
                        # Register even if removed, so later assignments
                        # still resolve to the correct declaration.
                        scopes[-1][statement.name] = statement

                        if id(statement) not in used:
                            changed = True
                            effect = preserve_effect(
                                statement.value, statement
                            )
                            if effect is not None:
                                result.append(effect)
                            continue

                    elif isinstance(statement, AssignmentNode):
                        if isinstance(statement.target, IdentifierNode):
                            declaration = resolve(statement.target.name)

                            if (
                                declaration is not None
                                and isinstance(declaration, declarations)
                                and id(declaration) not in used
                            ):
                                changed = True
                                effect = preserve_effect(
                                    statement.value, statement
                                )
                                if effect is not None:
                                    result.append(effect)
                                continue

                    elif isinstance(statement, IfNode):
                        scopes.append({})
                        statement.then_body = visit_block(statement.then_body)
                        scopes.pop()

                        if statement.else_body is not None:
                            scopes.append({})
                            statement.else_body = visit_block(
                                statement.else_body
                            )
                            scopes.pop()

                    result.append(statement)

                return result

            program.statements = visit_block(program.statements)

            for statement in program.statements:
                if isinstance(statement, FunctionDeclNode):
                    scopes.append({
                        p.name: p for p in statement.parameters
                    })
                    statement.body = visit_block(statement.body)
                    scopes.pop()

                elif isinstance(statement, StructDeclNode):
                    current_fields = {f.name for f in statement.fields}

                    for method in statement.member_functions:
                        scopes.append({
                            p.name: p for p in method.parameters
                        })
                        method.body = visit_block(method.body)
                        scopes.pop()

                    current_fields = set()

            return changed

        while optimize_pass():
            pass

        return program

    def collect_assigned_variables(self, program: ProgramNode) -> set[int]:
        from ast_nodes import (
            MutableDeclNode,
            ImmutableDeclNode,
            ConstantDeclNode,
            AssignmentNode,
            IdentifierNode,
            FunctionDeclNode,
            StructDeclNode,
            IfNode,
        )

        declarations = (
            MutableDeclNode,
            ImmutableDeclNode,
            ConstantDeclNode,
        )

        assigned = set()
        scopes = [{}]
        current_fields = set()

        def resolve(name):
            for scope in reversed(scopes[1:]):
                if name in scope:
                    return scope[name]

            if name in current_fields:
                return None

            return scopes[0].get(name)

        def visit_block(statements):
            for statement in statements:
                if isinstance(statement, declarations):
                    scopes[-1][statement.name] = statement

                elif isinstance(statement, AssignmentNode):
                    if isinstance(statement.target, IdentifierNode):
                        declaration = resolve(statement.target.name)

                        if declaration is not None:
                            assigned.add(id(declaration))

                elif isinstance(statement, IfNode):
                    scopes.append({})
                    visit_block(statement.then_body)
                    scopes.pop()

                    if statement.else_body is not None:
                        scopes.append({})
                        visit_block(statement.else_body)
                        scopes.pop()

        for statement in program.statements:
            if isinstance(statement, declarations):
                scopes[0][statement.name] = statement

        visit_block(program.statements)

        for statement in program.statements:
            if isinstance(statement, FunctionDeclNode):
                scopes.append({
                    parameter.name: parameter
                    for parameter in statement.parameters
                })

                visit_block(statement.body)
                scopes.pop()

            elif isinstance(statement, StructDeclNode):
                current_fields = {
                    field.name for field in statement.fields
                }

                for method in statement.member_functions:
                    scopes.append({
                        parameter.name: parameter
                        for parameter in method.parameters
                    })

                    visit_block(method.body)
                    scopes.pop()

                current_fields = set()

        return assigned

    def remove_unused_functions(self, program: ProgramNode) -> ProgramNode:
        from ast_nodes import FunctionDeclNode

        functions = {
            statement.name: statement
            for statement in program.statements
            if isinstance(statement, FunctionDeclNode)
        }

        def collect_calls(node, called):
            if isinstance(node, list):
                for item in node:
                    collect_calls(item, called)
                return

            if isinstance(node, FunctionCallNode):
                called.add(node.name)

            if not is_dataclass(node):
                return

            for field in fields(node):
                value = getattr(node, field.name)

                if is_dataclass(value) or isinstance(value, list):
                    collect_calls(value, called)

        # Start from executable top-level code and structures.
        reachable = set()

        for statement in program.statements:
            if not isinstance(statement, FunctionDeclNode):
                collect_calls(statement, reachable)

        # Follow calls from reachable functions.
        pending = list(reachable)
        visited = set()

        while pending:
            name = pending.pop()

            if name in visited:
                continue

            visited.add(name)

            function = functions.get(name)

            if function is None:
                continue

            called = set()
            collect_calls(function.body, called)

            for called_name in called:
                if called_name not in reachable:
                    reachable.add(called_name)
                    pending.append(called_name)

        program.statements = [
            statement
            for statement in program.statements
            if (
                not isinstance(statement, FunctionDeclNode)
                or statement.name in reachable
            )
        ]

        return program

    def count_function_calls(self, program: ProgramNode) -> dict[str, int]:
        from ast_nodes import FunctionDeclNode

        counts = {
            statement.name: 0
            for statement in program.statements
            if isinstance(statement, FunctionDeclNode)
        }

        def visit(node):
            if isinstance(node, list):
                for item in node:
                    visit(item)
                return

            if isinstance(node, FunctionCallNode):
                if node.name in counts:
                    counts[node.name] += 1

            if not is_dataclass(node):
                return

            for field in fields(node):
                value = getattr(node, field.name)

                if is_dataclass(value) or isinstance(value, list):
                    visit(value)

        visit(program)
        return counts

    def find_recursive_functions(self, program: ProgramNode) -> set[str]:
        from ast_nodes import FunctionDeclNode

        functions = {
            statement.name: statement
            for statement in program.statements
            if isinstance(statement, FunctionDeclNode)
        }

        def collect_calls(node, called):
            if isinstance(node, list):
                for item in node:
                    collect_calls(item, called)
                return

            if isinstance(node, FunctionCallNode):
                if node.name in functions:
                    called.add(node.name)

            if not is_dataclass(node):
                return

            for field in fields(node):
                value = getattr(node, field.name)

                if is_dataclass(value) or isinstance(value, list):
                    collect_calls(value, called)

        call_graph = {}

        for name, function in functions.items():
            called = set()
            collect_calls(function.body, called)
            call_graph[name] = called

        recursive = set()

        for start in functions:
            visited = set()
            pending = list(call_graph[start])

            while pending:
                name = pending.pop()

                if name == start:
                    recursive.add(start)
                    break

                if name in visited:
                    continue

                visited.add(name)
                pending.extend(call_graph.get(name, set()))

        return recursive

    def inline_functions(self, program: ProgramNode) -> ProgramNode:
        from copy import deepcopy
        from ast_nodes import (
            ExprNode, IdentifierNode, FunctionCallNode,
            FunctionDeclNode, MutableDeclNode, ImmutableDeclNode,
            ConstantDeclNode, ReturnNode, PrintNode, InlineBlockNode,
        )

        declarations = (
            MutableDeclNode, ImmutableDeclNode, ConstantDeclNode
        )
        counter = 0
        used_names = set()

        def collect_names(node):
            if isinstance(node, list):
                for item in node:
                    collect_names(item)
                return
            if not is_dataclass(node):
                return
            if isinstance(node, IdentifierNode):
                used_names.add(node.name)
            if isinstance(node, declarations):
                used_names.add(node.name)
            for field in fields(node):
                value = getattr(node, field.name)
                if is_dataclass(value) or isinstance(value, list):
                    collect_names(value)

        collect_names(program)

        def fresh(name):
            nonlocal counter
            while True:
                counter += 1
                result = f"_inline_{counter}_{name}"
                if result not in used_names:
                    used_names.add(result)
                    return result

        def rename(node, mapping):
            if isinstance(node, IdentifierNode):
                node.name = mapping.get(node.name, node.name)
                return
            if isinstance(node, list):
                for item in node:
                    rename(item, mapping)
                return
            if not is_dataclass(node):
                return
            for field in fields(node):
                value = getattr(node, field.name)
                if is_dataclass(value) or isinstance(value, list):
                    rename(value, mapping)

        def supported(fn):
            if not fn.body or not isinstance(fn.body[-1], ReturnNode):
                return False
            if not all(isinstance(s, declarations) for s in fn.body[:-1]):
                return False

            available = {p.name for p in fn.parameters}

            def valid_refs(node):
                if isinstance(node, IdentifierNode):
                    return node.name in available
                if isinstance(node, list):
                    return all(valid_refs(x) for x in node)
                if not is_dataclass(node):
                    return True
                return all(
                    valid_refs(getattr(node, f.name))
                    for f in fields(node)
                    if is_dataclass(getattr(node, f.name))
                    or isinstance(getattr(node, f.name), list)
                )

            for statement in fn.body[:-1]:
                if not valid_refs(statement.value):
                    return False
                available.add(statement.name)

            return valid_refs(fn.body[-1].value)

        def expand(fn, call):
            mapping = {}
            prefix = []

            for param, arg in zip(fn.parameters, call.arguments):
                name = fresh(param.name)
                mapping[param.name] = name
                prefix.append(MutableDeclNode(
                    line=call.line, column=call.column,
                    type_name=param.type_name,
                    name=name, value=arg
                ))

            for statement in fn.body[:-1]:
                copied = deepcopy(statement)
                rename(copied.value, mapping)
                name = fresh(copied.name)
                mapping[copied.name] = name
                copied.name = name
                prefix.append(copied)

            result = deepcopy(fn.body[-1].value)
            rename(result, mapping)
            return prefix, result

        def has_side_effects(node):
            from ast_nodes import ScanNode, FunctionCallNode, MemberCallNode

            if isinstance(node, (ScanNode, FunctionCallNode, MemberCallNode)):
                return True

            if isinstance(node, list):
                return any(has_side_effects(item) for item in node)

            if not is_dataclass(node):
                return False

            return any(
                has_side_effects(getattr(node, field.name))
                for field in fields(node)
            )

        def transform_expr(expr, functions, counts, recursive):
            # Work on a copy so an unsafe transformation can be discarded.
            original = deepcopy(expr)
            prefix = []
            earlier_expressions = []

            for field in fields(expr):
                value = getattr(expr, field.name)

                if isinstance(value, ExprNode):
                    new_prefix, new_value = transform_expr(
                        value, functions, counts, recursive
                    )

                    if new_prefix and any(
                        has_side_effects(previous)
                        for previous in earlier_expressions
                    ):
                        return [], original

                    prefix.extend(new_prefix)
                    setattr(expr, field.name, new_value)
                    earlier_expressions.append(new_value)

                elif isinstance(value, list):
                    new_items = []

                    for item in value:
                        if isinstance(item, ExprNode):
                            new_prefix, new_item = transform_expr(
                                item, functions, counts, recursive
                            )

                            if new_prefix and any(
                                has_side_effects(previous)
                                for previous in earlier_expressions
                            ):
                                return [], original

                            prefix.extend(new_prefix)
                            item = new_item
                            earlier_expressions.append(item)

                        new_items.append(item)

                    setattr(expr, field.name, new_items)

            if not isinstance(expr, FunctionCallNode):
                return prefix, expr

            fn = functions.get(expr.name)

            if (
                fn is None
                or counts.get(expr.name) != 1
                or expr.name in recursive
                or not supported(fn)
                or len(expr.arguments) != len(fn.parameters)
            ):
                return prefix, expr

            inserted, result = expand(fn, expr)
            prefix.extend(inserted)

            return prefix, result

        while True:
            counts = self.count_function_calls(program)
            recursive = self.find_recursive_functions(program)
            functions = {
                stmt.name: stmt
                for stmt in program.statements
                if isinstance(stmt, FunctionDeclNode)
            }

            changed = False

            def process(stmt):
                nonlocal changed

                if isinstance(stmt, (PrintNode, ReturnNode) + declarations):
                    prefix, value = transform_expr(
                        stmt.value, functions, counts, recursive
                    )
                    stmt.value = value
                    if prefix:
                        changed = True
                    return prefix + [stmt]

                return [stmt]

            updated = []

            for stmt in program.statements:
                if isinstance(stmt, FunctionDeclNode):
                    new_body = []
                    for inner in stmt.body:
                        new_body.extend(process(inner))
                    stmt.body = new_body
                    updated.append(stmt)

                elif isinstance(stmt, PrintNode):
                    statements = process(stmt)
                    if len(statements) > 1:
                        updated.append(InlineBlockNode(
                            line=stmt.line, column=stmt.column,
                            statements=statements
                        ))
                    else:
                        updated.append(stmt)

                elif isinstance(stmt, declarations):
                    updated.extend(process(stmt))

                else:
                    updated.append(stmt)

            program.statements = updated

            if not changed:
                break

            self.remove_unused_functions(program)

        return program
