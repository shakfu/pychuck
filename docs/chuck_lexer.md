# ChucK Pygments Lexer

pychuck includes a custom Pygments lexer for ChucK syntax highlighting in the REPL.

## Features

The ChucK lexer provides syntax highlighting for:

- **Keywords**: `if`, `else`, `while`, `for`, `repeat`, `break`, `continue`, `return`, `class`, `fun`, `spork`, etc.
- **ChucK Operators**: `=>`, `+=>`, `-=>`, `*=>`, `/=>`, `@=>`, `<<`, `>>`, `<<<`, `>>>`
- **Built-in Types**: `int`, `float`, `time`, `dur`, `string`, `Event`, `UGen`, `UAna`, etc.
- **Time Durations**: `100::ms`, `1::second`, `500::samp`, etc.
- **Built-in UGens**: `SinOsc`, `LPF`, `ADSR`, `JCRev`, `dac`, `adc`, etc.
- **Standard Library**: `Math`, `Std`, `Machine`, etc.
- **Comments**: Single-line (`//`) and multi-line (`/* */`)
- **Strings and Numbers**: Including hex literals, floats, and integers

## Usage

### In the REPL

The lexer is automatically used in the pychuck REPL when both `prompt_toolkit` and `pygments` are installed:

```bash
python -m pychuck tui
```

If Pygments is not available, the REPL falls back to a C lexer for basic syntax highlighting.

### Programmatically

You can use the ChucK lexer directly with Pygments:

```python
from pygments import highlight
from pygments.formatters import TerminalFormatter
from pychuck.cli.chuck_lexer import ChuckLexer

code = '''
SinOsc s => dac;
440 => s.freq;
while (true) {
    100::ms => now;
}
'''

lexer = ChuckLexer()
formatter = TerminalFormatter()
result = highlight(code, lexer, formatter)
print(result)
```

### With HTML Output

```python
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pychuck.cli.chuck_lexer import ChuckLexer

code = 'SinOsc s => dac; 440 => s.freq;'
lexer = ChuckLexer()
formatter = HtmlFormatter()
html = highlight(code, lexer, formatter)
```

## Lexer Details

- **Name**: ChucK
- **Aliases**: `chuck`
- **File patterns**: `*.ck`
- **MIME types**: `text/x-chuck`

## Testing

The lexer includes comprehensive tests in `tests/test_chuck_lexer.py`:

```bash
pytest tests/test_chuck_lexer.py -v
```

Tests cover:

- ChucK operators (`=>`, `+=>`, etc.)
- Time durations (`100::ms`)
- Keywords and built-in types
- UGen recognition
- Comments and strings
- Numbers (int, float, hex)
- Special operators (`<<<`, `>>>`, `@=>`)
- Function and class declarations
- Array syntax
- Standard library functions
- Complete program examples

## ChucK Language Reference

For more information on ChucK syntax, see:

- [ChucK Language Specification](https://chuck.stanford.edu/doc/language/)
- [ChucK Reference](https://chuck.stanford.edu/doc/reference/)

## Implementation Notes

The lexer is implemented as a `RegexLexer` subclass, following Pygments best practices:

- Token types from `pygments.token`
- Regex-based pattern matching
- Support for nested comments
- Special handling for ChucK-specific syntax (time durations, chuck operators)

## Contributing

To add or improve syntax highlighting:

1. Update patterns in `src/pychuck/cli/chuck_lexer.py`
2. Add test cases in `tests/test_chuck_lexer.py`
3. Test with `pytest tests/test_chuck_lexer.py`
4. Verify in REPL: `python -m pychuck tui`

Common additions:

- New UGens or standard library classes
- Additional keywords from ChucK updates
- Improved token classification for edge cases
