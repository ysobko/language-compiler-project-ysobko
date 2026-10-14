from dataclasses import dataclass
from enum import Enum


class TokenKind(Enum):
    # Keywords
    GO = "GO"
    HOLD = "HOLD"
    SIGN = "SIGN"
    CHECK = "CHECK"
    DETOUR = "DETOUR"

    # Stage 2 keywords
    ROUTE = "ROUTE"
    ARRIVE = "ARRIVE"
    MAP = "MAP"
    SCAN = "SCAN"
    PRINT = "PRINT"

    # Types
    TYPE_I32 = "TYPE_I32"
    TYPE_I64 = "TYPE_I64"
    TYPE_BOOL = "TYPE_BOOL"

    # Boolean
    GREEN = "GREEN"
    RED = "RED"

    # Operators
    ASSIGN = "ASSIGN"
    ARROW = "ARROW"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"

    CONDITION_MARKER = "CONDITION_MARKER"

    LBRACE = "LBRACE"
    RBRACE = "RBRACE"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COMMA = "COMMA"
    DOT = "DOT"

    INTEGER = "INTEGER"
    STRING = "STRING"
    IDENT = "IDENT"

    NEWLINE = "NEWLINE"

    EOF = "EOF"


@dataclass
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int
