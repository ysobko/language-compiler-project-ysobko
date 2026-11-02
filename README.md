# Traffica Compiler

Traffica is a small traffic-themed programming language with custom keywords and emoji-based types. Its compiler is written in Python and generates LLVM IR using `llvmlite`.

- **Stage 1:** Variables, constants, assignments, comparisons, and conditional statements.
- **Stage 2:** Functions, structures, member functions, arithmetic, input/output, semantic analysis, and LLVM code generation.

The complete language grammar is defined in [`grammar.ebnf`](grammar.ebnf).

## 1. Getting Started

### Requirements

- Python 3
- `llvmlite`
- Clang

Install the Python dependency:

```bash
python3 -m pip install llvmlite
```

### Running the Compiler

Generate LLVM IR from a source file:

```bash
python3 compiler.py program.src
```

This creates `program.ll`.

Compile and run the generated program:

```bash
clang program.ll -o program
./program
```

Other compiler options:

```bash
python3 compiler.py --ast program.src
python3 compiler.py --ir program.src
python3 compiler.py program.src -o output.ll
python3 compiler.py --help
```

The compiler can also read source code from standard input.

## 2. Language Features

### Types

Traffica supports three primitive types:

| Type | Meaning | Range |
|---|---|---|
| 🟢 | Signed 32-bit integer (`i32`) | -2147483648 to 2147483647 |
| 🛣️ | Signed 64-bit integer (`i64`) | -9223372036854775808 to 9223372036854775807 |
| 🚦 | Boolean | `green` or `red` |

`green` represents `true`, and `red` represents `false`.

### Variables and Constants

Traffica uses three declaration keywords:

- `go` — mutable variable.
- `hold` — immutable variable.
- `sign` — named constant.

```text
go 🟢 speed <- 60
hold 🟢 speed_limit <- 90
sign 🚦 ROAD_OPEN <- green

speed <- 80
```

Assignments use the `<-` operator. Assigning to an immutable variable or constant is not allowed.

### Arithmetic and Comparisons

Supported arithmetic operators are `+`, `-`, and `*`.

Multiplication has higher precedence than addition and subtraction. Parentheses can change the evaluation order.

```text
go 🟢 x <- 10 + 5 * 2
go 🟢 y <- (10 + 5) * 2

print(x)
print(y)
```

Output:

```text
20
30
```

Arithmetic requires compatible integer types; booleans cannot be used as arithmetic operands.

Comparison operators:

- `≡` — equality.
- `≠` — inequality.

### Conditional Statements

`check` is equivalent to `if`, and `detour` is an optional `else`. The `🚥` symbol separates the condition from its block.

```text
go 🟢 speed <- 60
hold 🟢 limit <- 90

check speed ≠ limit 🚥 {
    speed <- limit
} detour {
    speed <- 0
}
```

Both `check` and `detour` blocks must contain at least one statement. Nested conditionals are supported.

### Functions

Functions are declared using `route` and return values using `arrive`.

```text
route getSpeed(🟢 speed) -> 🟢 {
    arrive speed
}

go 🟢 result <- getSpeed(60)
```

Function calls are expressions, so nested calls are supported:

```text
go 🟢 result <- getSpeed(getSpeed(60))
```

Functions may be recursive and may call functions declared later in the source file.

### Structures

Structures are declared using `map`. Fields have types and are declared with `go` or `hold`.

```text
map Point {
    go 🟢 x
    go 🟢 y
}

go Point p <- Point{10, 20}

print(p.x)

p.x <- 50
```

Object initialization provides field values in declaration order.

Nested structures and chained field access are supported:

```text
c.center.x
```

### Member Functions

Functions declared inside structures are member functions.

```text
map Counter {
    go 🟢 value

    route increment(🟢 amount) -> 🟢 {
        value <- value + amount
        arrive value
    }
}

go Counter counter <- Counter{10}
print(counter.increment(5))
```

Output:

```text
15
```

Member functions can access the current object's fields and other member functions of the same structure.

### Input and Output

`scan()` reads one integer from standard input and returns an `🟢` (`i32`) value.

```text
go 🟢 speed <- scan()
print(speed)
```

`print()` supports integers, booleans, strings, and structure objects.

