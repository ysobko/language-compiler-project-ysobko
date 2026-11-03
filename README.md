# Traffica Compiler

Traffica is a small traffic-themed programming language with custom keywords and emoji-based types. Its compiler is written in Python and generates LLVM IR using `llvmlite`.

- **Stage 1:** Variables, constants, assignments, comparisons, and conditional statements.
- **Stage 2:** Functions, structures, member functions, arithmetic, input/output, semantic analysis, and LLVM code generation.
- **Stage 3:** Piping, interactive program, and AST optimization.

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

### Stage 3: Piping

Piping is a new language feature introduced in Stage 3.
The `|>` operator passes the result of the expression on its left
as an argument to the function on its right.

#### Syntax and Rules

```text
expression |> functionName
expression |> firstFunction |> secondFunction
```

- Piping is evaluated from left to right.
- Each piping stage calls a function with one argument.
- The result of one stage becomes the input of the next stage.
- The operator `|>` has lower precedence than `+`, `-`, and `*`.
- Each stage must refer to an existing function that accepts one argument.
- The compiler checks whether the output type of one stage matches the input type of the next stage.
- If the types are incompatible, compilation stops and reports the problematic stage.

For example:

```text
10 |> double |> addFive
```

is equivalent to:

```text
addFive(double(10))
```

The parser represents piping as nested function calls in the AST.
This allows the compiler to reuse the existing function call code generation.

#### Example 1: Chaining Functions

```text
route double(🟢 x) -> 🟢 {
    arrive x * 2
}

route addFive(🟢 x) -> 🟢 {
    arrive x + 5
}

go 🟢 result <- 10 |> double |> addFive
print(result)
```

Output:

```text
25
```

The value 10 is first passed to `double`, which returns 20.
Then 20 is passed to `addFive`, which returns 25.

#### Example 2: Piping with Arithmetic

```text
route square(🟢 x) -> 🟢 {
    arrive x * x
}

route addThree(🟢 x) -> 🟢 {
    arrive x + 3
}

print((2 + 4) |> square |> addThree)
```

Output:

```text
39
```

The arithmetic expression `(2 + 4)` is evaluated first.
The result 6 is passed to `square`, producing 36.
Finally, `addThree` returns 39.

#### Type Checking

Each piping stage must accept the type produced by the previous stage.

For example, this program is invalid:

```text
route double(🟢 x) -> 🟢 {
    arrive x * 2
}

route checkStatus(🚦 status) -> 🚦 {
    arrive status
}

print(10 |> double |> checkStatus)
```

The `double` function returns an `🟢` integer, but
`checkStatus` expects a `🚦` boolean.

The compiler reports:

```text
compilation error: line 9:23: Piping stage 'checkStatus' expects 🚦, got 🟢
```

#### Generated LLVM IR

The following excerpt is taken from the LLVM IR generated for Example 1:

```llvm
define i32 @"main"()
{
entry:
  %"call.double" = call i32 @"traffica_double"(i32 10)
  %"call.addFive" = call i32 @"traffica_addFive"(i32 %"call.double")
  store i32 %"call.addFive", i32* @"traffica_global_result"
  %"result.global.value" = load i32, i32* @"traffica_global_result"
  %".3" = call i32 (i8*, ...) @"printf"(i8* getelementptr ([4 x i8], [4 x i8]* @"traffica_fmt_print_i32", i32 0, i32 0), i32 %"result.global.value")
  ret i32 0
}
```

The first function call passes the value 10 to `traffica_double`.
The second function call passes the result of `double` to `traffica_addFive`, showing how piping is executed from left to right.
Finally, the result is stored in the variable and printed using `printf`.

#### Testing

Piping is covered by three valid and three invalid test programs.

Valid tests:
- `piping_chain`
- `piping_arithmetic`
- `piping_single`

Invalid tests:
- `piping_type_mismatch`
- `piping_unknown_function`
- `piping_wrong_arguments`

