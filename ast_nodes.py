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


@dataclass
class IntegerNode(ExprNode):
    value: int


@dataclass
class BooleanNode(ExprNode):
    value: bool


@dataclass
class IdentifierNode(ExprNode):
    name: str


@dataclass
class ComparisonNode(ExprNode):
    left: ExprNode
    operator: str
    right: ExprNode


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
    name: str
    value: ExprNode


@dataclass
class IfNode(StmtNode):
    condition: ComparisonNode
    then_body: list[StmtNode]
    else_body: list[StmtNode] | None
