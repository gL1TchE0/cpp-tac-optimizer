"""
C++ to GIMPLE IR Optimizer -- CLI Entry Point.

Usage:
    python main.py <input_file.cpp>
    python main.py                      (uses sample_input.cpp)
"""

import sys
import os

from lexer import Lexer
from parser import Parser
from gimple_generator import (
    GimpleGenerator,
    format_gimple,
    generate_from_gcc,
)
from optimizer import optimize
from decompiler import gimple_to_cpp


# ── Formatting helpers ────────────────────────────────────────────────────────

W = 65

def banner(title):
    pad = (W - len(title) - 2) // 2
    print()
    print("-" * W)
    print(" " + " " * pad + title)
    print("-" * W)

def section(title):
    print()
    print("-" * W)
    print(f"  {title}")
    print("-" * W)

def count_stmts(instrs):
    return len([i for i in instrs if i.op not in ('func_begin', 'func_end')])


# ── Token summary ─────────────────────────────────────────────────────────────

def summarize_tokens(tokens):
    from collections import Counter
    counts = Counter(t.type for t in tokens if t.type != 'EOF')
    order = ('INT', 'VOID', 'BOOL', 'FLOAT', 'DOUBLE',
             'IDENT', 'INT_LIT', 'FLOAT_LIT', 'STRING_LIT',
             'IF', 'ELSE', 'WHILE', 'FOR', 'RETURN', 'COUT', 'ENDL')
    parts = []
    for k in order:
        if k in counts:
            parts.append(f"{k}({counts.pop(k)})")
    for k, n in sorted(counts.items()):
        parts.append(f"{k}({n})")
    return "  ".join(parts)


# ── AST printer ───────────────────────────────────────────────────────────────

def print_ast_summary(program):
    from ast_nodes import (VarDecl, Assignment, IfStmt, WhileStmt, ForStmt,
                           ReturnStmt, PrintStmt, FunctionCall, Block,
                           BinaryExpr, UnaryExpr, Number, BoolLiteral, Identifier)

    def expr(node):
        if isinstance(node, Number):      return str(node.value)
        if isinstance(node, BoolLiteral): return str(node.value).lower()
        if isinstance(node, Identifier):  return node.name
        if isinstance(node, BinaryExpr):
            return f"({expr(node.left)} {node.op} {expr(node.right)})"
        if isinstance(node, UnaryExpr):
            return f"({node.op}{expr(node.operand)})"
        if isinstance(node, FunctionCall):
            return f"{node.name}({', '.join(expr(a) for a in node.args)})"
        return repr(node)

    def walk(node, depth=0):
        pad = '    ' + '  ' * depth
        if isinstance(node, Block):
            for s in node.statements: walk(s, depth)
        elif isinstance(node, VarDecl):
            init = f" = {expr(node.init)}" if node.init else ""
            print(f"{pad}VarDecl   {node.var_type} {node.name}{init}")
        elif isinstance(node, Assignment):
            print(f"{pad}Assign    {node.name} {node.op} {expr(node.value)}")
        elif isinstance(node, IfStmt):
            suffix = "(with else)" if node.else_body else ""
            print(f"{pad}If        ({expr(node.condition)}) {suffix}")
            walk(node.then_body, depth + 1)
            if node.else_body:
                print(f"{pad}  Else"); walk(node.else_body, depth + 1)
        elif isinstance(node, WhileStmt):
            print(f"{pad}While     ({expr(node.condition)})")
            walk(node.body, depth + 1)
        elif isinstance(node, ForStmt):
            cond = expr(node.condition) if node.condition else "true"
            print(f"{pad}For       ({cond})")
            walk(node.body, depth + 1)
        elif isinstance(node, ReturnStmt):
            print(f"{pad}Return    {expr(node.value) if node.value else 'void'}")
        elif isinstance(node, PrintStmt):
            print(f"{pad}Print     {', '.join(expr(v) for v in node.values)}")
        elif isinstance(node, FunctionCall):
            print(f"{pad}Call      {node.name}({', '.join(expr(a) for a in node.args)})")

    for func in program.functions:
        params = ', '.join(f"{t} {n}" for t, n in func.params)
        print(f"\n    Function  {func.return_type} {func.name}({params})")
        walk(func.body)


