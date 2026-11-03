import argparse
import sys
from pathlib import Path

from errors import CompilationError
from lexer import Lexer
from parser import Parser
from ast_dump import dump_ast
from semantic import SemanticAnalyzer
from codegen import LLVMCodeGenerator
from optimizer import ASTOptimizer


def main():
    argument_parser = argparse.ArgumentParser(
        description="Traffica compiler"
    )

    argument_parser.add_argument(
        "input",
        nargs="?",
        help="Source file (stdin if omitted)"
    )

    argument_parser.add_argument(
        "output_file",
        nargs="?",
        help="LLVM IR output file"
    )

    modes = argument_parser.add_mutually_exclusive_group()

    modes.add_argument(
        "--ast",
        action="store_true"
    )

    modes.add_argument(
        "--ir",
        action="store_true"
    )

    argument_parser.add_argument(
        "-o",
        "--output",
        help="LLVM IR output file"
    )

    argument_parser.add_argument(
        "--optimize",
        action="store_true",
        help="Optimize the AST before LLVM code generation"
    )

    args = argument_parser.parse_args()

    if args.input:
        try:
            source = Path(args.input).read_bytes()
        except OSError as error:
            print(
                f"compilation error: {error}",
                file=sys.stderr
            )
            sys.exit(1)
    else:
        source = sys.stdin.buffer.read()

    try:
        tokens = Lexer(source).tokenize()
        ast = Parser(tokens).parse_program()

        # Preserve the original --ast behavior.
        if args.ast and not args.optimize:
            print(dump_ast(ast))
            return

        # Check the original program before optimization.
        symbols = SemanticAnalyzer().analyze(ast)

        if args.optimize:
            ast = ASTOptimizer().optimize(ast)
            # Rebuild symbols for the optimized program.
            symbols = SemanticAnalyzer().analyze(ast)

        if args.ast:
            print(dump_ast(ast))
            return

        generator = LLVMCodeGenerator(symbols)
        llvm_ir = generator.ir_text(ast)

        if args.ir:
            print(llvm_ir)
            return

        if args.output and args.output_file:
            argument_parser.error(
                "use either positional output file or -o, not both"
            )

        if args.output_file:
            output_path = Path(args.output_file)
        elif args.output:
            output_path = Path(args.output)
        elif args.input:
            output_path = Path(args.input).with_suffix(".ll")
        else:
            output_path = Path("output.ll")

        output_path.write_text(llvm_ir)

        print(f"LLVM IR written to {output_path}")

    except CompilationError as error:
        print(
            f"compilation error: line {error.line}:{error.column}: {error.message}",
            file=sys.stderr
        )
        sys.exit(1)

    except (OSError, ValueError, KeyError, NotImplementedError) as error:
        print(
            f"compilation error: {error}",
            file=sys.stderr
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
