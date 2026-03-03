"""
GIMPLE to C++ Decompiler.

Converts optimized GIMPLE IR back to readable C++ source code.

Strategy:
  1. Split instructions into per-function basic blocks.
  2. Build a label-to-index map and detect back-edges (loops).
  3. Inline single-use temporaries into their consuming expression.
  4. Walk the block sequence, emitting while/if/if-else as structures.
"""

from gimple_generator import GimpleStmt  # noqa: F401 (ensure import resolves)


# ───────────────────────── helpers ───────────────────────────────────────────

def _is_temp(name):
    if not name or not name.startswith('_'):
        return False
    parts = name.split('_', 2)
    return len(parts) >= 2 and parts[1].isdigit()


def _is_literal(val):
    if val is None:
        return True
    try:
        float(val)
        return True
    except ValueError:
        return val.startswith('<bb')


def _count_uses(instrs):
    """Count how many times each name appears as an operand (read)."""
    uses = {}
    for s in instrs:
        for val in (s.arg1, s.arg2):
            if val and not _is_literal(val) and s.op != 'call':
                uses[val] = uses.get(val, 0) + 1
    return uses


# ───────────────────── per-function blocks ───────────────────────────────────

def _extract_functions(instructions):
    """Yield (func_name, [GimpleStmt]) for each function in the stream."""
    i = 0
    while i < len(instructions):
        s = instructions[i]
        if s.op == 'func_begin':
            name, body, i = s.arg1, [], i + 1
            while i < len(instructions) and instructions[i].op != 'func_end':
                body.append(instructions[i])
                i += 1
            yield name, body
        i += 1


def _build_blocks(instrs):
    """
    Split flat instruction list into basic blocks.
    Returns list of {'label': str|None, 'stmts': list, 'index': int}.
    """
    blocks, cur = [], {'label': None, 'stmts': [], 'index': 0}
    for s in instrs:
        if s.op == 'label':
            if cur['stmts'] or cur['label'] is not None:
                blocks.append(cur)
            cur = {'label': s.arg1, 'stmts': [], 'index': len(blocks)}
        else:
            cur['stmts'].append(s)
    if cur['stmts'] or cur['label'] is not None:
        blocks.append(cur)
    return blocks


# ───────────────────── expression inliner ────────────────────────────────────

class ExprInliner:
    """
    For every temporary that is defined exactly once and used exactly once,
    substitute its defining expression directly into the use site so the
    decompiled C++ looks like a single compound expression.
    """

    def __init__(self, instrs):
        uses         = _count_uses(instrs)
        self._map    = {}          # temp -> expr string
        self._skip   = set()      # instruction indices to suppress
        self._skip_stmts = set()  # GimpleStmt objects to suppress (by id)

        EXPR_OPS = {'+', '-', '*', '/', '%', '<', '>', '<=', '>=',
                    '==', '!=', '&&', '||', '<<', '>>',
                    '=', 'neg', 'not'}

        for idx, s in enumerate(instrs):
            if (s.op in EXPR_OPS
                    and _is_temp(s.result)
                    and uses.get(s.result, 0) == 1):
                self._map[s.result] = self._build(s)
                self._skip.add(idx)
                self._skip_stmts.add(id(s))

    def _build(self, s):
        a1 = self.resolve(s.arg1)
        a2 = self.resolve(s.arg2)
        op = s.op
        if op == '=':    return a1
        if op == 'neg':  return f"-{a1}"
        if op == 'not':  return f"!{a1}"
        return f"({a1} {op} {a2})"

    def resolve(self, val):
        return self._map.get(val, val) if val is not None else ''

    def is_skipped(self, s):
        return id(s) in self._skip_stmts


# ───────────────────── control-flow emitter ──────────────────────────────────

