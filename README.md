# cpp-tac-optimizer

A Python-based tool that transforms **C++ source code** into **Three-Address Code (TAC)** and applies **10 optimization passes** — built from scratch with no external dependencies.

> Built for Compiler Design coursework. Demonstrates key compiler optimization techniques on a supported C++ subset.

---

## Features

| # | Optimization Pass | Description |
|---|-------------------|-------------|
| 1 | **Constant Folding** | Evaluates constant expressions at compile time (`3 + 5` → `8`) |
| 2 | **Constant Propagation** | Replaces variables with known constant values |
| 3 | **Algebraic Simplification** | Simplifies identity ops (`x * 1` → `x`, `x + 0` → `x`) |
| 4 | **Strength Reduction** | Replaces expensive ops (`x * 4` → `x << 2`) |
| 5 | **Copy Propagation** | Eliminates redundant copies (`a = b; c = a` → `c = b`) |
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
 [ Lexer ]         Tokenize source into a token stream
     |
     v
 [ Parser ]        Build an Abstract Syntax Tree (AST)
     |
     v
 [ TAC Generator ] Convert AST to Three-Address Code
     |
     v
 [ Optimizer ]     Apply 10 optimization passes
     |
     v
 Optimized TAC     Final output with reduction summary
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
3. **Unoptimized TAC** — raw three-address code
4. **Each optimization pass** — with `[CHANGED]` or `[no change]` status
5. **Final optimized TAC** — with instruction count and reduction percentage

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
├── ast_nodes.py        # AST node class definitions
├── lexer.py            # Regex-based tokenizer
├── parser.py           # Recursive descent parser
├── tac_generator.py    # AST → Three-Address Code
├── optimizer.py        # 10 optimization passes
├── main.py             # CLI entry point
├── sample_input.cpp    # Sample C++ input (tests all passes)
└── README.md
```

---

## Sample Results

Running on `sample_input.cpp`:

```
Instructions before: 56
Instructions after:  37
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

---

## How It Works

### Three-Address Code Format

Each TAC instruction has **at most one operator** and **up to two operands**:

```
t0 = 3 + 5          # binary operation
a = t0               # assignment
iffalse t1 goto L0   # conditional branch
goto L1              # unconditional jump
param x              # function parameter
t2 = call square, 1  # function call
return t2            # return value
print a              # output
```

### Optimization Example

**Before (unoptimized):**
```
t0 = 3 + 5       # constant expression
a = t0
t1 = a * 2       # a is known to be 8
b = t1
t2 = b * 1       # multiply by 1 (identity)
c = t2
t3 = c * 4       # multiply by power of 2
e = t3
f = e             # redundant copy
t4 = f + 10       # uses copy instead of original
g = t4
j = 42            # never used
```

**After (optimized):**
```
a = 8             # constant folded
b = 16            # constant propagated + folded
e = 16 << 2       # algebraic simplified + strength reduced
g = e + 10        # copy propagated
                  # j = 42 removed (dead code)
```
