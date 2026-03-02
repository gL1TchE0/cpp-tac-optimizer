# cpp-tac-optimizer

A Python-based tool that transforms **C++ source code** into **GIMPLE intermediate representation** and applies **10 optimization passes** — built from scratch with no external dependencies.

> GIMPLE is GCC's tree-based IR used for compiler optimizations. This tool generates a simplified GIMPLE format and demonstrates key optimization techniques.

---

## Features

| # | Optimization Pass | Description |
|---|-------------------|-------------|
| 1 | **Constant Folding** | Evaluates constant expressions at compile time (`3 + 5` -> `8`) |
| 2 | **Constant Propagation** | Replaces variables with known constant values |
| 3 | **Algebraic Simplification** | Simplifies identity ops (`x * 1` -> `x`, `x + 0` -> `x`) |
| 4 | **Strength Reduction** | Replaces expensive ops (`x * 4` -> `x << 2`) |
| 5 | **Copy Propagation** | Eliminates redundant copies (`a = b; c = a` -> `c = b`) |
| 6 | **Common Subexpression Elimination** | Reuses previously computed expressions |
| 7 | **Dead Code Elimination** | Removes assignments to unused variables |
| 8 | **Unreachable Code Elimination** | Removes code after `return`, inside `if(false)`, etc. |
| 9 | **Loop Optimization** | Loop-invariant code motion |
| 10 | **Function Inlining** | Inlines small function bodies at call sites |

---

## Pipeline

```
C++ Source Code
     |
     v
 [ Lexer ]              Tokenize source into a token stream
     |
     v
 [ Parser ]             Build an Abstract Syntax Tree (AST)
     |
     v
 [ GIMPLE Generator ]   Convert AST to GIMPLE IR
     |
     v
 [ Optimizer ]          Apply 10 optimization passes
     |
     v
 Optimized GIMPLE IR    Final output with reduction summary
```

---

## Quick Start

### Prerequisites

- **Python 3.6+** (no external packages needed)

### Run

```bash
# Using the included sample (exercises all 10 passes)
python main.py sample_input.cpp

# Using your own C++ file
python main.py your_file.cpp
```

### Output

The tool prints each stage:
1. **Tokens** — lexical analysis output
2. **AST** — parsed abstract syntax tree
3. **Unoptimized GIMPLE** — raw GIMPLE IR with function declarations
4. **Each optimization pass** — with `[CHANGED]` or `[no change]` status
5. **Final optimized GIMPLE** — with statement count and reduction percentage

---

## GIMPLE Output Format

The output follows GCC's GIMPLE conventions:
- **Temporaries** use `_N` naming (e.g., `_0`, `_1`, `_2`)
- **Basic blocks** are labeled as `<bb N>:`
- **Conditionals** use `if (_N == 0) goto <bb M>;`
- **I/O** is represented as `__builtin_print()`
- **Functions** are wrapped with type signatures and variable declarations

Example output:
```c
main ()
{
  int _0, _1, _2;
  int a, b;

  <bb 2>:
    _0 = 3 + 5;
    a = _0;
    _1 = a * 2;
    b = _1;
    if (_2 == 0) goto <bb 4>;
  <bb 3>:
    ...
  <bb 4>:
    return 0;
}
```

---

## Supported C++ Subset

| Feature | Examples |
|---------|---------|
| Types | `int`, `float`, `double`, `bool`, `void` |
| Arithmetic | `+`, `-`, `*`, `/`, `%` |
| Comparison | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| Logical | `&&`, `\|\|`, `!` |
| Assignment | `=`, `+=`, `-=`, `*=`, `/=` |
| Increment/Decrement | `++x`, `x++`, `--x`, `x--` |
| Control Flow | `if / else`, `while`, `for` |
| Functions | Definitions, calls, `return` |
| I/O | `cout << expr << endl` |

---

## Project Structure

```
cpp-tac-optimizer/
├── ast_nodes.py            # AST node class definitions
├── lexer.py                # Regex-based tokenizer
├── parser.py               # Recursive descent parser
├── gimple_generator.py     # AST -> GIMPLE IR
├── optimizer.py            # 10 optimization passes
├── main.py                 # CLI entry point
├── sample_input.cpp        # Sample C++ input (tests all passes)
└── README.md
```

---

## Sample Results

Running on `sample_input.cpp`:

```
Statements before: 56
Statements after:  37
Removed: 19 (33.9% reduction)

OPTIMIZATION SUMMARY
  Pass  1: Constant Folding                         [APPLIED]
  Pass  2: Constant Propagation                     [APPLIED]
  Pass  3: Algebraic Simplification                 [APPLIED]
  Pass  4: Strength Reduction                       [APPLIED]
  Pass  5: Copy Propagation                         [APPLIED]
  Pass  6: Common Subexpression Elimination         [APPLIED]
  Pass  7: Dead Code Elimination                    [APPLIED]
  Pass  8: Unreachable Code Elimination             [APPLIED]
  Pass  9: Loop Optimization                        [APPLIED]
  Pass 10: Function Inlining                        [APPLIED]
```
