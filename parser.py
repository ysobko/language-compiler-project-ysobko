from errors import CompilationError
from tokens import Token, TokenKind
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

    def parse_expression(self, allow_object_creation=True):
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

        if token.kind == TokenKind.SCAN:
            scan_token = self.eat(TokenKind.SCAN)
            self.eat(TokenKind.LPAREN)
            self.eat(TokenKind.RPAREN)

            return ScanNode(
                line=scan_token.line,
                column=scan_token.column
            )

        if token.kind == TokenKind.IDENT:
            return self.parse_identifier_expression(
                allow_object_creation=allow_object_creation
            )

        raise CompilationError(
            token.line,
            token.column,
            "expected value"
        )

    def parse_argument_list(self):
        arguments = []

        if self.peek().kind == TokenKind.RPAREN:
            return arguments

        arguments.append(self.parse_expression())

        while self.peek().kind == TokenKind.COMMA:
            self.eat(TokenKind.COMMA)
            arguments.append(self.parse_expression())

        return arguments

    def parse_object_values(self):
        values = []

        if self.peek().kind == TokenKind.RBRACE:
            return values

        values.append(self.parse_expression())

        while self.peek().kind == TokenKind.COMMA:
            self.eat(TokenKind.COMMA)
            values.append(self.parse_expression())

        return values

    def parse_identifier_expression(self, allow_object_creation=True):
        name_token = self.eat(TokenKind.IDENT)

        # Function call: getSpeed(...)
        if self.peek().kind == TokenKind.LPAREN:
            self.eat(TokenKind.LPAREN)
            arguments = self.parse_argument_list()
            self.eat(TokenKind.RPAREN)

            return FunctionCallNode(
                line=name_token.line,
                column=name_token.column,
                name=name_token.text,
                arguments=arguments
            )

        # Object creation: Point{10, 20}
        if (
            allow_object_creation
            and self.peek().kind == TokenKind.LBRACE
        ):
            self.eat(TokenKind.LBRACE)
            values = self.parse_object_values()
            self.eat(TokenKind.RBRACE)

            return ObjectCreationNode(
                line=name_token.line,
                column=name_token.column,
                type_name=name_token.text,
                values=values
            )

        expression = IdentifierNode(
            line=name_token.line,
            column=name_token.column,
            name=name_token.text
        )

        # Field access / member call:
        # p.x
        # c.center.x
        # p.getX()
        while self.peek().kind == TokenKind.DOT:
            self.eat(TokenKind.DOT)
            member_token = self.eat(TokenKind.IDENT)

            if self.peek().kind == TokenKind.LPAREN:
                self.eat(TokenKind.LPAREN)
                arguments = self.parse_argument_list()
                self.eat(TokenKind.RPAREN)

                expression = MemberCallNode(
                    line=member_token.line,
                    column=member_token.column,
                    object=expression,
                    member_name=member_token.text,
                    arguments=arguments
                )

                # According to grammar.ebnf, a member call may only
                # appear at the end of a chain.
                break
            else:
                expression = FieldAccessNode(
                    line=member_token.line,
                    column=member_token.column,
                    object=expression,
                    field_name=member_token.text
                )

        return expression

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

        if token.kind == TokenKind.IDENT:
            self.eat(TokenKind.IDENT)
            return token.text

        raise CompilationError(
            token.line,
            token.column,
            "expected type"
        )

    def parse_parameter(self):
        type_token = self.peek()
        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        return ParameterNode(
            line=type_token.line,
            column=type_token.column,
            type_name=type_name,
            name=name_token.text
        )

    def parse_parameter_list(self):
        parameters = []

        if self.peek().kind == TokenKind.RPAREN:
            return parameters

        parameters.append(self.parse_parameter())

        while self.peek().kind == TokenKind.COMMA:
            self.eat(TokenKind.COMMA)
            parameters.append(self.parse_parameter())

        return parameters

    def parse_mutable_decl(self):
        go_token = self.eat(TokenKind.GO)

        if (
            self.peek().kind == TokenKind.IDENT
            and self.peek(1).kind == TokenKind.ASSIGN
        ):
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "expected type"
            )

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_expression()

        return MutableDeclNode(
            line=go_token.line,
            column=go_token.column,
            type_name=type_name,
            name=name_token.text,
            value=value
        )

    def parse_immutable_decl(self):
        hold_token = self.eat(TokenKind.HOLD)

        if (
            self.peek().kind == TokenKind.IDENT
            and self.peek(1).kind == TokenKind.ASSIGN
        ):
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "expected type"
            )

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_expression()

        return ImmutableDeclNode(
            line=hold_token.line,
            column=hold_token.column,
            type_name=type_name,
            name=name_token.text,
            value=value
        )

    def parse_constant_decl(self):
        sign_token = self.eat(TokenKind.SIGN)

        if (
            self.peek().kind == TokenKind.IDENT
            and self.peek(1).kind == TokenKind.ASSIGN
        ):
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "expected type"
            )

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.ASSIGN)

        value = self.parse_expression()

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

        target = IdentifierNode(
            line=name_token.line,
            column=name_token.column,
            name=name_token.text
        )

        while self.peek().kind == TokenKind.DOT:
            self.eat(TokenKind.DOT)
            field_token = self.eat(TokenKind.IDENT)

            target = FieldAccessNode(
                line=field_token.line,
                column=field_token.column,
                object=target,
                field_name=field_token.text
            )

        self.eat(TokenKind.ASSIGN)

        value = self.parse_expression()

        return AssignmentNode(
            line=name_token.line,
            column=name_token.column,
            target=target,
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

        if token.kind == TokenKind.PRINT:
            return self.parse_print_statement()

        if token.kind == TokenKind.IDENT:
            start_pos = self.pos

            expression = self.parse_expression()

            if self.peek().kind == TokenKind.ASSIGN:
                self.pos = start_pos
                return self.parse_assignment()

            if isinstance(expression, (FunctionCallNode, MemberCallNode)):
                return ExpressionStmtNode(
                    line=expression.line,
                    column=expression.column,
                    expression=expression
                )

            raise CompilationError(
                token.line,
                token.column,
                "expected assignment or function call"
            )

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
        # Grammar:
        # comparison ::= expression compOp expression
        #
        # The left side can always be parsed as a full expression.
        left = self.parse_expression()

        operator_token = self.parse_comp_op()

        # On the right side, IDENT "{" is ambiguous:
        #
        #   check a ≡ Point{10} 🚥 {   -> object creation
        #   check a ≡ b {              -> missing 🚥 before if body
        #
        # Try object creation first. It is accepted only when the
        # resulting expression is followed by the condition marker.
        if (
            self.peek().kind == TokenKind.IDENT
            and self.peek(1).kind == TokenKind.LBRACE
        ):
            start_pos = self.pos

            try:
                right = self.parse_expression()

                if self.peek().kind != TokenKind.CONDITION_MARKER:
                    self.pos = start_pos
                    right = self.parse_expression(
                        allow_object_creation=False
                    )
            except CompilationError:
                self.pos = start_pos
                right = self.parse_expression(
                    allow_object_creation=False
                )
        else:
            right = self.parse_expression()

        return ComparisonNode(
            line=left.line,
            column=left.column,
            left=left,
            operator=operator_token.text,
            right=right
        )

    def parse_print_statement(self):
        print_token = self.eat(TokenKind.PRINT)

        self.eat(TokenKind.LPAREN)

        if self.peek().kind == TokenKind.STRING:
            string_token = self.eat(TokenKind.STRING)
            value = StringNode(
                line=string_token.line,
                column=string_token.column,
                value=string_token.text
            )
        else:
            value = self.parse_expression()

        self.eat(TokenKind.RPAREN)

        return PrintNode(
            line=print_token.line,
            column=print_token.column,
            value=value
        )

    def parse_return_statement(self):
        arrive_token = self.eat(TokenKind.ARRIVE)
        value = self.parse_expression()

        return ReturnNode(
            line=arrive_token.line,
            column=arrive_token.column,
            value=value
        )

    def parse_statement(self):
        token = self.peek()

        if token.kind in (
            TokenKind.GO,
            TokenKind.HOLD,
            TokenKind.SIGN,
            TokenKind.IDENT,
            TokenKind.PRINT,
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

    def parse_function_body(self):
        statements = []

        while self.peek().kind == TokenKind.NEWLINE:
            self.eat(TokenKind.NEWLINE)

        while self.peek().kind not in (
            TokenKind.RBRACE,
            TokenKind.EOF,
        ):
            if self.peek().kind == TokenKind.ARRIVE:
                statement = self.parse_return_statement()
                self.eat(TokenKind.NEWLINE)

            elif self.peek().kind == TokenKind.CHECK:
                statement = self.parse_function_if_statement()

            else:
                statement = self.parse_statement()

            statements.append(statement)

            while self.peek().kind == TokenKind.NEWLINE:
                self.eat(TokenKind.NEWLINE)

        if not statements:
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "function body must contain at least one statement"
            )

        return statements

    def parse_function_if_statement(self):
        check_token = self.eat(TokenKind.CHECK)

        condition = self.parse_comparison()

        self.eat(TokenKind.CONDITION_MARKER)
        self.eat(TokenKind.LBRACE)
        self.eat(TokenKind.NEWLINE)

        then_body = self.parse_function_body()

        self.eat(TokenKind.RBRACE)

        else_body = None

        if self.peek().kind == TokenKind.DETOUR:
            self.eat(TokenKind.DETOUR)
            self.eat(TokenKind.LBRACE)
            self.eat(TokenKind.NEWLINE)

            else_body = self.parse_function_body()

            self.eat(TokenKind.RBRACE)

        self.eat(TokenKind.NEWLINE)

        return IfNode(
            line=check_token.line,
            column=check_token.column,
            condition=condition,
            then_body=then_body,
            else_body=else_body
        )

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

    def parse_field_decl(self):
        token = self.peek()

        if token.kind == TokenKind.GO:
            start_token = self.eat(TokenKind.GO)
            mutable = True
        elif token.kind == TokenKind.HOLD:
            start_token = self.eat(TokenKind.HOLD)
            mutable = False
        else:
            raise CompilationError(
                token.line,
                token.column,
                "expected field declaration"
            )

        type_name = self.parse_type()
        name_token = self.eat(TokenKind.IDENT)

        return FieldDeclNode(
            line=start_token.line,
            column=start_token.column,
            mutable=mutable,
            type_name=type_name,
            name=name_token.text
        )

    def parse_struct_decl(self):
        map_token = self.eat(TokenKind.MAP)
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.LBRACE)
        self.eat(TokenKind.NEWLINE)

        fields = []
        member_functions = []

        while self.peek().kind == TokenKind.NEWLINE:
            self.eat(TokenKind.NEWLINE)

        # grammar.ebnf requires at least one struct member.
        if self.peek().kind == TokenKind.RBRACE:
            token = self.peek()
            raise CompilationError(
                token.line,
                token.column,
                "structure body must contain at least one member"
            )

        while self.peek().kind not in (
            TokenKind.RBRACE,
            TokenKind.EOF,
        ):
            if self.peek().kind in (
                TokenKind.GO,
                TokenKind.HOLD,
            ):
                fields.append(self.parse_field_decl())
                self.eat(TokenKind.NEWLINE)

            elif self.peek().kind == TokenKind.ROUTE:
                member_functions.append(self.parse_function_decl())

            else:
                token = self.peek()
                raise CompilationError(
                    token.line,
                    token.column,
                    "expected field or member function"
                )

            while self.peek().kind == TokenKind.NEWLINE:
                self.eat(TokenKind.NEWLINE)

        self.eat(TokenKind.RBRACE)
        self.eat(TokenKind.NEWLINE)

        return StructDeclNode(
            line=map_token.line,
            column=map_token.column,
            name=name_token.text,
            fields=fields,
            member_functions=member_functions
        )

    def parse_function_decl(self):
        route_token = self.eat(TokenKind.ROUTE)
        name_token = self.eat(TokenKind.IDENT)

        self.eat(TokenKind.LPAREN)
        parameters = self.parse_parameter_list()
        self.eat(TokenKind.RPAREN)

        self.eat(TokenKind.ARROW)
        result_type = self.parse_type()

        self.eat(TokenKind.LBRACE)
        self.eat(TokenKind.NEWLINE)

        body = self.parse_function_body()

        self.eat(TokenKind.RBRACE)
        self.eat(TokenKind.NEWLINE)

        return FunctionDeclNode(
            line=route_token.line,
            column=route_token.column,
            name=name_token.text,
            parameters=parameters,
            result_type=result_type,
            body=body
        )

    def parse_program(self):
        statements = []

        while self.peek().kind != TokenKind.EOF:
            if self.peek().kind == TokenKind.NEWLINE:
                self.eat(TokenKind.NEWLINE)
                continue

            if self.peek().kind == TokenKind.ROUTE:
                statements.append(self.parse_function_decl())
            elif self.peek().kind == TokenKind.MAP:
                statements.append(self.parse_struct_decl())
            else:
                statements.append(self.parse_statement())

        self.eat(TokenKind.EOF)

        return ProgramNode(
            line=1,
            column=1,
            statements=statements
        )
