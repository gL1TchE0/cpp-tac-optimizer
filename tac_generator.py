"""
Three-Address Code (TAC) Generator.
Walks the AST and emits TAC instructions.
Each instruction has at most one operator and up to two operands.
"""

from ast_nodes import *


class TACInstruction:
    """A single Three-Address Code instruction."""

    def __init__(self, op, arg1=None, arg2=None, result=None):
        self.op = op
        self.arg1 = arg1
        self.arg2 = arg2
        self.result = result

    def copy(self):
        return TACInstruction(self.op, self.arg1, self.arg2, self.result)

    def __repr__(self):
        return f"TAC({self.op}, {self.arg1}, {self.arg2}, {self.result})"

    def __str__(self):
        if self.op == 'label':
            return f"{self.arg1}:"
        elif self.op == 'goto':
            return f"    goto {self.arg1}"
        elif self.op == 'iffalse':
            return f"    iffalse {self.arg1} goto {self.arg2}"
        elif self.op == 'param':
            return f"    param {self.arg1}"
        elif self.op == 'call':
            if self.result:
                return f"    {self.result} = call {self.arg1}, {self.arg2}"
            return f"    call {self.arg1}, {self.arg2}"
        elif self.op == 'return':
            return f"    return {self.arg1}" if self.arg1 is not None else "    return"
        elif self.op == 'print':
            return f"    print {self.arg1}"
        elif self.op == 'func_begin':
            return f"\nfunc_begin {self.arg1}"
        elif self.op == 'func_end':
            return f"func_end {self.arg1}"
        elif self.op == '=':
            return f"    {self.result} = {self.arg1}"
        elif self.op in ('+', '-', '*', '/', '%', '<', '>', '<=', '>=',
                         '==', '!=', '&&', '||', '<<', '>>'):
            return f"    {self.result} = {self.arg1} {self.op} {self.arg2}"
        elif self.op == 'neg':
            return f"    {self.result} = -{self.arg1}"
        elif self.op == 'not':
            return f"    {self.result} = !{self.arg1}"
        else:
            return f"    {self.result} = {self.op} {self.arg1}"


def format_tac(instructions):
    """Format a list of TAC instructions as a readable string."""
    return '\n'.join(str(instr) for instr in instructions)


class TACGenerator:
    """Converts an AST into Three-Address Code."""

    def __init__(self):
        self.instructions = []
        self.temp_count = 0
        self.label_count = 0
        self.function_tacs = {}  # func_name -> [TAC instructions]

    def new_temp(self):
        """Generate a new temporary variable name: t0, t1, t2, ..."""
        name = f"t{self.temp_count}"
        self.temp_count += 1
        return name

    def new_label(self):
        """Generate a new label name: L0, L1, L2, ..."""
        name = f"L{self.label_count}"
        self.label_count += 1
        return name

    def emit(self, op, arg1=None, arg2=None, result=None):
        """Emit a single TAC instruction."""
        instr = TACInstruction(op, arg1, arg2, result)
        self.instructions.append(instr)
        return instr

    # ─── Main Entry ──────────────────────────────────────────────────────

    def generate(self, program):
        """Generate TAC for the entire program."""
        for func in program.functions:
            self._gen_function(func)
        return self.instructions

    def _gen_function(self, func):
        self.emit('func_begin', func.name)
        start_idx = len(self.instructions)
        self._gen_block(func.body)
        end_idx = len(self.instructions)
        # Store function body TAC (for later inlining)
        self.function_tacs[func.name] = list(
            range(start_idx, end_idx)
        )
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
            # Expression statement (e.g., i++, function call)
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
            # Compound assignment: +=, -=, *=, /=
            op = assign.op[0]  # '+=' -> '+'
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
        # Init
        if stmt.init:
            self._gen_statement(stmt.init)

        label_start = self.new_label()
        label_end = self.new_label()

        self.emit('label', label_start)

        # Condition
        if stmt.condition:
            cond = self._gen_expr(stmt.condition)
            self.emit('iffalse', str(cond), label_end)

        # Body
        self._gen_block(stmt.body)

        # Update
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
        """Generate TAC for an expression, return the 'place' holding the result."""

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
                # i++ or ++i  →  i = i + 1
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
            # Push params, then call
            for arg in expr.args:
                place = self._gen_expr(arg)
                self.emit('param', str(place))
            temp = self.new_temp()
            self.emit('call', expr.name, str(len(expr.args)), temp)
            return temp

        return str(expr)
