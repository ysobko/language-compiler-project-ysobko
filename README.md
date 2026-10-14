Traffic Language Compiler

Traffic Language is small traffic-themed programming language.

It uses traffic-related keywords and emoji symbols for types and control flow. Stage 1 compiler contains hand-written byte lexer and recursive-descent parser that builds AST.

Full  grammar is available in grammar.ebnf.

Language Features:

Types

Traffic Language has 2 signed int types and 1 boolean type:

* 🟢 — signed 32-bit integer (i32)
* 🛣️ — signed 64-bit integer (i64)
* 🚦 — boolean

Example:

go 🟢 speed <- 60
go 🛣️ distance <- 5000000000
go 🚦 road_open <- green

Integer ranges are:

🟢  -2147483648 .. 2147483647
🛣️  -9223372036854775808 .. 9223372036854775807

Integer overflow checking is semantic rule of language. Semantic checks aren't performed in Stage 1 lexer and parser.

Mutable Variables

The 'go' keyword declares mutable variable.

go 🟢 speed <- 60
speed <- 80

Immutable Variables

The 'hold' keyword declares immutable variable.

hold 🟢 speed_limit <- 90

Constants

The 'sign' keyword declares named constant.

sign 🚦 ROAD_OPEN <- green

Assignment

The <- operator assigns value to variable.

speed <- 80

Values can be integer literals, boolean literals or identifiers.

speed <- speed_limit
road_open <- green

Boolean Values

Traffic Language uses traffic-themed boolean literals:

* green — true
* red — false

Example:

go 🚦 warning <- red
warning <- green

Comparisons

Language provides equality and inequality comparison operators:

* ≡ — equality
* ≠ — inequality

Examples:

speed ≡ speed_limit
speed ≠ speed_limit

Conditional Statements

'check' is the equivalent of if.

The 🚥 symbol marks the end of condition.

check speed ≠ speed_limit 🚥 {
    speed <- speed_limit
}

'detour' is the equivalent of else and is optional.

check speed ≠ speed_limit 🚥 {
    speed <- speed_limit
} detour {
    speed <- 0
}

Both check and detour blocks must contain at least one statement.

Conditional statements can also be nested:

check speed ≠ speed_limit 🚥 {
    check road_open ≡ green 🚥 {
        speed <- speed_limit
    }
}

Statements and Newlines

Line statements are terminated by newline. Blank lines are allowed and spaces and tabs between tokens are ignored.

For example, these are 2 separate statements:

speed <- 80
warning <- green

Compiler Structure

The Stage 1 compiler consists of:

* lexer.py — hand-written byte lexer
* tokens.py — token kinds and token representation
* parser.py — recursive-descent parser
* ast_nodes.py — AST node hierarchy
* ast_dump.py — stable textual AST representation
* errors.py — compilation error representation
* compiler.py — compiler command-line entry point
* grammar.ebnf — complete EBNF grammar
* tests/ — valid and invalid test programs
* run_tests.py — automated test runner

Requirements

Python 3 is required.

No third-party Python packages are needed.

Running the Compiler

The compiler can read source file directly.

To parse program and print its AST:

python3 compiler.py --ast input.txt

For example:

python3 compiler.py --ast tests/valid/01_all_declarations.src

The compiler also supports reading source code from standard input:

python3 compiler.py --ast < tests/valid/01_all_declarations.src

Without --ast, a valid program is parsed without printing the AST:

python3 compiler.py tests/valid/01_all_declarations.src

Errors

Lexical and syntax errors are printed to standard error in the following format:

compilation error: line L:C: message

Compilation errors produce non-zero exit code and no normal program output.

Example:

compilation error: line 4:13: expected comparison operator

Running the Tests

Run the complete test suite with:

python3 run_tests.py

The test runner executes all valid and invalid test cases.

Valid programs are parsed with --ast and their output is compared with the corresponding .ast files.

Invalid programs must produce non-zero exit code and their error output is compared with the corresponding .err files.

The current test suite contains:

* 18 valid programs with expected AST dumps
* 19 invalid programs with expected lexical or syntax errors
* 37 test cases in total

A successful run ends with:

37/37 tests passed

Grammar

The complete EBNF definition of Traffic Language is stored in:

grammar.ebnf

It defines syntax accepted by Stage 1 parser, including declarations, assignments, comparisons, conditional statements, blocks, identifiers, integer literals, and boolean literals.
