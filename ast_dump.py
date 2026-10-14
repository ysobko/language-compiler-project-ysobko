from ast_nodes import (
    ProgramNode,
    IntegerNode,
    BooleanNode,
    IdentifierNode,
    ComparisonNode,
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
        lines = [
            f"{prefix}Assignment {node.name}",
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