All tests are executed using `python3 run_tests.py`.

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
| `run_tests.py` | Test runner for all stages and interactive sessions |
| `tests/` | Valid and invalid programs for all stages |
| `programs/` | Interactive program and recorded input/output sessions |

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

Run all regression tests:

    python3 run_tests.py

The test suite includes Stage 1, Stage 2, and Stage 3 programs.

Current test results:

- 33 valid programs.
- 32 invalid programs.
- 15 end-to-end execution tests.
- 1 end-to-end test with input.
- 3 interactive program sessions.

A successful run ends with:

    68/68 tests passed

The Piping feature has three valid and three invalid tests.
These tests check function chaining, arithmetic expressions,
single-stage piping, type mismatches, unknown functions,
and incorrect argument counts.

## 7. Grammar

The complete EBNF grammar is available in [`grammar.ebnf`](grammar.ebnf).

It covers Stage 1, Stage 2, and Stage 3 syntax, including functions, structures, member functions, expressions, field access, object creation, input/output, and piping.

## Stage 3 — Interactive Program

The program is located in `programs/traffic_checker.txt`.

1. The program is an interactive traffic speed checker.
2. It asks the user to enter a car's speed.
3. The speed is read using the `scan()` function.
4. The program processes the speed using the piping operator.
5. The expression `speed |> addFive |> double` calls two functions from left to right.
6. The first function adds 5 to the entered speed.
7. The second function doubles the result.
8. The `SpeedChecker` structure stores a speed limit of 60.
9. Its member function `isDifferentFromLimit()` checks whether the adjusted speed differs from 60.
10. The program prints the adjusted speed and the comparison result.

### Compile to a Native Executable

```bash
python3 compiler.py programs/traffic_checker.txt /tmp/traffic_checker.ll
llc -filetype=obj /tmp/traffic_checker.ll -o /tmp/traffic_checker.o
clang /tmp/traffic_checker.o -o /tmp/traffic_checker
```

### Recorded Sessions

**Session 1 — Adjusted speed equals the limit**

Input: `25`

```bash
/tmp/traffic_checker < programs/traffic_checker_1.in
```

Expected output:

```text
Enter car speed:
Adjusted speed:
60
Speed differs from limit:
false
```

**Session 2 — Adjusted speed is greater than the limit**

Input: `30`

```bash
/tmp/traffic_checker < programs/traffic_checker_2.in
```

Expected output:

```text
Enter car speed:
Adjusted speed:
70
Speed differs from limit:
true
```

**Session 3 — Adjusted speed is less than the limit**

Input: `20`

```bash
/tmp/traffic_checker < programs/traffic_checker_3.in
```

Expected output:

```text
Enter car speed:
Adjusted speed:
50
Speed differs from limit:
true
```

### Automated Testing

Run all compiler tests and the three recorded interactive sessions:

```bash
python3 run_tests.py
```

The test script compiles the interactive program into a native executable
using `llc` and `clang`, then compares its output with the corresponding
`.expected` files.

---

## Stage 3 — Task 2: AST Optimizations

The Traffica compiler implements three AST optimizations:

1. Unused variable removal.
2. Unused function removal.
3. Function inlining.

All optimizations are optional and are enabled using the `--optimize` flag.

The optimizer works on the AST after the initial semantic analysis and before LLVM IR generation. After optimization, semantic analysis runs again to validate the modified AST.

### How to Run the Optimizer

Compile a program normally:

```bash
python3 compiler.py tests/optimizer/inlining_simple.src -o before.ll
```

Compile the same program with optimization:

```bash
python3 compiler.py tests/optimizer/inlining_simple.src --optimize -o after.ll
```

View the original AST:

```bash
python3 compiler.py tests/optimizer/inlining_simple.src --ast
```

View the optimized AST:

```bash
python3 compiler.py tests/optimizer/inlining_simple.src --optimize --ast
```

### Optimization 1: Unused Variable Removal

The optimizer removes variable declarations whose values are never used.

It repeats the removal process until no additional unused variables can be removed. This is necessary because removing one declaration may make another declaration unused.

