from dataclasses import dataclass
from enum import Enum


class TokenKind(Enum):
    # Keywords
    GO = "GO"
    HOLD = "HOLD"
    SIGN = "SIGN"
    CHECK = "CHECK"
    DETOUR = "DETOUR"

    TYPE_I32 = "TYPE_I32"
    TYPE_I64 = "TYPE_I64"
    TYPE_BOOL = "TYPE_BOOL"

    # Boolean
    GREEN = "GREEN"
    RED = "RED"

    ASSIGN = "ASSIGN"
    EQUAL = "EQUAL"
    NOT_EQUAL = "NOT_EQUAL"

    CONDITION_MARKER = "CONDITION_MARKER"

    LBRACE = "LBRACE"
    RBRACE = "RBRACE"

    INTEGER = "INTEGER"
    IDENT = "IDENT"

    NEWLINE = "NEWLINE"

    EOF = "EOF"


@dataclass
class Token:
    kind: TokenKind
    text: str
    line: int
    column: int
