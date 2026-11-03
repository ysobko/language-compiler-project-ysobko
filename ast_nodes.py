from dataclasses import dataclass


@dataclass
class ASTNode:
    line: int
    column: int


@dataclass
class StmtNode(ASTNode):
    pass


@dataclass
class ExprNode(ASTNode):
    pass


@dataclass
class ProgramNode(ASTNode):
    statements: list[StmtNode]


# Expressions

@dataclass
class IntegerNode(ExprNode):
    value: int


@dataclass
class BooleanNode(ExprNode):
    value: bool


@dataclass
class StringNode(ExprNode):
    value: str


@dataclass
class IdentifierNode(ExprNode):
    name: str


@dataclass
class ComparisonNode(ExprNode):
    left: ExprNode
    operator: str
    right: ExprNode


@dataclass
class BinaryOpNode(ExprNode):
    left: ExprNode
    operator: str
    right: ExprNode


@dataclass
class FunctionCallNode(ExprNode):
    name: str
    arguments: list[ExprNode]
    is_pipe_stage: bool = False


@dataclass
class ObjectCreationNode(ExprNode):
    type_name: str
    values: list[ExprNode]


@dataclass
class FieldAccessNode(ExprNode):
    object: ExprNode
    field_name: str


@dataclass
class MemberCallNode(ExprNode):
    object: ExprNode
    member_name: str
    arguments: list[ExprNode]


@dataclass
class ScanNode(ExprNode):
    pass


# Declarations and assignments

@dataclass
class MutableDeclNode(StmtNode):
    type_name: str
    name: str
    value: ExprNode


@dataclass
class ImmutableDeclNode(StmtNode):
    type_name: str
    name: str
    value: ExprNode


@dataclass
class ConstantDeclNode(StmtNode):
    type_name: str
    name: str
    value: ExprNode


@dataclass
class AssignmentNode(StmtNode):
    target: ExprNode
    value: ExprNode


# Control flow

@dataclass
class IfNode(StmtNode):
    condition: ComparisonNode
    then_body: list[StmtNode]
    else_body: list[StmtNode] | None


@dataclass
class ReturnNode(StmtNode):
    value: ExprNode


# Functions

@dataclass
class ParameterNode(ASTNode):
    type_name: str
    name: str


@dataclass
class FunctionDeclNode(StmtNode):
    name: str
    parameters: list[ParameterNode]
    result_type: str
    body: list[StmtNode]


# Structures

@dataclass
class FieldDeclNode(ASTNode):
    mutable: bool
    type_name: str
    name: str


@dataclass
class StructDeclNode(StmtNode):
    name: str
    fields: list[FieldDeclNode]
    member_functions: list[FunctionDeclNode]



@dataclass
class ExpressionStmtNode(StmtNode):
    expression: ExprNode


@dataclass
class PrintNode(StmtNode):
    value: ExprNode

@dataclass
class InlineBlockNode(StmtNode):
    """Internal optimizer node containing statements in a local scope."""
    statements: list[StmtNode]
