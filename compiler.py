import sys

from errors import CompilationError
from lexer import Lexer
from parser import Parser
from ast_dump import dump_ast


def main():
    ast_mode = False
    input_path = None

    for argument in sys.argv[1:]:
        if argument == "--ast":
            ast_mode = True
        else:
            input_path = argument

    if input_path is not None:
        try:
            with open(input_path, "rb") as source_file:
                source = source_file.read()
        except OSError as error:
            print(f"compilation error: {error}", file=sys.stderr)
            sys.exit(1)
    else:
        source = sys.stdin.buffer.read()

    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()

        parser = Parser(tokens)
        ast = parser.parse_program()

        if ast_mode:
            print(dump_ast(ast))

    except CompilationError as error:
        print(
            f"compilation error: line {error.line}:{error.column}: {error.message}",
            file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
