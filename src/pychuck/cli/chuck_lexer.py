"""
Pygments lexer for the ChucK audio programming language.

Uses chuck_lang module as the single source of truth for ChucK language elements.

See:
- https://chuck.stanford.edu/doc/language/
- https://pygments.org/docs/lexerdevelopment/
"""

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import (
    Comment, Keyword, Name, Number, Operator, Punctuation,
    String, Text, Whitespace
)
from ..chuck_lang import KEYWORDS, TYPES, UGENS, STD_CLASSES, TIME_UNITS

__all__ = ['ChuckLexer']


class ChuckLexer(RegexLexer):
    """
    Lexer for the ChucK audio programming language.

    ChucK is a strongly-typed, strongly-timed, concurrent audio
    and multimedia programming language.
    """

    name = 'ChucK'
    url = 'https://chuck.stanford.edu'
    aliases = ['chuck']
    filenames = ['*.ck']
    mimetypes = ['text/x-chuck']

    tokens = {
        'root': [
            # Whitespace
            (r'\s+', Whitespace),

            # Comments
            (r'//.*?$', Comment.Single),
            (r'/\*', Comment.Multiline, 'comment'),

            # Chuck operator (most distinctive feature)
            (r'=>', Operator.Word),
            (r'\+=>|\-=>|\*=>|/=>|%=>|&=>|\|=>|\^=>', Operator.Word),
            (r'@=>', Operator.Word),
            (r'<<=|>>=', Operator.Word),
            (r'\+\+|--', Operator),

            # Keywords (from chuck_lang module)
            (words(sorted(KEYWORDS | TYPES), suffix=r'\b'), Keyword),

            # Built-in UGens and classes (from chuck_lang module)
            (words(sorted(UGENS | STD_CLASSES), suffix=r'\b'), Name.Builtin),

            # Standard library functions (commonly used)
            (r'\b(Std|Math|Machine)\s*\.\s*[a-zA-Z_][a-zA-Z0-9_]*', Name.Builtin),

            # Time durations (very important in ChucK)
            # Build pattern dynamically from TIME_UNITS
            (r'\b\d+(\.\d+)?\s*::\s*(' + '|'.join(sorted(TIME_UNITS)) + r')\b', Number.Float),
            (r'::(' + '|'.join(sorted(TIME_UNITS)) + r')\b', Keyword.Type),

            # Special ChucK syntax
            (r'<<<', Operator),
            (r'>>>', Operator),
            (r'@\(', Punctuation),  # array literal prefix

            # Operators
            (r'[+\-*/%]', Operator),
            (r'[<>!=]=?', Operator),
            (r'&&|\|\|', Operator),
            (r'[&|^~]', Operator),
            (r'<<|>>', Operator),

            # Punctuation
            (r'[{}()\[\];,.]', Punctuation),
            (r'::', Punctuation),  # scope resolution

            # Numbers
            (r'0[xX][0-9a-fA-F]+', Number.Hex),
            (r'\d+\.\d+([eE][+-]?\d+)?', Number.Float),
            (r'\d+([eE][+-]?\d+)?', Number.Integer),

            # Strings
            (r'"([^"\\]|\\.)*"', String.Double),
            (r"'([^'\\]|\\.)*'", String.Single),

            # Identifiers
            (r'[a-zA-Z_][a-zA-Z0-9_]*', Name),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline),
        ],
    }
