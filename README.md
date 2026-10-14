Traffica Compiler

Traffica is a small traffic-themed programming language.

It uses traffic-related keywords and emoji symbols for types and control flow.

Stage 1 introduced variables, constants, assignments, comparisons, and conditional statements.

Stage 2 extends the language with functions, structures, member functions, input, and output.

The full grammar is available in grammar.ebnf.

⸻

Language Features

Types

Traffica has two signed integer types and one boolean type:

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

Integer overflow checking is a semantic rule of the language.

⸻

Mutable Variables

The go keyword declares a mutable variable.

go 🟢 speed <- 60
speed <- 80

⸻

Immutable Variables

The hold keyword declares an immutable variable.

hold 🟢 speed_limit <- 90

⸻

Constants

The sign keyword declares a named constant.

sign 🚦 ROAD_OPEN <- green

⸻

Assignment

The <- operator assigns a value to a variable.

speed <- 80

Values can be integer literals, boolean literals, or identifiers.

speed <- speed_limit
road_open <- green

⸻

Boolean Values

Traffica uses traffic-themed boolean literals:

* green — true
* red — false

Example:

go 🚦 warning <- red
warning <- green

⸻

Comparisons

Traffica provides equality and inequality comparison operators:

* ≡ — equality
* ≠ — inequality

Examples:

speed ≡ speed_limit
speed ≠ speed_limit

⸻

Conditional Statements

check is the equivalent of if.

The 🚥 symbol marks the end of the condition.

check speed ≠ speed_limit 🚥 {
    speed <- speed_limit
}

detour is the equivalent of else and is optional.

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

⸻

Stage 2 Features and Semantic Rules

Functions

Rules

A function call must have exactly the same number of arguments as the function declaration.

Each argument type must match the type of the corresponding parameter.

The value used with arrive must match the declared result type of the function.

A function body can see its parameters, its local variables, and global names.

A function call is an expression, and each function argument is also an expression.

A function may call itself recursively.

A function may call another function declared later in the source file.

Example

The route keyword declares a function. The arrive keyword leaves the function with a value.

route getSpeed(🟢 speed) -> 🟢 {
    arrive speed
}
go 🟢 result <- getSpeed(60)

Because arguments are expressions, function calls may be nested:

go 🟢 result <- getSpeed(getSpeed(60))

⸻

Structures

Rules

A structure defines a named type with typed fields.

Every field is either mutable with go or immutable with hold.

Object creation must provide exactly one value for every field, in the same order in which the fields are declared.

The type of every value used to create an object must match the type of the corresponding field.

A field access must refer to a field that exists in the structure.

Field access may be chained.

Assignment through a field chain is allowed only if the object and every field in the chain are mutable.

Example

The map keyword declares a structure.

map Point {
    go 🟢 x
    go 🟢 y
}
go Point p <- Point{10, 20}

Fields are accessed using .:

print(p.x)

Field access may be chained:

c.center.x

A mutable field of a mutable object may be assigned a new value:

go Point p <- Point{10, 20}
p.x <- 50

⸻

Member Functions

Rules

A member function body can see its parameters, local variables, the fields of the current object, other member functions of the same structure, and global names.

Inside a member function, a name is looked up in this order:

1. parameters and local variables;
2. fields of the current object;
3. global names.

Therefore, if a parameter, a field, and a global name are the same, the parameter is used first.

Other member functions of the same structure are visible by name inside a member function.

A member function that assigns a field is a mutating member function.

A mutating member function may be called only on a mutable object.

A non-mutating member function may be called on both mutable and immutable objects.

Example

A route declared inside a map is a member function.

map Point {
    go 🟢 x
    route getX() -> 🟢 {
        arrive x
    }
    route copyX() -> 🟢 {
        arrive getX()
    }
}
go Point p <- Point{10}
print(p.getX())

A member function that changes a field is mutating:

map Point {
    go 🟢 x
    route setX(🟢 value) -> 🟢 {
        x <- value
        arrive x
    }
}

Calling it on a mutable object is valid:

go Point p <- Point{10}
p.setX(50)

Calling it on an immutable object is invalid:

hold Point p <- Point{10}
p.setX(50)

⸻

Input

Rules

scan() reads exactly one integer from standard input.

The result of scan() has type 🟢 (i32).

Because scan() produces a value, it may be used as an expression.

Example

go 🟢 speed <- scan()

If the input is:

60

then speed receives the value 60.

⸻

Output

Rules

print can print 🟢 integers, 🛣️ integers, 🚦 booleans, string literals, and structure objects.

A boolean is printed as true or false.

An object is printed as its type name followed by its fields in declaration order using this format:

Type{field=value, field=value}

Every print statement writes exactly one newline after the printed value.

Examples

Integer:

print(60)

Output:

60

Boolean:

print(green)
print(red)

Output:

true
false

String literal:

print("Traffica")

Output:

Traffica

Object:

map Point {
    go 🟢 x
    go 🟢 y
}
go Point p <- Point{10, 20}
print(p)

Output:

Point{x=10, y=20}

⸻

Statements and Newlines

Line statements are terminated by newline.

Blank lines are allowed, and spaces and tabs between tokens are ignored.

For example, these are two separate statements:

speed <- 80
warning <- green

⸻

Compiler Structure

The compiler consists of:

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

⸻

Requirements

Python 3 is required.

⸻

Running the Compiler

The compiler can read a source file directly.

To parse a program and print its AST:

python3 compiler.py --ast input.txt

For example:

python3 compiler.py --ast tests/valid/01_all_declarations.src

The compiler also supports reading source code from standard input:

python3 compiler.py --ast < tests/valid/01_all_declarations.src

Without --ast, a valid Stage 1 program is parsed without printing the AST:

python3 compiler.py tests/valid/01_all_declarations.src

⸻

Errors

Lexical and syntax errors are printed to standard error in the following format:

compilation error: line L:C: message

Compilation errors produce a non-zero exit code and no normal program output.

Example:

compilation error: line 4:13: expected comparison operator

⸻

Running the Tests

Run the test suite with:

python3 run_tests.py

The Stage 1 test runner executes all valid and invalid test cases.

Valid programs are parsed with --ast and their output is compared with the corresponding expected AST output.

Invalid programs must produce a non-zero exit code and their error output is compared with the expected error.

The Stage 1 test suite contains:

* 18 valid programs with expected AST dumps
* 19 invalid programs with expected lexical or syntax errors
* 37 test cases in total

A successful Stage 1 test run ends with:

37/37 tests passed

⸻

Grammar

The complete EBNF definition of Traffica is stored in:

grammar.ebnf

It defines the syntax accepted by the Traffica compiler, including the original Stage 1 syntax and the Stage 2 functions, structures, member functions, input/output, expressions, field access, and object creation.
