from errors import CompilationError
from tokens import Token, TokenKind
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


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset=0):
        pos = self.pos + offset

        if pos >= len(self.tokens):
            return self.tokens[-1]

        return self.tokens[pos]

    def eat(self, kind: TokenKind):
        token = self.peek()

        if token.kind != kind:
            raise CompilationError(
                token.line,
                token.column,
                f"expected {kind.value}, got {token.kind.value}"
            )

        self.pos += 1
        return token

    def parse_value(self):
        token = self.peek()

        if token.kind == TokenKind.INTEGER:
            self.eat(TokenKind.INTEGER)

            return IntegerNode(
                line=token.line,
                column=token.column,
                value=int(token.text)
            )

        if token.kind == TokenKind.GREEN:
            self.eat(TokenKind.GREEN)

            return BooleanNode(
                line=token.line,
                column=token.column,
                value=True
            )

        if token.kind == TokenKind.RED:
            self.eat(TokenKind.RED)

            return BooleanNode(
                line=token.line,
                column=token.column,
                value=False
            )

        if token.kind == TokenKind.IDENT:
            self.eat(TokenKind.IDENT)

            return IdentifierNode(
                line=token.line,
                column=token.column,
                name=token.text
            )

        raise CompilationError(
            token.line,
            token.column,
            "expected value"
        )

    def parse_type(self):
        token = self.peek()

        if token.kind == TokenKind.TYPE_I32:
            self.eat(TokenKind.TYPE_I32)
            return token.text

        if token.kind == TokenKind.TYPE_I64:
            self.eat(TokenKind.TYPE_I64)
            return token.text

        if token.kind == TokenKind.TYPE_BOOL:
            self.eat(TokenKind.TYPE_BOOL)
            return token.text

        raise CompilationError(
            token.line,
            token.column,
            "expected type"
        )

    def parse_mutable_decl(self):
        go_token = self.eat(TokenKind.GO)

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_value()

        return MutableDeclNode(
            line=go_token.line,
            column=go_token.column,
            type_name=type_name,
            name=name_token.text,
            value=value
        )

    def parse_immutable_decl(self):
        hold_token = self.eat(TokenKind.HOLD)

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_value()

        return ImmutableDeclNode(
            line=hold_token.line,
            column=hold_token.column,
            type_name=type_name,
            name=name_token.text,
            value=value
        )

    def parse_constant_decl(self):
        sign_token = self.eat(TokenKind.SIGN)

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_value()

        return ConstantDeclNode(
            line=sign_token.line,
            column=sign_token.column,
            type_name=type_name,
            name=name_token.text,
            value=value
        )

    def parse_decl(self):
        token = self.peek()

        if token.kind == TokenKind.GO:
            return self.parse_mutable_decl()

        if token.kind == TokenKind.HOLD:
            return self.parse_immutable_decl()

        if token.kind == TokenKind.SIGN:
            return self.parse_constant_decl()

        raise CompilationError(
            token.line,
            token.column,
            "expected declaration"
        )

    def parse_assignment(self):
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_value()

        return AssignmentNode(
            line=name_token.line,
            column=name_token.column,
            name=name_token.text,
            value=value
        )

    def parse_line_statement(self):
        token = self.peek()

        if token.kind in (
            TokenKind.GO,
            TokenKind.HOLD,
            TokenKind.SIGN,
        ):
            return self.parse_decl()

        if token.kind == TokenKind.IDENT:
            return self.parse_assignment()

        raise CompilationError(
            token.line,
            token.column,
            "expected statement"
        )

    def parse_comp_op(self):
        token = self.peek()

        if token.kind == TokenKind.EQUAL:
            return self.eat(TokenKind.EQUAL)

        if token.kind == TokenKind.NOT_EQUAL:
            return self.eat(TokenKind.NOT_EQUAL)

        raise CompilationError(
            token.line,
            token.column,
            "expected comparison operator"
        )

    def parse_comparison(self):
        left = self.parse_value()

        operator_token = self.parse_comp_op()

        right = self.parse_value()

        return ComparisonNode(
            line=left.line,
            column=left.column,
            left=left,
            operator=operator_token.text,
            right=right
        )

    def parse_statement(self):
        token = self.peek()

        if token.kind in (
            TokenKind.GO,
            TokenKind.HOLD,
            TokenKind.SIGN,
            TokenKind.IDENT,
        ):
            statement = self.parse_line_statement()
            self.eat(TokenKind.NEWLINE)
            return statement

        if token.kind == TokenKind.CHECK:
            return self.parse_if_statement()

        raise CompilationError(
            token.line,
            token.column,
            "expected statement"
        )

    def parse_block(self):
        statements = []

        while self.peek().kind == TokenKind.NEWLINE:
            self.eat(TokenKind.NEWLINE)

        while self.peek().kind not in (
            TokenKind.RBRACE,
            TokenKind.EOF,
        ):
            statements.append(self.parse_statement())

            while self.peek().kind == TokenKind.NEWLINE:
                self.eat(TokenKind.NEWLINE)

        if not statements:
            token = self.peek()

            raise CompilationError(
                token.line,
                token.column,
                "block must contain at least one statement"
            )

        return statements

    def parse_if_statement(self):
        check_token = self.eat(TokenKind.CHECK)

        condition = self.parse_comparison()

        self.eat(TokenKind.CONDITION_MARKER)
        self.eat(TokenKind.LBRACE)
        self.eat(TokenKind.NEWLINE)

        then_body = self.parse_block()

        self.eat(TokenKind.RBRACE)

        else_body = None

        if self.peek().kind == TokenKind.DETOUR:
            self.eat(TokenKind.DETOUR)
            self.eat(TokenKind.LBRACE)
            self.eat(TokenKind.NEWLINE)

            else_body = self.parse_block()

            self.eat(TokenKind.RBRACE)

        self.eat(TokenKind.NEWLINE)

        return IfNode(
            line=check_token.line,
            column=check_token.column,
            condition=condition,
            then_body=then_body,
            else_body=else_body
        )

    def parse_program(self):
        statements = []

        while self.peek().kind != TokenKind.EOF:
            if self.peek().kind == TokenKind.NEWLINE:
                self.eat(TokenKind.NEWLINE)
                continue

            statements.append(self.parse_statement())

        self.eat(TokenKind.EOF)

        return ProgramNode(
            line=1,
            column=1,
            statements=statements
        )
