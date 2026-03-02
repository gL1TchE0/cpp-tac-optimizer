"""
AST Node definitions for the C++ subset parser.
Each node represents a construct in the source language.
"""


class ASTNode:
    """Base class for all AST nodes."""
    pass


# ─── Expressions ─────────────────────────────────────────────────────────────

class Number(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"Number({self.value})"


class BoolLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"BoolLiteral({self.value})"


class Identifier(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name})"


class BinaryExpr(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinaryExpr({self.op}, {self.left}, {self.right})"


class UnaryExpr(ASTNode):
    def __init__(self, op, operand, prefix=True):
        self.op = op
        self.operand = operand
        self.prefix = prefix

    def __repr__(self):
        return f"UnaryExpr({self.op}, {self.operand})"


class FunctionCall(ASTNode):
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"FunctionCall({self.name}, {self.args})"


# ─── Statements ──────────────────────────────────────────────────────────────

class VarDecl(ASTNode):
    def __init__(self, var_type, name, init=None):
        self.var_type = var_type
        self.name = name
        self.init = init

    def __repr__(self):
        return f"VarDecl({self.var_type}, {self.name}, {self.init})"


class Assignment(ASTNode):
    def __init__(self, name, value, op='='):
        self.name = name
        self.value = value
        self.op = op

    def __repr__(self):
        return f"Assignment({self.name} {self.op} {self.value})"


class IfStmt(ASTNode):
    def __init__(self, condition, then_body, else_body=None):
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body

    def __repr__(self):
        return f"IfStmt({self.condition})"


class WhileStmt(ASTNode):
    def __init__(self, condition, body):
        self.condition = condition
        self.body = body

    def __repr__(self):
        return f"WhileStmt({self.condition})"


class ForStmt(ASTNode):
    def __init__(self, init, condition, update, body):
        self.init = init
        self.condition = condition
        self.update = update
        self.body = body

    def __repr__(self):
        return f"ForStmt(...)"


class ReturnStmt(ASTNode):
    def __init__(self, value=None):
        self.value = value

    def __repr__(self):
        return f"ReturnStmt({self.value})"


class PrintStmt(ASTNode):
    def __init__(self, values):
        self.values = values

    def __repr__(self):
        return f"PrintStmt({self.values})"


class Block(ASTNode):
    def __init__(self, statements):
        self.statements = statements

    def __repr__(self):
        return f"Block({len(self.statements)} stmts)"


class Function(ASTNode):
    def __init__(self, return_type, name, params, body):
        self.return_type = return_type
        self.name = name
        self.params = params  # list of (type, name) tuples
        self.body = body

    def __repr__(self):
        return f"Function({self.return_type} {self.name}({self.params}))"


class Program(ASTNode):
    def __init__(self, functions):
        self.functions = functions

    def __repr__(self):
        return f"Program({len(self.functions)} functions)"
