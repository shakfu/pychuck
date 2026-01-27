"""
ChucK language support for numchuck.

This subpackage provides ChucK language constants and syntax highlighting:
- constants: Keywords, types, UGens, operators, and other language elements
- lexer: Pygments lexer for syntax highlighting
"""

from .constants import (
    ALL_BUILTINS,
    ALL_IDENTIFIERS,
    ALL_KEYWORDS,
    ALL_UGEN_PARAMS,
    CATEGORIES,
    KEYWORDS,
    MACHINE_METHODS,
    MATH_FUNCTIONS,
    OPERATORS,
    REPL_COMMANDS,
    STD_CLASSES,
    STD_FUNCTIONS,
    TIME_UNITS,
    TYPES,
    UGEN_PARAMS,
    UGENS,
    get_category,
    is_builtin,
    is_keyword,
    is_type,
    is_ugen,
)
from .lexer import ChuckLexer

__all__ = [
    # Constants
    "KEYWORDS",
    "TYPES",
    "OPERATORS",
    "TIME_UNITS",
    "UGENS",
    "UGEN_PARAMS",
    "ALL_UGEN_PARAMS",
    "MATH_FUNCTIONS",
    "STD_FUNCTIONS",
    "STD_CLASSES",
    "MACHINE_METHODS",
    "REPL_COMMANDS",
    "ALL_KEYWORDS",
    "ALL_BUILTINS",
    "ALL_IDENTIFIERS",
    "CATEGORIES",
    # Helper functions
    "is_keyword",
    "is_type",
    "is_ugen",
    "is_builtin",
    "get_category",
    # Lexer
    "ChuckLexer",
]