# ── Optimization annotator ────────────────────────────────────────────────────

def build_annotations(gimple_stmts, function_tacs):
    """Run each pass individually and track which statement strings are changed
    or removed. Returns {stmt_str -> (pass_num, pass_name)}."""
    from optimizer import (
        constant_folding, constant_propagation, algebraic_simplification,
        strength_reduction, copy_propagation, common_subexpression_elimination,
        dead_code_elimination, unreachable_code_elimination, loop_optimization,
        function_inlining, copy_instructions,
    )

    PASSES = [
        (1,  "Constant Folding",               constant_folding),
        (2,  "Constant Propagation",            constant_propagation),
        (3,  "Algebraic Simplification",        algebraic_simplification),
        (4,  "Strength Reduction",              strength_reduction),
        (5,  "Copy Propagation",               copy_propagation),
        (6,  "Common Subexpression Elim.",     common_subexpression_elimination),
        (7,  "Dead Code Elimination",          dead_code_elimination),
        (8,  "Unreachable Code Elimination",   unreachable_code_elimination),
        (9,  "Loop Optimization",              loop_optimization),
    ]

    current     = copy_instructions(gimple_stmts)
    annotations = {}   # stmt_str -> (pass_num, pass_name)

    for pass_num, pass_name, pass_fn in PASSES:
        before_strs = [str(s) for s in current]
        new_instrs, changed = pass_fn(current)
        if changed:
            after_set = set(str(s) for s in new_instrs)
            for stmt_str in before_strs:
                if stmt_str not in after_set and stmt_str not in annotations:
                    annotations[stmt_str] = (pass_num, pass_name)
        current = new_instrs

    # Pass 10: Function Inlining — mark param/call pairs
    before_strs = [str(s) for s in current]
    new_instrs, changed, _ = function_inlining(current, function_tacs or {})
    if changed:
        after_set = set(str(s) for s in new_instrs)
        for stmt_str in before_strs:
            if stmt_str not in after_set and stmt_str not in annotations:
                annotations[stmt_str] = (10, "Function Inlining")

    return annotations


