"""
Lexer for the C++ subset.
Tokenizes source code into a stream of tokens using regex patterns.
"""

import re


class Token:
    """Represents a single token with type, value, and source line number."""

    def __init__(self, type, value, line):
        self.type = type
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class Lexer:
    """
    Tokenizes C++ source code into a list of Token objects.
    Skips comments, preprocessor directives, and whitespace.
    """

    KEYWORDS = {
        'int', 'float', 'double', 'bool', 'void',
        'if', 'else', 'while', 'for', 'return',
        'true', 'false',
        'cout', 'endl', 'cin',
        'using', 'namespace', 'std',
    }

    # Order matters: longer/more specific patterns first
    TOKEN_SPECS = [
        ('COMMENT_LINE',  r'//[^\n]*'),
        ('COMMENT_BLOCK', r'/\*[\s\S]*?\*/'),
        ('PREPROCESSOR',  r'#[^\n]*'),
        ('FLOAT_LIT',     r'\d+\.\d+'),
        ('INT_LIT',       r'\d+'),
        ('STRING_LIT',    r'"[^"]*"'),
        ('LSHIFT',        r'<<'),
        ('RSHIFT',        r'>>'),
        ('INC',           r'\+\+'),
        ('DEC',           r'--'),
        ('PLUS_EQ',       r'\+='),
        ('MINUS_EQ',      r'-='),
        ('STAR_EQ',       r'\*='),
        ('SLASH_EQ',      r'/='),
        ('LE',            r'<='),
        ('GE',            r'>='),
        ('EQEQ',          r'=='),
        ('NEQ',           r'!='),
        ('AND',           r'&&'),
        ('OR',            r'\|\|'),
        ('NOT',           r'!'),
        ('PLUS',          r'\+'),
        ('MINUS',         r'-'),
        ('STAR',          r'\*'),
        ('SLASH',         r'/'),
        ('MOD',           r'%'),
        ('EQ',            r'='),
        ('LT',            r'<'),
        ('GT',            r'>'),
        ('LPAREN',        r'\('),
        ('RPAREN',        r'\)'),
        ('LBRACE',        r'\{'),
        ('RBRACE',        r'\}'),
        ('SEMICOLON',     r';'),
        ('COMMA',         r','),
        ('IDENT',         r'[a-zA-Z_]\w*'),
        ('NEWLINE',       r'\n'),
        ('SKIP',          r'[ \t\r]+'),
        ('MISMATCH',      r'.'),
    ]

    def __init__(self, source):
        self.source = source
        self.tokens = []
        self._tokenize()

    def _tokenize(self):
        """Convert source code into a list of tokens."""
        token_regex = '|'.join(
            f'(?P<{name}>{pattern})' for name, pattern in self.TOKEN_SPECS
        )
        line_num = 1

        for match in re.finditer(token_regex, self.source):
            kind = match.lastgroup
            value = match.group()

            if kind == 'NEWLINE':
                line_num += 1
                continue
            elif kind == 'SKIP':
                continue
            elif kind in ('COMMENT_LINE', 'COMMENT_BLOCK', 'PREPROCESSOR'):
                line_num += value.count('\n')
                continue
            elif kind == 'MISMATCH':
                raise SyntaxError(
                    f"Unexpected character {value!r} at line {line_num}"
                )

            # Convert identifiers that are keywords to keyword tokens
            if kind == 'IDENT' and value in self.KEYWORDS:
                kind = value.upper()  # e.g. 'int' -> 'INT'

            self.tokens.append(Token(kind, value, line_num))

        # Sentinel EOF token
        self.tokens.append(Token('EOF', '', line_num))

    def get_tokens(self):
        """Return the list of tokens."""
        return self.tokens
