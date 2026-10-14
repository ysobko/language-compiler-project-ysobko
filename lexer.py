from tokens import Token, TokenKind
from errors import CompilationError


KEYWORDS = {
    "go": TokenKind.GO,
    "hold": TokenKind.HOLD,
    "sign": TokenKind.SIGN,
    "check": TokenKind.CHECK,
    "detour": TokenKind.DETOUR,
    "green": TokenKind.GREEN,
    "red": TokenKind.RED,
}


MULTIBYTE_TOKENS = {
    "🟢".encode("utf-8"): TokenKind.TYPE_I32,
    "🛣️".encode("utf-8"): TokenKind.TYPE_I64,
    "🚦".encode("utf-8"): TokenKind.TYPE_BOOL,
    "🚥".encode("utf-8"): TokenKind.CONDITION_MARKER,
    "≡".encode("utf-8"): TokenKind.EQUAL,
    "≠".encode("utf-8"): TokenKind.NOT_EQUAL,
}


def is_letter(byte):
    return (
        ord("a") <= byte <= ord("z")
        or ord("A") <= byte <= ord("Z")
    )


def is_digit(byte):
    return ord("0") <= byte <= ord("9")


class Lexer:
    def __init__(self, source: bytes):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1

    def peek(self, offset=0):
        pos = self.pos + offset

        if pos >= len(self.source):
            return None

        return self.source[pos]

    def advance(self):
        if self.pos >= len(self.source):
            return None

        byte = self.source[self.pos]
        self.pos += 1

        if byte == ord("\n"):
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return byte

    def skip_whitespace(self):
        while self.peek() in (ord(" "), ord("\t")):
            self.advance()

    def matches(self, sequence):
        end = self.pos + len(sequence)
        return self.source[self.pos:end] == sequence

    def read_identifier(self):
        start_pos = self.pos
        start_line = self.line
        start_column = self.column

        while self.pos < len(self.source):
            byte = self.peek()

            if (
                is_letter(byte)
                or is_digit(byte)
                or byte == ord("_")
            ):
                self.advance()
            else:
                break

        text = self.source[start_pos:self.pos].decode("ascii")
        kind = KEYWORDS.get(text, TokenKind.IDENT)

        return Token(
            kind,
            text,
            start_line,
            start_column
        )

    def read_integer(self):
        start_pos = self.pos
        start_line = self.line
        start_column = self.column

        if self.peek() == ord("-"):
            self.advance()

        while (
            self.pos < len(self.source)
            and is_digit(self.peek())
        ):
            self.advance()

        text = self.source[start_pos:self.pos].decode("ascii")

        return Token(
            TokenKind.INTEGER,
            text,
            start_line,
            start_column
        )

    def read_multibyte_token(self):
        start_line = self.line
        start_column = self.column

        for sequence, kind in MULTIBYTE_TOKENS.items():
            if self.matches(sequence):
                text = sequence.decode("utf-8")

                for _ in range(len(sequence)):
                    self.advance()

                return Token(
                    kind,
                    text,
                    start_line,
                    start_column
                )

        return None

    def tokenize(self):
        tokens = []

        while self.pos < len(self.source):
            byte = self.peek()

            if byte in (ord(" "), ord("\t")):
                self.skip_whitespace()
                continue

            if byte == ord("\n"):
                line = self.line
                column = self.column

                self.advance()

                tokens.append(
                    Token(
                        TokenKind.NEWLINE,
                        "\n",
                        line,
                        column
                    )
                )
                continue

            if is_letter(byte) or byte == ord("_"):
                tokens.append(self.read_identifier())
                continue

            if is_digit(byte):
                tokens.append(self.read_integer())
                continue

            if (
                byte == ord("-")
                and self.peek(1) is not None
                and is_digit(self.peek(1))
            ):
                tokens.append(self.read_integer())
                continue

            if (
                byte == ord("<")
                and self.peek(1) == ord("-")
            ):
                line = self.line
                column = self.column

                self.advance()
                self.advance()

                tokens.append(
                    Token(
                        TokenKind.ASSIGN,
                        "<-",
                        line,
                        column
                    )
                )
                continue

            if byte == ord("{"):
                line = self.line
                column = self.column

                self.advance()

                tokens.append(
                    Token(
                        TokenKind.LBRACE,
                        "{",
                        line,
                        column
                    )
                )
                continue

            if byte == ord("}"):
                line = self.line
                column = self.column

                self.advance()

                tokens.append(
                    Token(
                        TokenKind.RBRACE,
                        "}",
                        line,
                        column
                    )
                )
                continue

            if byte >= 128:
                token = self.read_multibyte_token()

                if token is not None:
                    tokens.append(token)
                    continue

            if byte < 128:
                raise CompilationError(
                    self.line,
                    self.column,
                    f"unexpected byte '{chr(byte)}'"
                )

            raise CompilationError(
                self.line,
                self.column,
                f"unexpected byte 0x{byte:02x}"
            )

        tokens.append(
            Token(
                TokenKind.EOF,
                "",
                self.line,
                self.column
            )
        )

        return tokens
