"""
Optimizer for Three-Address Code.
Implements 10 optimization passes that transform TAC instructions.

Passes (applied in order):
  1. Constant Folding       - Evaluate constant expressions at compile time
  2. Constant Propagation   - Replace variables with known constants
  3. Algebraic Simplification - Simplify identity/zero operations
  4. Strength Reduction     - Replace expensive ops with cheaper ones
  5. Copy Propagation       - Eliminate redundant copies
  6. Common Subexpression Elimination (CSE)
  7. Dead Code Elimination  - Remove unused assignments
  8. Unreachable Code Elimination
  9. Loop Optimization      - Loop-invariant code motion
 10. Function Inlining      - Inline small function bodies
"""

import math
from gimple_generator import GimpleStmt, format_gimple


# ─── Helpers ─────────────────────────────────────────────────────────────────

def is_number(val):
    """Check if a string represents a numeric literal."""
    if val is None:
        return False
    try:
        float(str(val))
        return True
    except (ValueError, TypeError):
        return False


def get_number(val):
    """Parse a string to int or float."""
    s = str(val)
    if '.' in s:
        return float(s)
    return int(s)


def is_power_of_two(n):
    """Check if an integer is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def log2_int(n):
    """Return log2 for a power of 2."""
    return int(math.log2(n))


ARITHMETIC_OPS = {'+', '-', '*', '/', '%'}
COMPARISON_OPS = {'<', '>', '<=', '>=', '==', '!='}
BINARY_OPS = ARITHMETIC_OPS | COMPARISON_OPS | {'&&', '||', '<<', '>>'}


def copy_instructions(instructions):
    """Deep copy a list of TAC instructions."""
    return [i.copy() for i in instructions]


# ═══════════════════════════════════════════════════════════════════════════
# PASS 1: Constant Folding
# ═══════════════════════════════════════════════════════════════════════════

def constant_folding(instructions):
    """Evaluate binary operations on two constants at compile time.
    Example: t0 = 3 + 5  →  t0 = 8
    """
    result = []
    changed = False

    for instr in instructions:
        if (instr.op in BINARY_OPS and
                is_number(instr.arg1) and is_number(instr.arg2)):
            a = get_number(instr.arg1)
            b = get_number(instr.arg2)
            val = None

            try:
                if instr.op == '+':    val = a + b
                elif instr.op == '-':  val = a - b
                elif instr.op == '*':  val = a * b
                elif instr.op == '/':  val = a // b if isinstance(a, int) and isinstance(b, int) and b != 0 else (a / b if b != 0 else None)
                elif instr.op == '%':  val = a % b if b != 0 else None
                elif instr.op == '<':  val = int(a < b)
                elif instr.op == '>':  val = int(a > b)
                elif instr.op == '<=': val = int(a <= b)
                elif instr.op == '>=': val = int(a >= b)
                elif instr.op == '==': val = int(a == b)
                elif instr.op == '!=': val = int(a != b)
                elif instr.op == '&&': val = int(bool(a) and bool(b))
                elif instr.op == '||': val = int(bool(a) or bool(b))
                elif instr.op == '<<': val = int(a) << int(b)
                elif instr.op == '>>': val = int(a) >> int(b)
            except Exception:
                val = None

            if val is not None:
                # Convert float results that are whole numbers to int
                if isinstance(val, float) and val == int(val):
                    val = int(val)
                result.append(GimpleStmt('=', str(val), result=instr.result))
                changed = True
                continue

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 2: Constant Propagation
# ═══════════════════════════════════════════════════════════════════════════

def constant_propagation(instructions):
    """Replace variable uses with their known constant values.
    Example: a = 8; b = a * 2  →  a = 8; b = 8 * 2
    """
    result = []
    constants = {}  # variable -> constant value
    changed = False

    for instr in instructions:
        new_instr = instr.copy()

        # At labels, clear constants (jump targets can come from anywhere)
        if instr.op == 'label':
            constants.clear()
            result.append(new_instr)
            continue

        # At function boundaries, clear constants
        if instr.op in ('func_begin', 'func_end'):
            constants.clear()
            result.append(new_instr)
            continue

        # Replace arg1 if it's a known constant
        if new_instr.arg1 in constants:
            new_instr.arg1 = constants[new_instr.arg1]
            changed = True

        # Replace arg2 if it's a known constant
        if new_instr.arg2 in constants and instr.op not in ('iffalse', 'goto', 'call'):
            new_instr.arg2 = constants[new_instr.arg2]
            changed = True

        # Track new constant assignments: x = <constant>
        if new_instr.op == '=' and is_number(new_instr.arg1) and new_instr.result:
            constants[new_instr.result] = new_instr.arg1
        elif new_instr.result:
            # Variable is redefined with non-constant, invalidate
            constants.pop(new_instr.result, None)

        result.append(new_instr)

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 3: Algebraic Simplification
# ═══════════════════════════════════════════════════════════════════════════

def algebraic_simplification(instructions):
    """Simplify identity and zero operations.
    x + 0 → x,  x - 0 → x,  x * 1 → x,  x / 1 → x,
    x * 0 → 0,  0 + x → x,  1 * x → x,  0 * x → 0
    """
    result = []
    changed = False

    for instr in instructions:
        if instr.op in BINARY_OPS and instr.result:
            a1, a2 = instr.arg1, instr.arg2
            simplified = None

            # x + 0  or  0 + x
            if instr.op == '+':
                if is_number(a2) and get_number(a2) == 0:
                    simplified = a1
                elif is_number(a1) and get_number(a1) == 0:
                    simplified = a2

            # x - 0
            elif instr.op == '-':
                if is_number(a2) and get_number(a2) == 0:
                    simplified = a1
                # x - x → 0
                elif a1 == a2:
                    simplified = '0'

            # x * 1, 1 * x, x * 0, 0 * x
            elif instr.op == '*':
                if is_number(a2) and get_number(a2) == 1:
                    simplified = a1
                elif is_number(a1) and get_number(a1) == 1:
                    simplified = a2
                elif is_number(a2) and get_number(a2) == 0:
                    simplified = '0'
                elif is_number(a1) and get_number(a1) == 0:
                    simplified = '0'

            # x / 1
            elif instr.op == '/':
                if is_number(a2) and get_number(a2) == 1:
                    simplified = a1
                # x / x → 1
                elif a1 == a2:
                    simplified = '1'

            if simplified is not None:
                result.append(GimpleStmt('=', simplified, result=instr.result))
                changed = True
                continue

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 4: Strength Reduction
# ═══════════════════════════════════════════════════════════════════════════

def strength_reduction(instructions):
    """Replace expensive operations with cheaper equivalents.
    x * 2   → x << 1       x * 4  → x << 2
    x * 8   → x << 3       x / 2  → x >> 1
    x * 2^n → x << n       x / 2^n → x >> n
    """
    result = []
    changed = False

    for instr in instructions:
        if instr.op == '*' and instr.result:
            # Check if one operand is a power of 2
            if is_number(instr.arg2):
                n = get_number(instr.arg2)
                if isinstance(n, int) and n > 1 and is_power_of_two(n):
                    shift = log2_int(n)
                    result.append(GimpleStmt(
                        '<<', instr.arg1, str(shift), instr.result
                    ))
                    changed = True
                    continue
            elif is_number(instr.arg1):
                n = get_number(instr.arg1)
                if isinstance(n, int) and n > 1 and is_power_of_two(n):
                    shift = log2_int(n)
                    result.append(GimpleStmt(
                        '<<', instr.arg2, str(shift), instr.result
                    ))
                    changed = True
                    continue

        elif instr.op == '/' and instr.result:
            if is_number(instr.arg2):
                n = get_number(instr.arg2)
                if isinstance(n, int) and n > 1 and is_power_of_two(n):
                    shift = log2_int(n)
                    result.append(GimpleStmt(
                        '>>', instr.arg1, str(shift), instr.result
                    ))
                    changed = True
                    continue

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 5: Copy Propagation
# ═══════════════════════════════════════════════════════════════════════════

def copy_propagation(instructions):
    """Replace uses of a copied variable with the original.
    a = b; c = a + 1  →  a = b; c = b + 1
    """
    result = []
    copies = {}   # variable -> source variable
    changed = False

    for instr in instructions:
        new_instr = instr.copy()

        if instr.op in ('label', 'func_begin', 'func_end'):
            copies.clear()
            result.append(new_instr)
            continue

        # Replace arg1 if it's a known copy
        if new_instr.arg1 in copies:
            new_instr.arg1 = copies[new_instr.arg1]
            changed = True

        # Replace arg2 if it's a known copy (skip labels in iffalse/goto)
        if (new_instr.arg2 in copies and
                instr.op not in ('iffalse', 'goto', 'call')):
            new_instr.arg2 = copies[new_instr.arg2]
            changed = True

        # Track copies: x = y (where y is not a constant)
        if (new_instr.op == '=' and new_instr.result and
                new_instr.arg1 and not is_number(new_instr.arg1)):
            copies[new_instr.result] = new_instr.arg1
        elif new_instr.result:
            # Variable redefined, invalidate
            copies.pop(new_instr.result, None)
            # Also invalidate anything that copies this variable
            to_remove = [k for k, v in copies.items() if v == new_instr.result]
            for k in to_remove:
                del copies[k]

        result.append(new_instr)

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 6: Common Subexpression Elimination (CSE)
# ═══════════════════════════════════════════════════════════════════════════

def common_subexpression_elimination(instructions):
    """Reuse results of previously computed expressions.
    t1 = a + b; t2 = a + b  →  t1 = a + b; t2 = t1
    """
    result = []
    expr_map = {}   # (op, arg1, arg2) -> result_variable
    changed = False

    for instr in instructions:
        if instr.op in ('label', 'func_begin', 'func_end', 'goto'):
            expr_map.clear()
            result.append(instr.copy())
            continue

        if instr.op in BINARY_OPS and instr.result:
            key = (instr.op, instr.arg1, instr.arg2)
            if key in expr_map:
                # Reuse the previous result
                result.append(GimpleStmt(
                    '=', expr_map[key], result=instr.result
                ))
                changed = True
                continue
            else:
                expr_map[key] = instr.result
                # Also store commutative version
                if instr.op in ('+', '*', '==', '!=', '&&', '||'):
                    comm_key = (instr.op, instr.arg2, instr.arg1)
                    expr_map[comm_key] = instr.result

        # If a variable in an expression gets redefined, invalidate
        if instr.result:
            to_remove = [k for k in expr_map
                         if instr.result in (k[1], k[2])]
            for k in to_remove:
                del expr_map[k]

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 7: Dead Code Elimination
# ═══════════════════════════════════════════════════════════════════════════

def dead_code_elimination(instructions):
    """Remove assignments to variables that are never subsequently used.
    Preserves: returns, prints, calls, control flow, func boundaries.
    """
    # First pass: find all variables that are "used" (appear as operands)
    used_vars = set()
    for instr in instructions:
        if instr.op in ('func_begin', 'func_end', 'label'):
            continue
        if instr.arg1 and not is_number(instr.arg1):
            used_vars.add(instr.arg1)
        if instr.arg2 and not is_number(instr.arg2):
            if instr.op not in ('call',):  # arg2 of call is count, not var
                used_vars.add(instr.arg2)

    # Second pass: remove assignments to unused variables
    result = []
    changed = False

    for instr in instructions:
        # Never remove control flow, I/O, returns, function boundaries
        if instr.op in ('label', 'goto', 'iffalse', 'return', 'print',
                         'param', 'call', 'func_begin', 'func_end'):
            result.append(instr.copy())
            continue

        # Treat assignments whose RHS looks like a function call as
        # side-effectful and thus not removable, even if the result
        # variable is never used later. This keeps GCC's I/O calls such
        # as std::basic_ostream<char>::operator<< (&cout, x).
        if (
            instr.op == '='
            and isinstance(instr.arg1, str)
            and '(' in instr.arg1
            and ')' in instr.arg1
        ):
            result.append(instr.copy())
            continue

        # Remove assignment if result is never used
        if instr.result and instr.result not in used_vars:
            changed = True
            continue  # skip this instruction

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 8: Unreachable Code Elimination
# ═══════════════════════════════════════════════════════════════════════════

def unreachable_code_elimination(instructions):
    """Remove code that can never be executed.
    - Code after unconditional goto/return (until next label)
    - Branches on known-false conditions (iffalse <true_const> → always skip)
    """
    result = []
    changed = False
    unreachable = False

    for instr in instructions:
        # Labels are always reachable (jump targets)
        if instr.op == 'label':
            unreachable = False
            result.append(instr.copy())
            continue

        # func_begin/func_end always kept
        if instr.op in ('func_begin', 'func_end'):
            unreachable = False
            result.append(instr.copy())
            continue

        # If we're in unreachable code, skip
        if unreachable:
            changed = True
            continue

        # After goto or return, subsequent code is unreachable
        if instr.op in ('goto', 'return'):
            result.append(instr.copy())
            unreachable = True
            continue

        # iffalse <constant> goto L
        # If constant is truthy (non-zero), iffalse never branches → remove it
        # If constant is falsy (zero), iffalse always branches → convert to goto
        if instr.op == 'iffalse' and is_number(instr.arg1):
            val = get_number(instr.arg1)
            if val == 0:
                # iffalse 0 goto L → always branches, becomes goto L
                result.append(GimpleStmt('goto', instr.arg2))
                unreachable = True
                changed = True
                continue
            else:
                # iffalse <non-zero> goto L → never branches, remove
                changed = True
                continue

        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 9: Loop Optimization (Loop-Invariant Code Motion)
# ═══════════════════════════════════════════════════════════════════════════

def loop_optimization(instructions):
    """Move loop-invariant computations out of loops.
    A computation is loop-invariant if its operands are defined outside the loop.
    """
    # Detect loops: find back-edges (goto to an earlier label)
    label_positions = {}
    for i, instr in enumerate(instructions):
        if instr.op == 'label':
            label_positions[instr.arg1] = i

    # Find loops: a loop is between a label and a goto that jumps back to it
    loops = []
    for i, instr in enumerate(instructions):
        if instr.op == 'goto' and instr.arg1 in label_positions:
            target_pos = label_positions[instr.arg1]
            if target_pos < i:
                loops.append((target_pos, i))  # (start, end) of loop

    if not loops:
        return copy_instructions(instructions), False

    changed = False
    result_instrs = copy_instructions(instructions)

    for loop_start, loop_end in loops:
        # Find variables defined inside the loop
        loop_defs = set()
        for i in range(loop_start, loop_end + 1):
            instr = result_instrs[i]
            if instr.result:
                loop_defs.add(instr.result)

        # Find loop-invariant instructions
        invariant_indices = []
        for i in range(loop_start + 1, loop_end):
            instr = result_instrs[i]
            if instr.op in ('label', 'goto', 'iffalse', 'return', 'print',
                             'param', 'call', 'func_begin', 'func_end', '='):
                continue
            if instr.op not in BINARY_OPS:
                continue

            # Check if both operands are defined outside the loop
            arg1_invariant = (is_number(instr.arg1) or
                              instr.arg1 not in loop_defs)
            arg2_invariant = (instr.arg2 is None or
                              is_number(instr.arg2) or
                              instr.arg2 not in loop_defs)

            if arg1_invariant and arg2_invariant:
                invariant_indices.append(i)

        if not invariant_indices:
            continue

        # Move invariant instructions before the loop
        moved = [result_instrs[i].copy() for i in invariant_indices]

        # Remove from inside the loop (reverse order to preserve indices)
        for i in sorted(invariant_indices, reverse=True):
            result_instrs.pop(i)

        # Insert before the loop start
        # Adjust loop_start: find the label position again
        adjusted_start = loop_start
        for m_instr in reversed(moved):
            result_instrs.insert(adjusted_start, m_instr)

        changed = True

    return result_instrs, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 10: Function Inlining
# ═══════════════════════════════════════════════════════════════════════════

def function_inlining(instructions, function_tacs, max_body_size=10):
    """Inline small function bodies at their call sites.
    Only inlines functions with body size <= max_body_size instructions.
    """
    # Detect entry-point functions: defined but never explicitly called.
    # These are never candidates for inlining (e.g. main).
    all_defined = {i.arg1 for i in instructions if i.op == 'func_begin'}
    all_called  = {i.arg1 for i in instructions if i.op == 'call'}
    entry_points = all_defined - all_called

    # Extract function definitions: name -> body_instructions
    func_defs = {}
    i = 0
    while i < len(instructions):
        instr = instructions[i]
        if instr.op == 'func_begin' and instr.arg1 not in entry_points:
            func_name = instr.arg1
            body = []
            i += 1
            while i < len(instructions) and instructions[i].op != 'func_end':
                body.append(instructions[i])
                i += 1
            if len(body) <= max_body_size:
                func_defs[func_name] = body
        i += 1

    if not func_defs:
        return copy_instructions(instructions), False, set()

    # Find the parameter names for each function from the original AST
    # We infer params by looking at param instructions before calls
    # and matching with function body variable usage

    result = []
    changed = False
    inlined_funcs = set()   # tracks which function names were actually inlined
    inline_counter = [0]

    def get_unique_suffix():
        inline_counter[0] += 1
        return f"_inline{inline_counter[0]}"

    i = 0
    while i < len(instructions):
        instr = instructions[i]

        # Look for: param a1; param a2; ... ; result = call func, N
        if instr.op == 'param':
            # Collect all params until we hit a call
            params_collected = [instr]
            j = i + 1
            while j < len(instructions) and instructions[j].op == 'param':
                params_collected.append(instructions[j])
                j += 1

            if (j < len(instructions) and
                    instructions[j].op == 'call' and
                    instructions[j].arg1 in func_defs):

                call_instr = instructions[j]
                func_name = call_instr.arg1
                func_body = func_defs[func_name]
                call_result = call_instr.result
                suffix = get_unique_suffix()

                # Collect argument values from param instructions
                arg_values = [p.arg1 for p in params_collected]

                # Find the parameter names used in the function body
                # by analyzing which variables appear but aren't defined
                # within the body (heuristic for simple functions)
                body_defs = set()
                body_uses = set()
                for bi in func_body:
                    # Skip labels — they aren't variable uses
                    if bi.op in ('label', 'goto', 'iffalse'):
                        continue
                    if bi.result:
                        body_defs.add(bi.result)
                    if bi.arg1 and not is_number(bi.arg1):
                        body_uses.add(bi.arg1)
                    if bi.arg2 and not is_number(bi.arg2):
                        body_uses.add(bi.arg2)

                # Parameters are variables used but not defined in body
                func_params = sorted(body_uses - body_defs)

                # Build param mapping
                param_map = {}
                for idx, param_name in enumerate(func_params):
                    if idx < len(arg_values):
                        param_map[param_name] = arg_values[idx]

                # Build a rename map for all temporaries/locals in the body
                # (variables defined inside the function that aren't params)
                rename_map = dict(param_map)  # start with param mappings
                for bi in func_body:
                    if bi.result and bi.result not in rename_map:
                        rename_map[bi.result] = bi.result + suffix

                # Helper to resolve a value through the rename map
                def resolve(val):
                    if val is None:
                        return None
                    return rename_map.get(val, val)

                # Inline the function body (skip labels — they belong to
                # the original function and would conflict in the caller)
                for bi in func_body:
                    if bi.op in ('label', 'goto', 'iffalse'):
                        continue  # skip control flow from inlined function
                    elif bi.op == 'return':
                        # return val → call_result = val
                        ret_val = resolve(bi.arg1)
                        if call_result:
                            result.append(GimpleStmt(
                                '=', ret_val, result=call_result
                            ))
                    else:
                        new_bi = bi.copy()
                        new_bi.arg1 = resolve(new_bi.arg1)
                        new_bi.arg2 = resolve(new_bi.arg2)
                        if new_bi.result:
                            new_bi.result = resolve(new_bi.result)
                        result.append(new_bi)

                changed = True
                inlined_funcs.add(func_name)
                i = j + 1
                continue

            # Not followed by an inlineable call, emit params normally
            for p in params_collected:
                result.append(p.copy())
            i = j
            continue

        result.append(instr.copy())
        i += 1

    return result, changed, inlined_funcs


# ═══════════════════════════════════════════════════════════════════════════
# PASS 11 (internal): Remove Inlined Functions
# ═══════════════════════════════════════════════════════════════════════════

def remove_inlined_functions(instructions, inlined_funcs):
    """Remove function definitions that were fully inlined at their call sites.
    inlined_funcs: the set of function names returned by function_inlining.
    """
    if not inlined_funcs:
        return copy_instructions(instructions), False

    result = []
    skip = False
    changed = False
    for instr in instructions:
        if instr.op == 'func_begin' and instr.arg1 in inlined_funcs:
            skip = True
            changed = True
            continue
        if instr.op == 'func_end' and skip:
            skip = False
            continue
        if skip:
            continue
        result.append(instr.copy())

    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# PASS 12 (internal): Redundant Goto Elimination
# ═══════════════════════════════════════════════════════════════════════════

def redundant_goto_elimination(instructions):
    """Remove 'goto <bb N>' when <bb N> is the very next label in sequence."""
    result = []
    changed = False
    n = len(instructions)
    for i, instr in enumerate(instructions):
        if instr.op == 'goto':
            # Find the next non-nothing instruction
            next_label = None
            for j in range(i + 1, n):
                if instructions[j].op == 'label':
                    next_label = instructions[j].arg1
                    break
                elif instructions[j].op not in ('func_begin', 'func_end'):
                    break
            if next_label == instr.arg1:
                changed = True
                continue  # skip this redundant goto
        result.append(instr.copy())
    return result, changed


# ═══════════════════════════════════════════════════════════════════════════
# Main Optimizer
# ═══════════════════════════════════════════════════════════════════════════

ALL_PASSES = [
    ("Constant Folding",                constant_folding),
    ("Constant Propagation",            constant_propagation),
    ("Algebraic Simplification",        algebraic_simplification),
    ("Strength Reduction",              strength_reduction),
    ("Copy Propagation",                copy_propagation),
    ("Common Subexpression Elimination", common_subexpression_elimination),
    ("Dead Code Elimination",           dead_code_elimination),
    ("Unreachable Code Elimination",    unreachable_code_elimination),
    ("Loop Optimization",               loop_optimization),
    ("Function Inlining",               None),  # handled specially
]


def optimize(instructions, function_tacs=None, verbose=True):
    """Run all optimization passes on the TAC instructions.

    Args:
        instructions: list of GimpleStmt
        function_tacs: dict of function_name -> body indices (for inlining)
        verbose: if True, print each pass's result

    Returns:
        optimized list of GimpleStmt, and a log of changes per pass
    """
    current = copy_instructions(instructions)
    pass_log = []

    inlined_funcs = set()
    for pass_num, (name, pass_fn) in enumerate(ALL_PASSES, 1):
        if name == "Function Inlining":
            new_instrs, changed, inlined_funcs = function_inlining(
                current, function_tacs or {}
            )
        else:
            new_instrs, changed = pass_fn(current)

        status = "CHANGED" if changed else "no change"
        pass_log.append((pass_num, name, changed, copy_instructions(new_instrs)))

        if verbose:
            print(f"\n{'='*65}")
            print(f"  PASS {pass_num}: {name} [{status}]")
            print(f"{'='*65}")
            print(format_gimple(new_instrs))

        current = new_instrs

    # --- Post-inlining cleanup: run to fixed point ---
    # After inlining, new constant-folding and copy-prop opportunities appear.
    # We iterate all cleanup passes until nothing changes anymore.
    cleanup_pass_fns = [
        constant_folding,
        constant_propagation,
        algebraic_simplification,
        copy_propagation,
        dead_code_elimination,
        unreachable_code_elimination,
        redundant_goto_elimination,
    ]

    any_cleanup = False
    for _round in range(10):  # max 10 rounds to guarantee termination
        round_changed = False
        for pass_fn in cleanup_pass_fns:
            new_instrs, changed = pass_fn(current)
            if changed:
                round_changed = True
                any_cleanup = True
            current = new_instrs
        if not round_changed:
            break  # fixed point reached

    # --- Remove fully-inlined function bodies ---
    current, inlined_removed = remove_inlined_functions(
        current, inlined_funcs
    )
    if inlined_removed:
        any_cleanup = True

    if any_cleanup and verbose:
        print(f"\n{'='*65}")
        print(f"  CLEANUP PASSES (fixed-point folding + dead code + goto elim)")
        print(f"{'='*65}")
        print(format_gimple(current))

    return current, pass_log