Booleans are printed as `true` or `false`. Every `print()` statement ends with a newline.

Objects are printed using their type name and fields in declaration order:

```text
Point{x=10, y=20}
```

### Statements and Newlines

Statements are separated by newlines. Blank lines are allowed, and spaces and tabs between tokens are ignored.

## 3. Semantic Rules

Semantic analysis runs as a separate pass over the AST before LLVM code generation.

### Scope and Declarations

- Variables must be declared before use.
- A name cannot be declared twice in the same scope.
- Functions can access their parameters, local variables, and global names.
- Member functions resolve names in this order:
  1. Parameters and local variables.
  2. Fields of the current object.
  3. Global names.

### Type Checking

- Assignments must respect declared types.
- Function calls must provide the correct number and types of arguments.
- The expression used with `arrive` must match the function's declared return type.
- Object initialization must provide exactly one value per field, in declaration order, with matching types.
- Field access must reference an existing field.

### Mutability

- `go` variables are mutable.
- `hold` variables and `sign` constants cannot be reassigned.
- Assignment through a field chain is allowed only when the object and every field in the chain are mutable.
- A member function that assigns a field is considered mutating.
- Mutating member functions cannot be called on immutable objects.
- Non-mutating member functions can be called on mutable or immutable objects.

### Integer Overflow

Traffica uses signed 32-bit and 64-bit integers.

Integer literals and constant arithmetic expressions are checked during semantic analysis against the supported ranges.

Arithmetic involving runtime values uses LLVM signed overflow checks. If an operation overflows, the generated program terminates using `abort()`.

## 4. Compiler Architecture

The compiler uses the following pipeline:

```text
Source Code
    |
    v
Lexer
    |
    v
Parser
    |
    v
AST
    |
    v
Semantic Analysis + Symbol Table
    |
    v
LLVM IR Code Generation
    |
    v
LLVM IR (.ll)
    |
    v
Clang
    |
    v
Executable
```

### Project Structure

| File | Responsibility |
|---|---|
| `lexer.py` | Hand-written byte lexer |
| `tokens.py` | Token definitions |
| `parser.py` | Recursive-descent parser |
| `ast_nodes.py` | AST node definitions |
| `ast_dump.py` | Textual AST representation |
| `symbols.py` | Symbol table |
| `semantic.py` | Semantic analysis and type checking |
| `codegen.py` | LLVM IR generation |
| `compiler.py` | Compiler CLI |
| `errors.py` | Compilation errors |
| `grammar.ebnf` | Language grammar |
| `run_tests.py` | Stage 1 test runner |
| `tests/` | Valid and invalid Stage 1 programs |

### LLVM Code Generation

LLVM IR is generated using the `llvmlite.ir` builder API.

- Variables and arithmetic use the appropriate integer widths.
- Conditionals use basic blocks and conditional branches.
- Functions are declared before their bodies are generated, allowing forward calls.
- User-defined functions receive prefixes to avoid runtime naming conflicts.
- Structures use LLVM identified types.
- Field access uses `getelementptr` with field indices from the symbol table.
- Member functions receive the object's pointer as their first argument.
- Input and output use external `scanf` and `printf` declarations.
- Format strings are stored as global constants.
- `i32` values use `%d`, while `i64` values use `%lld`.
- Object printing iterates through the structure's fields.

The compiler writes LLVM IR using the module generated by the builder.

## 5. Error Handling

Lexical, syntax, and semantic errors stop compilation and produce a non-zero exit code.

Errors are reported to standard error.

Example:

```text
compilation error: line 4:13: expected comparison operator
```

Invalid programs do not proceed to LLVM code generation.

## 6. Testing

Run the Stage 1 regression tests:

```bash
python3 run_tests.py
```

The suite contains:

- 18 valid programs with expected AST output.
- 19 invalid programs with expected error messages.

A successful run ends with:

```text
37/37 tests passed
```

Stage 2 semantic analysis and LLVM code generation have also been checked using compilation and execution tests.

## 7. Grammar

The complete EBNF grammar is available in [`grammar.ebnf`](grammar.ebnf).

It covers Stage 1 and Stage 2 syntax, including functions, structures, member functions, expressions, field access, object creation, and input/output.
