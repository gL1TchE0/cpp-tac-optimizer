"""
GIMPLE Intermediate Representation Generator.
Converts an AST into GCC-style GIMPLE three-address statements.

GIMPLE is GCC's intermediate representation used for optimization.
Each statement has at most one operator and up to two operands.
Temporary variables use the naming convention _N (SSA-style).
Basic blocks are labeled as <bb N>.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ast_nodes import *


class GimpleStmt:
    """A single GIMPLE statement."""

    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def copy(self):
        return GimpleStmt(self.op, self.arg1, self.arg2, self.result)

    def __repr__(self):
        return f"Gimple({self.op}, {self.arg1}, {self.arg2}, {self.result})"

    def __str__(self):
        if self.op == 'label':
            return f"  {self.arg1}:"
        elif self.op == 'goto':
            return f"    goto {self.arg1};"
        elif self.op == 'iffalse':
            # Display more intuitively as a negative condition:
            # internal semantics: if (arg1 == 0) goto arg2;
            return f"    if ({self.arg1}) goto {self.arg2};"
        elif self.op == 'param':
            return f"    param {self.arg1};"
        elif self.op == 'call':
            if self.result:
                return f"    {self.result} = {self.arg1} ({self.arg2});"
            return f"    {self.arg1} ({self.arg2});"
        elif self.op == 'return':
            if self.arg1 is not None:
                return f"    return {self.arg1};"
            return f"    return;"
        elif self.op == 'print':
            return f"    __builtin_print ({self.arg1});"
        elif self.op == 'func_begin':
            return f"FUNC_BEGIN {self.arg1}"
        elif self.op == 'func_end':
            return f"FUNC_END {self.arg1}"
        elif self.op == '=':
            return f"    {self.result} = {self.arg1};"
        elif self.op in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=',
                         '==', '!=', '&&', '||', '<<', '>>'):
            return f"    {self.result} = {self.arg1} {self.op} {self.arg2};"
        elif self.op == 'neg':
            return f"    {self.result} = -{self.arg1};"
        elif self.op == 'not':
            return f"    {self.result} = !{self.arg1};"
        else:
            return f"    {self.result} = {self.op} {self.arg1};"


def format_gimple(instructions):
    """Format GIMPLE instructions with proper function structure.

    Wraps function bodies in declarations with variable listings,
    matching GCC's -fdump-tree-gimple output style.
    """
    lines = []
    i = 0

    while i < len(instructions):
        instr = instructions[i]

        if instr.op == 'func_begin':
            func_name = instr.arg1
            # Skip internal GCC helper functions (they are not part of the
            # user-level program we want to display, e.g. __tcf_0, static
            # initialization helpers, etc.).
            if func_name.startswith("__"):
                # Fast-forward to matching func_end
                i += 1
                while i < len(instructions) and instructions[i].op != 'func_end':
                    i += 1
                # func_end will be skipped by the main loop increment
                continue
            # Collect all instructions in this function
            body = []
            i += 1
            while i < len(instructions) and instructions[i].op != 'func_end':
                body.append(instructions[i])
                i += 1

            # Gather all variables (temporaries and user variables)
            temps = set()
            user_vars = set()
            for stmt in body:
                for val in [stmt.arg1, stmt.arg2, stmt.result]:
                    if val is None:
                        continue
                    if _is_temp(val):
                        temps.add(val)
                    elif _is_user_var(val):
                        user_vars.add(val)

            # Format function header
            lines.append(f"{func_name} ()")
            lines.append("{")

            # Variable declarations
            if temps:
                sorted_temps = sorted(temps, key=_temp_sort_key)
                lines.append(f"  int {', '.join(sorted_temps)};")
            if user_vars:
                sorted_vars = sorted(user_vars)
                lines.append(f"  int {', '.join(sorted_vars)};")

            if temps or user_vars:
                lines.append("")

            for stmt in body:
                lines.append(str(stmt))

            lines.append("}")
            lines.append("")

        i += 1

    return '\n'.join(lines)


def _is_temp(name):
    """Check if a variable name is a GIMPLE temporary (_N pattern)."""
    if name and name.startswith('_') and name[1:].replace('_', '').replace('inline', '').isdigit():
        return True
    # Also handle suffixed temps like _0_inline1
    if name and name.startswith('_'):
        parts = name.split('_', 2)
        if len(parts) >= 2 and parts[1].isdigit():
            return True
    return False


def _is_user_var(name):
    """Check if a string is a user variable (not a number, label, or temp)."""
    if name is None:
        return False
    try:
        float(name)
        return False
    except ValueError:
        pass
    # Treat any GIMPLE label-like tokens as non-vars
    if name.startswith('<') or name.startswith('_'):
        return False
    # Obvious boolean literals
    if name in ('0', '1'):
        return False
    # Heuristic: anything that looks like an expression (spaces, operators,
    # parentheses, logical not) is not a "user variable" for declaration
    # purposes in formatted GIMPLE.
    if any(ch in name for ch in (" ", "(", ")", "!", "&", "|", "<", ">", "=")):
        return False
    return True


def _temp_sort_key(name):
    """Sort temporaries numerically: _0, _1, _2, ..."""
    try:
        return int(name.split('_')[1])
    except (IndexError, ValueError):
        return 0


class GimpleGenerator:
    """Converts an AST into GIMPLE three-address statements."""

    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.bb_count = 2  # bb 0 = ENTRY, bb 1 = EXIT, user blocks start at 2
        self.function_tacs = {}  # func_name -> [body indices]

    def new_temp(self):
        """Generate a new GIMPLE temporary: _0, _1, _2, ..."""
        name = f"_{self.temp_count}"
        self.temp_count += 1
        return name

    def new_label(self):
        """Generate a new basic block label: <bb 2>, <bb 3>, ..."""
        name = f"<bb {self.bb_count}>"
        self.bb_count += 1
        return name

    def emit(self, op, arg1=None, arg2=None, result=None):
        """Emit a single GIMPLE statement."""
        stmt = GimpleStmt(op, arg1, arg2, result)
        self.instructions.append(stmt)
        return stmt

    # ─── Main Entry ──────────────────────────────────────────────────────

    def generate(self, program):
        """Generate GIMPLE for the entire program."""
        for func in program.functions:
            self._gen_function(func)
        return self.instructions

    def _gen_function(self, func):
        self.emit('func_begin', func.name)
        # Each function starts at <bb 2> (bb 0 = ENTRY, bb 1 = EXIT)
        self.bb_count = 3  # next generated label will be <bb 3>
        start_idx = len(self.instructions)
        # Emit entry basic block label
        self.emit('label', '<bb 2>')
        self._gen_block(func.body)
        end_idx = len(self.instructions)
        self.function_tacs[func.name] = list(range(start_idx, end_idx))
        self.emit('func_end', func.name)

    def _gen_block(self, block):
        for stmt in block.statements:
            self._gen_statement(stmt)

    # ─── Statements ──────────────────────────────────────────────────────

    def _gen_statement(self, stmt):
        if isinstance(stmt, VarDecl):
            self._gen_var_decl(stmt)
        elif isinstance(stmt, Assignment):
            self._gen_assignment(stmt)
        elif isinstance(stmt, IfStmt):
            self._gen_if(stmt)
        elif isinstance(stmt, WhileStmt):
            self._gen_while(stmt)
        elif isinstance(stmt, ForStmt):
            self._gen_for(stmt)
        elif isinstance(stmt, ReturnStmt):
            self._gen_return(stmt)
        elif isinstance(stmt, PrintStmt):
            self._gen_print(stmt)
        elif isinstance(stmt, Block):
            self._gen_block(stmt)
        else:
            self._gen_expr(stmt)

    def _gen_var_decl(self, decl):
        if decl.init is not None:
            place = self._gen_expr(decl.init)
            self.emit('=', str(place), result=decl.name)

    def _gen_assignment(self, assign):
        place = self._gen_expr(assign.value)
        if assign.op == '=':
            self.emit('=', str(place), result=assign.name)
        else:
            op = assign.op[0]
            temp = self.new_temp()
            self.emit(op, assign.name, str(place), temp)
            self.emit('=', temp, result=assign.name)

    def _gen_if(self, stmt):
        cond = self._gen_expr(stmt.condition)

        if stmt.else_body:
            label_else = self.new_label()
            label_end = self.new_label()
            self.emit('iffalse', str(cond), label_else)
            self._gen_block(stmt.then_body)
            self.emit('goto', label_end)
            self.emit('label', label_else)
            self._gen_block(stmt.else_body)
            self.emit('label', label_end)
        else:
            label_end = self.new_label()
            self.emit('iffalse', str(cond), label_end)
            self._gen_block(stmt.then_body)
            self.emit('label', label_end)

    def _gen_while(self, stmt):
        label_start = self.new_label()
        label_end = self.new_label()

        self.emit('label', label_start)
        cond = self._gen_expr(stmt.condition)
        self.emit('iffalse', str(cond), label_end)
        self._gen_block(stmt.body)
        self.emit('goto', label_start)
        self.emit('label', label_end)

    def _gen_for(self, stmt):
        if stmt.init:
            self._gen_statement(stmt.init)

        label_start = self.new_label()
        label_end = self.new_label()

        self.emit('label', label_start)

        if stmt.condition:
            cond = self._gen_expr(stmt.condition)
            self.emit('iffalse', str(cond), label_end)

        self._gen_block(stmt.body)

        if stmt.update:
            if isinstance(stmt.update, Assignment):
                self._gen_assignment(stmt.update)
            else:
                self._gen_expr(stmt.update)

        self.emit('goto', label_start)
        self.emit('label', label_end)

    def _gen_return(self, stmt):
        if stmt.value:
            place = self._gen_expr(stmt.value)
            self.emit('return', str(place))
        else:
            self.emit('return')

    def _gen_print(self, stmt):
        for val_expr in stmt.values:
            place = self._gen_expr(val_expr)
            self.emit('print', str(place))

    # ─── Expressions ─────────────────────────────────────────────────────

    def _gen_expr(self, expr):
        """Generate GIMPLE for an expression, return the 'place' holding the result."""

        if isinstance(expr, Number):
            return str(expr.value)

        elif isinstance(expr, BoolLiteral):
            return '1' if expr.value else '0'

        elif isinstance(expr, Identifier):
            return expr.name

        elif isinstance(expr, BinaryExpr):
            left = self._gen_expr(expr.left)
            right = self._gen_expr(expr.right)
            temp = self.new_temp()
            self.emit(expr.op, str(left), str(right), temp)
            return temp

        elif isinstance(expr, UnaryExpr):
            operand = self._gen_expr(expr.operand)
            if expr.op in ('++', '--'):
                delta_op = '+' if expr.op == '++' else '-'
                temp = self.new_temp()
                self.emit(delta_op, str(operand), '1', temp)
                self.emit('=', temp, result=str(operand))
                return str(operand)
            elif expr.op == '-':
                temp = self.new_temp()
                self.emit('neg', str(operand), result=temp)
                return temp
            elif expr.op == '!':
                temp = self.new_temp()
                self.emit('not', str(operand), result=temp)
                return temp

        elif isinstance(expr, FunctionCall):
            for arg in expr.args:
                place = self._gen_expr(arg)
                self.emit('param', str(place))
            temp = self.new_temp()
            self.emit('call', expr.name, str(len(expr.args)), temp)
            return temp

        return str(expr)


# ════════════════════════════════════════════════════════════════════════════
# GCC-BACKED GIMPLE LOADER
# ════════════════════════════════════════════════════════════════════════════


def _run_gcc_dump_gimple(source_path, gcc='g++'):
    """Invoke GCC to produce a -fdump-tree-gimple file for the given source.

    Returns the path to the generated .gimple file.
    """
    source_path = Path(source_path).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Input source file not found: {source_path}")

    tmpdir = Path(tempfile.mkdtemp(prefix="gcc_gimple_"))
    try:
        # Copy the source into the temp directory so GCC writes dumps there
        tmp_src = tmpdir / source_path.name
        shutil.copy2(source_path, tmp_src)

        # Compile with GIMPLE dump enabled. We don't care about the object file,
        # only about the dump that GCC writes next to the source.
        cmd = [
            gcc,
            "-O0",
            "-fdump-tree-gimple",
            "-c",
            str(tmp_src),
        ]

        proc = subprocess.run(
            cmd,
            cwd=str(tmpdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"GCC failed with exit code {proc.returncode}:\n{proc.stderr}"
            )

        # Find the .gimple dump file GCC produced
        gimple_files = list(tmpdir.glob("*.gimple"))
        if not gimple_files:
            raise FileNotFoundError(
                "GCC did not produce a .gimple dump file "
                "(expected with -fdump-tree-gimple)."
            )

        # If multiple, pick the most recently modified
        gimple_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return gimple_files[0]
    finally:
        # NOTE: We intentionally do not delete tmpdir so users can inspect
        # the raw dump if they wish. Uncomment to auto-clean:
        # shutil.rmtree(tmpdir, ignore_errors=True)
        pass


def _parse_gcc_gimple_dump(dump_path):
    """Parse a GCC -fdump-tree-gimple file into GimpleStmt objects.

    This is a *conservative* parser that focuses on the core patterns used
    by the optimizer: assignments, arithmetic, comparisons, gotos, labels,
    and returns. More complex constructs are treated as opaque assignments.
    """
    dump_path = Path(dump_path)
    text = dump_path.read_text(encoding="utf-8", errors="replace")

    # Labels for basic blocks or compiler-generated targets
    generic_label_re = re.compile(r"^<([^>]+)>:")
    goto_re = re.compile(r"^\s*goto\s+<([^>]+)>;")
    return_re = re.compile(r"^\s*return(?:\s+(.+))?;")
    assign_re = re.compile(r"^\s*([\w\.]+)\s*=\s*(.+);")

    # Binary ops ordered by length to avoid partial matches
    bin_ops = [
        "<=", ">=", "==", "!=", "&&", "||", "<<", ">>",
        "+", "-", "*", "/", "%", "<", ">",
    ]

    def parse_rhs(rhs):
        rhs = rhs.strip()

        # Heuristic: treat expressions that look like function calls
        # (including operator<< calls) as opaque RHS for a simple
        # assignment, so that dead-code elimination preserves their
        # side effects.
        if "(" in rhs and rhs.endswith(")") and "::operator" in rhs:
            return "=", rhs, None

        # Unary negation / logical not
        if rhs.startswith("-") and " " not in rhs[1:]:
            return "neg", rhs[1:].strip(), None
        if rhs.startswith("!") and " " not in rhs[1:]:
            return "not", rhs[1:].strip(), None

        # Binary operation
        for op in bin_ops:
            parts = rhs.split(op)
            if len(parts) == 2:
                left, right = parts[0].strip(), parts[1].strip()
                if left and right:
                    return op, left, right

        # Fallback: treat as simple assignment
        return "=", rhs, None

    instructions = []
    function_tacs = {}
    current_func = None
    func_start = None
    brace_depth = 0  # track nested scopes within a function

    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()

        # Skip GCC comments and empty lines
        if not stripped or stripped.startswith(";;"):
            continue

        # Update brace depth for function bodies
        if current_func is not None:
            if "{" in stripped:
                brace_depth += stripped.count("{")
            if "}" in stripped:
                # If this closing brace ends the function body, handle below
                brace_depth -= stripped.count("}")
                if brace_depth <= 0:
                    function_tacs[current_func] = list(
                        range(func_start, len(instructions))
                    )
                    instructions.append(GimpleStmt("func_end", current_func))
                    current_func = None
                    func_start = None
                    brace_depth = 0
                    continue

        # Function header lines look like:
        #   int square(int) (int x)
        #   int add(int, int) (int a, int b)
        #   int main() ()
        #   void __static_initialization_and_destruction_0(int, int) (...)
        if current_func is None and "(" in stripped and not stripped.endswith(";"):
            if not stripped.startswith(("struct ", "class ", "union ")):
                # Take the last word before the first '(' as the function name.
                prefix = stripped.split("(", 1)[0].strip()
                parts = prefix.split()
                if parts:
                    name = parts[-1]
                    # Close previous function if any (defensive, though we
                    # shouldn't normally see nested functions in C++).
                    if current_func is not None:
                        function_tacs[current_func] = list(
                            range(func_start, len(instructions))
                        )
                        instructions.append(GimpleStmt("func_end", current_func))

                    current_func = name
                    func_start = len(instructions)
                    brace_depth = 0
                    instructions.append(GimpleStmt("func_begin", name))
                    continue

        # Basic block / compiler labels: <bb 2>: or <D.35869>:
        m_lbl = generic_label_re.match(stripped)
        if m_lbl:
            label_name = m_lbl.group(1)
            instructions.append(GimpleStmt("label", f"<{label_name}>"))
            continue

        # GCC-style conditional branch:
        #   if (COND) goto <T>; else goto <F>;
        # We encode this as:
        #   iffalse !COND, <T>
        # so that our decompiler sees the loop/if condition as (!COND) and
        # emits `while (!COND)` or `if (!COND)` consistently with control flow.
        if stripped.startswith("if ") and " goto <" in stripped and " else goto <" in stripped:
            try:
                cond_part, rest = stripped.split(")", 1)
                cond_expr = cond_part.split("(", 1)[1].strip()
                # rest is like: " goto <T>; else goto <F>;"
                # First target (true branch)
                t_start = rest.index("<") + 1
                t_end = rest.index(">", t_start)
                true_label = rest[t_start:t_end]
                # Build logical negation of the condition for our representation
                neg_cond = f"!({cond_expr})"
                instructions.append(
                    GimpleStmt("iffalse", neg_cond, f"<{true_label}>")
                )
                continue
            except Exception:
                # Fall back to normal parsing if anything goes wrong
                pass

        # Goto
        m_goto = goto_re.match(stripped)
        if m_goto:
            target = m_goto.group(1)
            instructions.append(GimpleStmt("goto", f"<{target}>"))
            continue

        # Return
        m_ret = return_re.match(stripped)
        if m_ret:
            val = m_ret.group(1)
            if val is not None:
                val = val.strip()
            instructions.append(GimpleStmt("return", val))
            continue

        # Assignment / expression
        m_asn = assign_re.match(stripped)
        if m_asn:
            lhs = m_asn.group(1)
            rhs = m_asn.group(2).strip()
            op, arg1, arg2 = parse_rhs(rhs)
            if op == "=" and arg2 is None:
                instructions.append(GimpleStmt("=", arg1, result=lhs))
            elif op in ("neg", "not"):
                instructions.append(GimpleStmt(op, arg1, result=lhs))
            else:
                instructions.append(GimpleStmt(op, arg1, arg2, lhs))
            continue

        # Fallback: ignore unrecognized lines; they may be GCC metadata or
        # constructs we don't currently translate. The optimizer will simply
        # not see them.
        continue

    # Close trailing function if file ended without explicit balanced braces
    if current_func is not None:
        function_tacs[current_func] = list(
            range(func_start, len(instructions))
        )
        instructions.append(GimpleStmt("func_end", current_func))

    return instructions, function_tacs


def generate_from_gcc(source_path, gcc="g++"):
    """Run GCC to dump real GIMPLE and parse it into our IR.

    Returns:
        (instructions, function_tacs)
    """
    dump_path = _run_gcc_dump_gimple(source_path, gcc=gcc)
    return _parse_gcc_gimple_dump(dump_path)