The optimizer considers variable scopes and shadowing. Variables with the same name in different scopes are treated as separate declarations.

**Example:**

```text
go 🟢 unused <- 100
go 🟢 result <- 20
print(result)
```

**Optimized AST:**

```text
Program
  MutableDecl 🟢 result
    Integer 20
  Print
    Identifier result
```

The declaration of `unused` disappears because its value is never read.

#### Preserving Side Effects

Removing an unused variable must not remove side effects from its initializer.

For example:

```text
go 🟢 unused <- scan()
print(10)
```

**Optimized AST:**

```text
Program
  ExpressionStmt
    Scan
  Print
    Integer 10
```

The unused variable is removed, but `scan()` remains because it reads input.

The optimizer also preserves expressions containing function calls that may have side effects.

### Optimization 2: Unused Function Removal

The optimizer removes functions that are not reachable from the main program.

This includes functions that are only called by other unused functions.

**Example:**

```text
route helper(🟢 x) -> 🟢 {
    arrive x * 2
}

route unused(🟢 x) -> 🟢 {
    arrive helper(x)
}

print(30)
```

**Optimized AST:**

```text
Program
  Print
    Integer 30
```

Both functions are removed because neither is reachable from the main program.

The optimizer repeats this process until no additional unused functions remain.

### Optimization 3: Function Inlining

Function inlining replaces a function call with the body of the called function.

The optimizer considers functions that are called exactly once.

During inlining:

1. Each parameter becomes a variable declaration initialized with the corresponding argument.
2. Local declarations from the function body are copied to the call site.
3. The final `arrive` expression replaces the original function call.
4. Parameters and local variables are renamed to avoid name collisions.
5. The original function is removed when it becomes unused.

#### Simple Inlining Example

**Original program:**

```text
route double(🟢 x) -> 🟢 {
    arrive x * 2
}

print(double(10))
```

**Optimized AST:**

```text
Program
  InlineBlock
    MutableDecl 🟢 _inline_1_x
      Integer 10
    Print
      BinaryOp *
        Identifier _inline_1_x
        Integer 2
```

The call to `double(10)` is replaced with the calculation inside `main`.

The parameter `x` becomes a local variable named `_inline_1_x`.

The `InlineBlock` keeps the inserted declarations in their own scope.

#### Nested Inlining and Name Collisions

The optimizer also supports nested calls.

For example:

```text
route addFive(🟢 x) -> 🟢 {
    arrive x + 5
}

route double(🟢 x) -> 🟢 {
    arrive x * 2
}

go 🟢 x <- 100
go 🟢 result <- double(addFive(10))

print(x)
print(result)
```

**Optimized AST:**

```text
Program
  MutableDecl 🟢 x
    Integer 100
  MutableDecl 🟢 _inline_1_x
    Integer 10
  MutableDecl 🟢 _inline_2_x
    BinaryOp +
      Identifier _inline_1_x
      Integer 5
  MutableDecl 🟢 result
    BinaryOp *
      Identifier _inline_2_x
      Integer 2
  Print
    Identifier x
  Print
    Identifier result
```

**Program output:**

```text
100
30
```

Both functions are inlined, and their parameters receive unique names.

The original variable `x` is not overwritten.

### Supported Inlining Shapes

The current implementation supports:

- Non-recursive functions called exactly once.
- Functions with parameters.
- Functions containing local variable declarations followed by a final `arrive`.
- Function bodies whose local initializers and final return expression use their parameters or previously declared local variables.
- Calls inside supported expressions and variable initializers.
- Calls in `print()` statements.
- Nested function calls.
- Global `go`, `hold`, and `sign` initializers.
- Renaming parameters and local variables to avoid collisions.

### Unsupported Inlining Shapes

Some cases are intentionally left unchanged.

**1. Recursive functions**

Recursive functions are never inlined, including functions involved in indirect recursion.

**2. Functions called more than once**

The optimizer only considers functions called exactly once.

**3. Early returns inside conditional statements**

For example, functions containing `arrive` inside `check` branches are not inlined.

