import sys

from errors import CompilationError
from lexer import Lexer
from parser import Parser
from ast_dump import dump_ast


def main():
    source = sys.stdin.buffer.read()

    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse_program()

        if "--ast" in sys.argv:
            print(dump_ast(ast))

    except CompilationError as error:
        print(
            f"compilation error: line {error.line}:{error.column}: {error.message}",
            file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