class Emitter:
    """
    Reconstructs structured control flow (while, if, if-else) from the
    basic-block list and emits indented C++ lines.
    """

    def __init__(self, blocks, inliner):
        self.blocks   = blocks
        self.inliner  = inliner
        self.lbl_idx  = {b['label']: b['index']
                         for b in blocks if b['label'] is not None}
        # Identify loop headers: blocks whose label is the target of a back-edge
        self.loop_headers = self._find_loop_headers()
        self.done     = set()     # blocks already emitted
        self.out      = []

    def _find_loop_headers(self):
        """Return set of block indices that are targets of backward gotos."""
        headers = set()
        for b in self.blocks:
            stmts = b['stmts']
            if stmts and stmts[-1].op == 'goto':
                target = stmts[-1].arg1
                t_idx  = self.lbl_idx.get(target, -1)
                if t_idx <= b['index']:      # back-edge
                    headers.add(t_idx)
        return headers

    # ── public entry ─────────────────────────────────────────────────────────

    def run(self, indent=1):
        i = 0
        while i < len(self.blocks):
            i = self._emit(i, indent)
        return self.out

    # ── recursive block emitter ───────────────────────────────────────────────

    def _emit(self, idx, indent):
        if idx >= len(self.blocks) or idx in self.done:
            return idx + 1

        b     = self.blocks[idx]
        stmts = b['stmts']
        self.done.add(idx)
        pad   = '    ' * indent

        # ── Case 1: loop header ───────────────────────────────────────────────
        if idx in self.loop_headers:
            # The loop block structure from our GIMPLE generator:
            #   [preamble stmts...]     <- may include cond computation
            #   iffalse cond, <exit>   <- the loop test
            #   [body stmts...]
            #   goto <this label>      <- back-edge (last stmt)
            #
            # Find the iffalse position by scanning (not necessarily first).
            iffalse_pos = next(
                (si for si, s in enumerate(stmts) if s.op == 'iffalse'), None
            )

            if iffalse_pos is not None:
                exit_lbl = stmts[iffalse_pos].arg2
                exit_idx = self.lbl_idx.get(exit_lbl, len(self.blocks))
                cond_raw = self.inliner.resolve(stmts[iffalse_pos].arg1)

                # The variable that the iffalse tests (e.g. _11 in "if _11 == 0")
                # is computed in the preamble. We suppress those "cond-setup"
                # statements because the condition is already visible inside
                # while(cond_raw); emitting them before the loop is redundant.
                cond_var = stmts[iffalse_pos].arg1  # e.g. "_11"

                # Emit preamble (skip stmts that only compute the cond variable)
                for s in stmts[:iffalse_pos]:
                    if s.result == cond_var:   # suppress cond-setup
                        continue
                    line = self._stmt(s, indent)
                    if line:
                        self.out.append(line)

                # Body = stmts after iffalse, excluding the trailing goto
                body_stmts = stmts[iffalse_pos + 1 : -1]

                self.out.append(f"{pad}while ({cond_raw}) {{")
                for s in body_stmts:
                    line = self._stmt(s, indent + 1)
                    if line:
                        self.out.append(line)
                self.out.append(f"{pad}}}")
                return self._emit(exit_idx, indent)

        # ── Case 2: block ending with iffalse (if / if-else) ─────────────────
        preamble, term = self._split(stmts)
        for s in preamble:
            line = self._stmt(s, indent)
            if line:
                self.out.append(line)

        if term is None:
            return idx + 1

        if term.op == 'return':
            val = self.inliner.resolve(term.arg1) if term.arg1 else ''
            self.out.append(f"{pad}return {val};")
            return idx + 1

        if term.op == 'goto':
            t_idx = self.lbl_idx.get(term.arg1, -1)
            if t_idx > idx:
                return self._emit(t_idx, indent)
            return idx + 1   # back-edge handled as part of while above

        if term.op == 'iffalse':
            cond_raw = self.inliner.resolve(term.arg1)
            f_lbl    = term.arg2
            f_idx    = self.lbl_idx.get(f_lbl, len(self.blocks))

            # Check if the then-branch ends with a goto (→ if-else)
            then_end_idx = f_idx - 1
            has_else     = False
            end_idx      = f_idx

            if (0 <= then_end_idx < len(self.blocks)):
                then_last = self.blocks[then_end_idx]['stmts']
                if then_last and then_last[-1].op == 'goto':
                    end_lbl  = then_last[-1].arg1
                    end_idx  = self.lbl_idx.get(end_lbl, f_idx)
                    has_else = end_idx > f_idx   # sanity: else must come after

            self.out.append(f"{pad}if ({cond_raw}) {{")
            i2 = idx + 1
            while i2 < f_idx:
                i2 = self._emit(i2, indent + 1)

            if has_else:
                self.out.append(f"{pad}}} else {{")
                i2 = f_idx
                while i2 < end_idx:
                    i2 = self._emit(i2, indent + 1)
                self.out.append(f"{pad}}}")
                return self._emit(end_idx, indent)
            else:
                self.out.append(f"{pad}}}")
                return self._emit(f_idx, indent)

        return idx + 1

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _split(stmts):
        if stmts and stmts[-1].op in ('goto', 'iffalse', 'return'):
            return stmts[:-1], stmts[-1]
        return stmts, None

    def _stmt(self, s, indent):
        # Suppress definitions of inlined temps
        if self.inliner.is_skipped(s):
            return None

        pad = '    ' * indent
        r   = self.inliner
        op  = s.op

        if op == '=':
            rhs = r.resolve(s.arg1)
            if s.result == rhs:
                return None
            return f"{pad}{s.result} = {rhs};"

        if op in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=',
                  '==', '!=', '&&', '||', '<<', '>>'):
            rhs = f"{r.resolve(s.arg1)} {op} {r.resolve(s.arg2)}"
            return f"{pad}{s.result} = {rhs};"

        if op == 'neg':
            return f"{pad}{s.result} = -{r.resolve(s.arg1)};"
        if op == 'not':
            return f"{pad}{s.result} = !{r.resolve(s.arg1)};"

        if op == 'print':
            return f"{pad}cout << {r.resolve(s.arg1)} << endl;"

        if op in ('param', 'call', 'label', 'func_begin', 'func_end'):
            return None

        return None