**4. Complex function bodies**

The current implementation does not inline function bodies containing unsupported control-flow statements or statements outside the supported declaration-and-final-return shape.

**5. Expressions where inlining may change evaluation order**

Inlining is skipped when moving calculations could change the order of expressions with side effects.

For example:

```text
route double(🟢 x) -> 🟢 {
    arrive x * 2
}

print(scan() - double(scan()))
```

If the user enters `10` and then `3`, the correct result is:

```text
4
```

Moving the second `scan()` before the first one would change the result.

Therefore, the optimizer keeps the function call in this case.

Unsupported calls remain unchanged to preserve the original program behavior.

### LLVM IR Before and After Inlining

The following example uses:

`tests/optimizer/inlining_simple.src`

The complete generated LLVM IR files are available at:

- `docs/optimization/before.ll`
- `docs/optimization/after.ll`

#### Before Optimization

The compiler generates a separate function:

```llvm
define i32 @"traffica_double"(i32 %"x")
{
entry:
  %"x.addr" = alloca i32
  store i32 %"x", i32* %"x.addr"
  %"x.value" = load i32, i32* %"x.addr"
  %"arithmetic.checked" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"x.value", i32 2)
  %"arithmetic.result" = extractvalue {i32, i1} %"arithmetic.checked", 0
  %"arithmetic.overflow" = extractvalue {i32, i1} %"arithmetic.checked", 1
  br i1 %"arithmetic.overflow", label %"arithmetic.overflow.error", label %"arithmetic.continue"
arithmetic.overflow.error:
  call void @"abort"()
  unreachable
arithmetic.continue:
  ret i32 %"arithmetic.result"
}
```

The `main` function calls it:

```llvm
%"call.double" = call i32 @"traffica_double"(i32 10)
```

#### After Optimization

The separate `traffica_double` function is removed.

Its parameter and calculation are moved into `main`:

```llvm
%"_inline_1_x" = alloca i32
store i32 10, i32* %"_inline_1_x"
%"_inline_1_x.value" = load i32, i32* %"_inline_1_x"
%"arithmetic.checked" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"_inline_1_x.value", i32 2)
%"arithmetic.result" = extractvalue {i32, i1} %"arithmetic.checked", 0
```

The result is passed directly to `printf` without calling `traffica_double`.

The overflow check is still present, so inlining does not remove the compiler's arithmetic safety checks.

### Optimization Tests

Six optimizer tests are located in `tests/optimizer/`.

| Test | Optimization | Purpose |
|------|--------------|---------|
| `unused_variable_simple` | Unused variables | Remove an unused variable |
| `unused_variable_side_effect` | Unused variables | Preserve `scan()` after removing a declaration |
| `unused_function_simple` | Unused functions | Remove an unused function |
| `unused_function_chain` | Unused functions | Remove a chain of unreachable functions |
| `inlining_simple` | Inlining | Replace a single function call |
| `inlining_nested` | Inlining | Inline nested calls and avoid name collisions |

Each test includes:

- `.src` — source program.
- `.ast.expected` — expected optimized AST.
- `.expected` — expected program output.
- `.input` — optional input for programs using `scan()`.

The automated test runner:

1. Compiles each program to an optimized AST.
2. Compares the AST with its expected result.
3. Compiles the program without optimization.
4. Compiles the program with optimization.
5. Executes both versions.
6. Checks that both outputs match the expected output.

Run all optimizer tests:

```bash
python3 tests/optimizer/run_optimizer_tests.py
```

**Test result: 6/6 optimizer tests passed.**

### Regression Testing

The existing compiler test suite can be run with:

```bash
python3 run_tests.py
```

The latest test results were:

- **69/69** standard tests passed.
- **69/69** regression tests passed with `--optimize`.
- **6/6** optimizer-specific tests passed.

The optimized regression run checks successful compilation of valid
AST-only programs, expected diagnostics for invalid programs, and
expected output for end-to-end and interactive programs.

These results confirm that the supported optimizations preserve
the expected program behavior in the tested cases.

