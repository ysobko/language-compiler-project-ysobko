from ast_nodes import (
    ProgramNode,
    IntegerNode,
    BooleanNode,
    StringNode,
    IdentifierNode,
    ComparisonNode,
    FunctionCallNode,
    ObjectCreationNode,
    FieldAccessNode,
    MemberCallNode,
    ExpressionStmtNode,
    ScanNode,
    PrintNode,
    ParameterNode,
    FunctionDeclNode,
    ReturnNode,
    FieldDeclNode,
    StructDeclNode,
    MutableDeclNode,
    ImmutableDeclNode,
    ConstantDeclNode,
    AssignmentNode,
    IfNode,
)


def dump_ast(node, indent=0):
    prefix = "  " * indent

    if isinstance(node, ProgramNode):
        lines = [f"{prefix}Program"]

        for statement in node.statements:
            lines.append(dump_ast(statement, indent + 1))

        return "\n".join(lines)

    if isinstance(node, StructDeclNode):
        lines = [f"{prefix}StructDecl {node.name}"]

        lines.append(f"{prefix}  Fields")

        for field in node.fields:
            lines.append(dump_ast(field, indent + 2))

        if node.member_functions:
            lines.append(f"{prefix}  MemberFunctions")

            for function in node.member_functions:
                lines.append(dump_ast(function, indent + 2))

        return "\n".join(lines)

    if isinstance(node, FieldDeclNode):
        mutability = "mutable" if node.mutable else "immutable"

        return (
            f"{prefix}Field {mutability} "
            f"{node.type_name}  {node.name}"
        )

    if isinstance(node, FunctionDeclNode):
        lines = [
            f"{prefix}FunctionDecl {node.name} -> {node.result_type}",
            f"{prefix}  Parameters",
        ]

        for parameter in node.parameters:
            lines.append(dump_ast(parameter, indent + 2))

        lines.append(f"{prefix}  Body")

        for statement in node.body:
            lines.append(dump_ast(statement, indent + 2))

        return "\n".join(lines)

    if isinstance(node, ParameterNode):
        return f"{prefix}Parameter {node.type_name} {node.name}"

    if isinstance(node, ReturnNode):
        lines = [
            f"{prefix}Return",
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, PrintNode):
        lines = [
            f"{prefix}Print",
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, ExpressionStmtNode):
        lines = [
            f"{prefix}ExpressionStmt",
            dump_ast(node.expression, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, MutableDeclNode):
        lines = [
            f"{prefix}MutableDecl {node.type_name} {node.name}",
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, ImmutableDeclNode):
        lines = [
            f"{prefix}ImmutableDecl {node.type_name} {node.name}",
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, ConstantDeclNode):
        lines = [
            f"{prefix}ConstantDecl {node.type_name} {node.name}",
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, AssignmentNode):
        if isinstance(node.target, IdentifierNode):
            lines = [
                f"{prefix}Assignment {node.target.name}",
                dump_ast(node.value, indent + 1),
            ]
            return "\n".join(lines)

        lines = [
            f"{prefix}Assignment",
            dump_ast(node.target, indent + 1),
            dump_ast(node.value, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, IntegerNode):
        return f"{prefix}Integer {node.value}"

    if isinstance(node, BooleanNode):
        value = "true" if node.value else "false"
        return f"{prefix}Boolean {value}"

    if isinstance(node, IdentifierNode):
        return f"{prefix}Identifier {node.name}"

    if isinstance(node, StringNode):
        return f'{prefix}String "{node.value}"'

    if isinstance(node, ScanNode):
        return f"{prefix}Scan"

    if isinstance(node, FunctionCallNode):
        lines = [f"{prefix}FunctionCall {node.name}"]

        for argument in node.arguments:
            lines.append(dump_ast(argument, indent + 1))

        return "\n".join(lines)

    if isinstance(node, ObjectCreationNode):
        lines = [f"{prefix}ObjectCreation {node.type_name}"]

        for value in node.values:
            lines.append(dump_ast(value, indent + 1))

        return "\n".join(lines)

    if isinstance(node, FieldAccessNode):
        lines = [
            f"{prefix}FieldAccess {node.field_name}",
            dump_ast(node.object, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, MemberCallNode):
        lines = [
            f"{prefix}MemberCall {node.member_name} [chain_end=true]",
            dump_ast(node.object, indent + 1),
        ]

        for argument in node.arguments:
            lines.append(dump_ast(argument, indent + 1))

        return "\n".join(lines)

    if isinstance(node, ComparisonNode):
        lines = [
            f"{prefix}Comparison {node.operator}",
            dump_ast(node.left, indent + 1),
            dump_ast(node.right, indent + 1),
        ]
        return "\n".join(lines)

    if isinstance(node, IfNode):
        lines = [
            f"{prefix}If",
            f"{prefix}  Condition",
            dump_ast(node.condition, indent + 2),
            f"{prefix}  Then",
        ]

        for statement in node.then_body:
            lines.append(dump_ast(statement, indent + 2))

        if node.else_body is not None:
            lines.append(f"{prefix}  Else")

            for statement in node.else_body:
                lines.append(dump_ast(statement, indent + 2))

        return "\n".join(lines)

    raise ValueError(
        f"unsupported AST node: {type(node).__name__}"
    )