def print_gimple_annotated(filtered_stmts, annotations):
    """Print GIMPLE statements with inline optimization annotations."""
    COL = 52   # column at which annotations start

    in_func   = False
    func_name = None

    for stmt in filtered_stmts:
        if stmt.op == 'func_begin':
            func_name = stmt.arg1
            in_func   = True
            print(f"\n{stmt.arg1} ()")
            print("{")
            continue
        if stmt.op == 'func_end':
            print("}")
            in_func = False
            continue

        line_str  = str(stmt)
        note      = annotations.get(line_str)
        note_text = f"[Pass {note[0]}: {note[1]}]" if note else ""

        # Pad to column then append annotation
        padded = f"{line_str:<{COL}}"
        print(padded + ("  " + note_text if note_text else ""))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = os.path.join(os.path.dirname(__file__), 'sample_input.cpp')

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    with open(input_file, 'r') as f:
        source = f.read()

    src_lines = source.strip().splitlines()

    # ── Header ────────────────────────────────────────────────────
    banner("C++ TO GIMPLE IR OPTIMIZER")
    print(f"\n  Input : {os.path.abspath(input_file)}")
    print(f"  Lines : {len(src_lines)}")

    # ── Stage 1: Lexical Analysis ─────────────────────────────────
    section("STAGE 1: LEXICAL ANALYSIS")

    lexer       = Lexer(source)
    tokens      = lexer.get_tokens()
    real_tokens = [t for t in tokens if t.type != 'EOF']
    sample      = real_tokens[:10]

    print(f"\n  Total tokens : {len(real_tokens)}")
    print(f"  Token types  : {summarize_tokens(tokens)}")
    print(f"\n  First {len(sample)} tokens:")
    for tok in sample:
        print(f"    line {tok.line:>2}  {tok.type:<14}  {tok.value!r}")
    if len(real_tokens) > len(sample):
        print(f"    ... and {len(real_tokens) - len(sample)} more")

    # ── Stage 2: Parsing ──────────────────────────────────────────
    section("STAGE 2: ABSTRACT SYNTAX TREE")

    parser = Parser(tokens)
    ast    = parser.parse()

    print(f"\n  Functions found : {', '.join(f.name for f in ast.functions)}")
    print_ast_summary(ast)

    # ── Stage 3: Unoptimized GIMPLE (annotated) ───────────────────
    section("STAGE 3: GIMPLE IR (Unoptimized) — with optimization markers")

    # Prefer real GCC GIMPLE via -fdump-tree-gimple, but fall back to the
    # internal AST-based generator if GCC is unavailable or fails.
    try:
        gimple_stmts, function_tacs = generate_from_gcc(input_file)
    except Exception as e:
        print("\n  [info] GCC-backed GIMPLE generation failed, "
              "falling back to internal generator.")
        print(f"         Reason: {e}")
        generator = GimpleGenerator()
        gimple_stmts = generator.generate(ast)
        function_tacs = generator.function_tacs
    else:
        # For compatibility with existing optimizer APIs, we still expose
        # function_tacs separately (no need to instantiate GimpleGenerator).
        generator = None

    total_before = count_stmts(gimple_stmts)

    # Determine which functions are called by others (not entry points)
    INLINE_THRESHOLD = 10
    all_func_names = {s.arg1 for s in gimple_stmts if s.op == 'func_begin'}
    called_by_others = {s.arg1 for s in gimple_stmts if s.op == 'call'}
    # Entry points: defined but never called (e.g. main)
    entry_points = all_func_names - called_by_others

    # Inlinable: non-entry functions with small bodies
    inlinable = set()
    i = 0
    while i < len(gimple_stmts):
        s = gimple_stmts[i]
        if s.op == 'func_begin' and s.arg1 not in entry_points:
            fname, body, i = s.arg1, [], i + 1
            while i < len(gimple_stmts) and gimple_stmts[i].op != 'func_end':
                body.append(gimple_stmts[i]); i += 1
            if len(body) <= INLINE_THRESHOLD:
                inlinable.add(fname)
        i += 1

    # Filter inlinable bodies out of the unoptimized display
    filtered, skip_func = [], False
    for s in gimple_stmts:
        if s.op == 'func_begin' and s.arg1 in inlinable:
            skip_func = True;  continue
        if s.op == 'func_end'   and skip_func:
            skip_func = False; continue
        if skip_func:           continue
        filtered.append(s)

    # Build per-statement optimization annotations
    annotations = build_annotations(gimple_stmts, function_tacs)

    print()
    print_gimple_annotated(filtered, annotations)
    print(f"\n  Total statements (all functions) : {total_before}")

    # ── Stage 4: Optimization Passes ──────────────────────────────
    section("STAGE 4: OPTIMIZATION PASSES")

    optimized, pass_log = optimize(
        gimple_stmts,
        function_tacs=function_tacs,
        verbose=False
    )

    print()
    print(f"  {'Pass':<6}  {'Optimization':<42}  Status")
    print(f"  {'-'*6}  {'-'*42}  {'-'*10}")
    for pass_num, name, changed, _ in pass_log:
        status = "APPLIED   " if changed else "no change "
        print(f"  {pass_num:<6}  {name:<42}  {status}")

    # ── Stage 5: Final Optimized GIMPLE ───────────────────────────
    banner("FINAL OPTIMIZED GIMPLE IR")
    print()
    print(format_gimple(optimized))

    total_after = count_stmts(optimized)
    removed     = total_before - total_after
    pct         = (removed / total_before * 100) if total_before > 0 else 0.0

    section("OPTIMIZATION SUMMARY")
    print(f"\n  Statements before : {total_before}")
    print(f"  Statements after  : {total_after}")
    print(f"  Statements removed: {removed}  ({pct:.1f}% reduction)")

    # -- Stage 6: Decompile back to C++ -----------------------------------
    banner("STAGE 6: RECONSTRUCTED C++")
    print()
    try:
        cpp_out = gimple_to_cpp(optimized)
        print(cpp_out)
    except Exception as e:
        print(f"  (Decompilation error: {e})")
    print()


if __name__ == '__main__':
    main()