# ───────────────────── variable declaration helpers ──────────────────────────

def _declared_vars(instrs):
    """Return ordered list of user-visible variables (non-temp results)."""
    seen, out = set(), []
    for s in instrs:
        if s.result and not _is_temp(s.result) and s.result not in seen:
            out.append(s.result)
            seen.add(s.result)
    return out


def _remaining_temps(instrs, inliner):
    """Return temps that survive (used more than once → not inlined)."""
    seen, out = set(), []
    for s in instrs:
        if (s.result and _is_temp(s.result)
                and s.result not in inliner._map
                and s.result not in seen):
            out.append(s.result)
            seen.add(s.result)
    return out


# ───────────────────── public entry point ────────────────────────────────────

def gimple_to_cpp(instructions):
    """
    Convert a list of optimized GimpleStmt objects to C++ source.
    Returns the full C++ code as a string.
    """
    parts = []
    for func_name, body in _extract_functions(instructions):
        # Skip internal GCC helper functions; they are implementation details
        # (e.g. iostream initialization) and not part of the user's program.
        if func_name.startswith("__"):
            continue
        parts.append(_decompile_function(func_name, body))
    return '\n\n'.join(parts)


def _decompile_function(func_name, instrs):
    lines = []

    # Return type heuristic
    has_return_val = any(s.op == 'return' and s.arg1 for s in instrs)
    ret = 'int' if has_return_val else 'void'

    lines.append(f"{ret} {func_name}()")
    lines.append("{")

    inliner = ExprInliner(instrs)

    # Variable declarations
    uv = _declared_vars(instrs)
    rt = _remaining_temps(instrs, inliner)

    if uv:
        lines.append(f"    int {', '.join(uv)};")
    if rt:
        lines.append(f"    int {', '.join(rt)};")
    if uv or rt:
        lines.append("")

    blocks = _build_blocks(instrs)
    emitter = Emitter(blocks, inliner)
    for line in emitter.run(indent=1):
        if line is not None:
            lines.append(line)

    lines.append("}")
    return '\n'.join(lines)
