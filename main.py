"""
C++ to Three-Address Code Optimizer — CLI Entry Point.

Usage:
    python main.py <input_file.cpp>
    python main.py                      (uses sample_input.cpp)

Stages:
    1. Lexing   → Tokens
    2. Parsing  → AST
    3. TAC Gen  → Unoptimized Three-Address Code
    4. Optimize → 10 optimization passes
    5. Output   → Final optimized TAC
"""

import sys
import os

from lexer import Lexer
from parser import Parser
from tac_generator import TACGenerator, format_tac
from optimizer import optimize


def print_header(title):
    width = 65
    print(f"\n{'#' * width}")
    print(f"#  {title:^{width - 4}}#")
    print(f"{'#' * width}")


def print_section(title):
    print(f"\n{'-' * 65}")
    print(f"  {title}")
    print(f"{'-' * 65}")


def main():
    # ─── Read input file ─────────────────────────────────────────────
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = os.path.join(os.path.dirname(__file__), 'sample_input.cpp')

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    with open(input_file, 'r') as f:
        source = f.read()

    print_header("C++ TO THREE-ADDRESS CODE OPTIMIZER")
    print(f"\n  Input file: {input_file}")

    # ─── Stage 1: Lexing ─────────────────────────────────────────────
    print_section("STAGE 1: LEXICAL ANALYSIS (Tokens)")
    lexer = Lexer(source)
    tokens = lexer.get_tokens()

    for tok in tokens:
        print(f"    {tok}")

    # ─── Stage 2: Parsing ────────────────────────────────────────────
    print_section("STAGE 2: PARSING (AST)")
    parser = Parser(tokens)
    ast = parser.parse()

    def print_ast(node, indent=4):
        prefix = ' ' * indent
        if hasattr(node, '__dict__'):
            print(f"{prefix}{node.__class__.__name__}:")
            for key, val in node.__dict__.items():
                if isinstance(val, list):
                    print(f"{prefix}  {key}:")
                    for item in val:
                        print_ast(item, indent + 4)
                elif hasattr(val, '__dict__'):
                    print(f"{prefix}  {key}:")
                    print_ast(val, indent + 4)
                else:
                    print(f"{prefix}  {key}: {val}")
        else:
            print(f"{prefix}{node}")

    print_ast(ast)

    # ─── Stage 3: TAC Generation ─────────────────────────────────────
    print_section("STAGE 3: THREE-ADDRESS CODE (Unoptimized)")
    generator = TACGenerator()
    tac_instructions = generator.generate(ast)
    print(format_tac(tac_instructions))

    total_before = len([i for i in tac_instructions
                        if i.op not in ('func_begin', 'func_end')])
    print(f"\n  Total instructions: {total_before}")

    # ─── Stage 4: Optimization ───────────────────────────────────────
    print_section("STAGE 4: OPTIMIZATION PASSES")
    optimized, pass_log = optimize(
        tac_instructions,
        function_tacs=generator.function_tacs,
        verbose=True
    )

    # ─── Stage 5: Final Output ───────────────────────────────────────
    print_header("FINAL OPTIMIZED THREE-ADDRESS CODE")
    print(format_tac(optimized))

    total_after = len([i for i in optimized
                       if i.op not in ('func_begin', 'func_end')])
    print(f"\n  Instructions before: {total_before}")
    print(f"  Instructions after:  {total_after}")
    removed = total_before - total_after
    if total_before > 0:
        pct = (removed / total_before) * 100
        print(f"  Removed: {removed} ({pct:.1f}% reduction)")

    # ─── Summary ─────────────────────────────────────────────────────
    print_section("OPTIMIZATION SUMMARY")
    for pass_num, name, changed, _ in pass_log:
        status = "APPLIED" if changed else "no change"
        print(f"  Pass {pass_num:2d}: {name:<40s} [{status}]")

    print()


if __name__ == '__main__':
    main()
