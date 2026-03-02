"""
Recursive Descent Parser for the C++ subset.
Converts a token stream into an Abstract Syntax Tree (AST).
Handles operator precedence via separate parsing levels.
"""

from ast_nodes import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ─── Token Helpers ───────────────────────────────────────────────────

    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def consume(self, expected=None):
        tok = self.current()
        if expected and tok.type != expected:
            raise SyntaxError(
                f"Expected {expected}, got {tok.type} ({tok.value!r}) "
                f"at line {tok.line}"
            )
        self.pos += 1
        return tok

    def match(self, *types):
        if self.current().type in types:
            return self.consume()
        return None

    # ─── Top Level ───────────────────────────────────────────────────────

    def parse(self):
        """Parse the entire program: skip 'using' decls, parse functions."""
        functions = []
        while self.current().type != 'EOF':
            # Skip 'using namespace std;'
            if self.current().type == 'USING':
                while self.current().type != 'SEMICOLON':
                    self.consume()
                self.consume('SEMICOLON')
                continue
            functions.append(self.parse_function())
        return Program(functions)

    def parse_function(self):
        ret_type = self.consume().value        # return type (int, void, etc.)
        name = self.consume('IDENT').value      # function name
        self.consume('LPAREN')
        params = self.parse_params()
        self.consume('RPAREN')
        body = self.parse_block()
        return Function(ret_type, name, params, body)

    def parse_params(self):
        params = []
        if self.current().type != 'RPAREN':
            ptype = self.consume().value
            pname = self.consume('IDENT').value
            params.append((ptype, pname))
            while self.match('COMMA'):
                ptype = self.consume().value
                pname = self.consume('IDENT').value
                params.append((ptype, pname))
        return params

    def parse_block(self):
        self.consume('LBRACE')
        stmts = []
        while self.current().type != 'RBRACE':
            stmts.append(self.parse_statement())
        self.consume('RBRACE')
        return Block(stmts)

    # ─── Statements ──────────────────────────────────────────────────────

    def parse_statement(self):
        tok = self.current()

        if tok.type in ('INT', 'FLOAT', 'DOUBLE', 'BOOL', 'VOID'):
            return self.parse_var_decl()
        elif tok.type == 'IF':
            return self.parse_if()
        elif tok.type == 'WHILE':
            return self.parse_while()
        elif tok.type == 'FOR':
            return self.parse_for()
        elif tok.type == 'RETURN':
            return self.parse_return()
        elif tok.type == 'COUT':
            return self.parse_print()
        elif tok.type == 'IDENT':
            next_tok = self.peek()
            if next_tok.type in ('EQ', 'PLUS_EQ', 'MINUS_EQ', 'STAR_EQ', 'SLASH_EQ'):
                return self.parse_assignment()
            else:
                # Expression statement (e.g., function call, i++)
                expr = self.parse_expression()
                self.consume('SEMICOLON')
                return expr
        else:
            raise SyntaxError(
                f"Unexpected token {tok.type} ({tok.value!r}) at line {tok.line}"
            )

    def parse_var_decl(self):
        var_type = self.consume().value
        name = self.consume('IDENT').value
        init = None
        if self.match('EQ'):
            init = self.parse_expression()
        self.consume('SEMICOLON')
        return VarDecl(var_type, name, init)

    def parse_assignment(self):
        name = self.consume('IDENT').value
        op_tok = self.consume()           # =, +=, -=, *=, /=
        value = self.parse_expression()
        self.consume('SEMICOLON')
        return Assignment(name, value, op_tok.value)

    def parse_if(self):
        self.consume('IF')
        self.consume('LPAREN')
        condition = self.parse_expression()
        self.consume('RPAREN')
        then_body = self.parse_block()
        else_body = None
        if self.match('ELSE'):
            if self.current().type == 'IF':
                else_body = Block([self.parse_if()])
            else:
                else_body = self.parse_block()
        return IfStmt(condition, then_body, else_body)

    def parse_while(self):
        self.consume('WHILE')
        self.consume('LPAREN')
        condition = self.parse_expression()
        self.consume('RPAREN')
        body = self.parse_block()
        return WhileStmt(condition, body)

    def parse_for(self):
        self.consume('FOR')
        self.consume('LPAREN')

        # Init part
        init = None
        if self.current().type in ('INT', 'FLOAT', 'DOUBLE', 'BOOL'):
            var_type = self.consume().value
            name = self.consume('IDENT').value
            init_val = None
            if self.match('EQ'):
                init_val = self.parse_expression()
            self.consume('SEMICOLON')
            init = VarDecl(var_type, name, init_val)
        elif self.current().type == 'IDENT':
            name = self.consume('IDENT').value
            op_tok = self.consume()
            value = self.parse_expression()
            self.consume('SEMICOLON')
            init = Assignment(name, value, op_tok.value)
        else:
            self.consume('SEMICOLON')

        # Condition part
        condition = None
        if self.current().type != 'SEMICOLON':
            condition = self.parse_expression()
        self.consume('SEMICOLON')

        # Update part
        update = None
        if self.current().type != 'RPAREN':
            if (self.current().type == 'IDENT' and
                    self.peek().type in ('EQ', 'PLUS_EQ', 'MINUS_EQ', 'STAR_EQ', 'SLASH_EQ')):
                name = self.consume('IDENT').value
                op_tok = self.consume()
                value = self.parse_expression()
                update = Assignment(name, value, op_tok.value)
            else:
                update = self.parse_expression()
        self.consume('RPAREN')

        body = self.parse_block()
        return ForStmt(init, condition, update, body)

    def parse_return(self):
        self.consume('RETURN')
        value = None
        if self.current().type != 'SEMICOLON':
            value = self.parse_expression()
        self.consume('SEMICOLON')
        return ReturnStmt(value)

    def parse_print(self):
        self.consume('COUT')
        values = []
        while self.match('LSHIFT'):
            if self.current().type == 'ENDL':
                self.consume('ENDL')
                continue
            values.append(self.parse_expression())
        self.consume('SEMICOLON')
        return PrintStmt(values)

    # ─── Expressions (precedence levels, lowest to highest) ──────────────

    def parse_expression(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.current().type == 'OR':
            op = self.consume().value
            right = self.parse_and()
            left = BinaryExpr(op, left, right)
        return left

    def parse_and(self):
        left = self.parse_equality()
        while self.current().type == 'AND':
            op = self.consume().value
            right = self.parse_equality()
            left = BinaryExpr(op, left, right)
        return left

    def parse_equality(self):
        left = self.parse_comparison()
        while self.current().type in ('EQEQ', 'NEQ'):
            op = self.consume().value
            right = self.parse_comparison()
            left = BinaryExpr(op, left, right)
        return left

    def parse_comparison(self):
        left = self.parse_additive()
        while self.current().type in ('LT', 'GT', 'LE', 'GE'):
            op = self.consume().value
            right = self.parse_additive()
            left = BinaryExpr(op, left, right)
        return left

    def parse_additive(self):
        left = self.parse_multiplicative()
        while self.current().type in ('PLUS', 'MINUS'):
            op = self.consume().value
            right = self.parse_multiplicative()
            left = BinaryExpr(op, left, right)
        return left

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.current().type in ('STAR', 'SLASH', 'MOD'):
            op = self.consume().value
            right = self.parse_unary()
            left = BinaryExpr(op, left, right)
        return left

    def parse_unary(self):
        if self.current().type == 'NOT':
            op = self.consume().value
            operand = self.parse_unary()
            return UnaryExpr(op, operand)
        elif self.current().type == 'MINUS':
            op = self.consume().value
            operand = self.parse_unary()
            return UnaryExpr(op, operand)
        elif self.current().type == 'INC':
            self.consume()
            operand = self.parse_primary()
            return UnaryExpr('++', operand)
        elif self.current().type == 'DEC':
            self.consume()
            operand = self.parse_primary()
            return UnaryExpr('--', operand)
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        if self.current().type == 'INC':
            self.consume()
            return UnaryExpr('++', expr, prefix=False)
        elif self.current().type == 'DEC':
            self.consume()
            return UnaryExpr('--', expr, prefix=False)
        return expr

    def parse_primary(self):
        tok = self.current()

        if tok.type == 'INT_LIT':
            self.consume()
            return Number(int(tok.value))
        elif tok.type == 'FLOAT_LIT':
            self.consume()
            return Number(float(tok.value))
        elif tok.type in ('TRUE', 'FALSE'):
            self.consume()
            return BoolLiteral(tok.value == 'true')
        elif tok.type == 'IDENT':
            name = self.consume().value
            # Check for function call
            if self.current().type == 'LPAREN':
                self.consume('LPAREN')
                args = []
                if self.current().type != 'RPAREN':
                    args.append(self.parse_expression())
                    while self.match('COMMA'):
                        args.append(self.parse_expression())
                self.consume('RPAREN')
                return FunctionCall(name, args)
            return Identifier(name)
        elif tok.type == 'LPAREN':
            self.consume('LPAREN')
            expr = self.parse_expression()
            self.consume('RPAREN')
            return expr
        else:
            raise SyntaxError(
                f"Unexpected token in expression: {tok.type} ({tok.value!r}) "
                f"at line {tok.line}"
            )
