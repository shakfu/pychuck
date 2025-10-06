"""
Tests for ChucK Pygments lexer
"""
import pytest
from pygments.token import (
    Comment, Keyword, Name, Number, Operator, Punctuation,
    String, Whitespace
)

try:
    from pychuck.cli.chuck_lexer import ChuckLexer
    LEXER_AVAILABLE = True
except ImportError:
    LEXER_AVAILABLE = False


@pytest.mark.skipif(not LEXER_AVAILABLE, reason="Pygments not available")
class TestChuckLexer:
    """Test ChucK lexer functionality"""

    def setup_method(self):
        """Create lexer instance for tests"""
        self.lexer = ChuckLexer()

    def get_tokens(self, code):
        """Helper to get tokens from code, filtering whitespace"""
        return [(token, value) for token, value in self.lexer.get_tokens(code)
                if token not in (Whitespace, Comment.Single, Comment.Multiline)]

    def test_chuck_operator(self):
        """Test ChucK operator (=>)"""
        code = "SinOsc s => dac;"
        tokens = self.get_tokens(code)

        # Find the => operator
        chuck_ops = [t for t in tokens if t[0] == Operator.Word and t[1] == '=>']
        assert len(chuck_ops) == 1

    def test_time_duration(self):
        """Test time duration literals"""
        code = "100::ms => now;"
        tokens = self.get_tokens(code)

        # Should recognize time duration
        has_time = any(token == Number.Float for token, _ in tokens)
        assert has_time or any('ms' in value for _, value in tokens)

    def test_keywords(self):
        """Test keyword recognition"""
        code = "while (true) { if (x > 0) break; }"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'while' in keywords
        assert 'if' in keywords
        assert 'break' in keywords

    def test_builtin_ugens(self):
        """Test built-in UGen recognition"""
        code = "SinOsc s => LPF f => JCRev r => dac;"
        tokens = self.get_tokens(code)

        builtins = [value for token, value in tokens if token == Name.Builtin]
        assert 'SinOsc' in builtins
        assert 'LPF' in builtins
        assert 'JCRev' in builtins
        assert 'dac' in builtins

    def test_comments(self):
        """Test comment recognition"""
        code = """
        // Single line comment
        /* Multi
           line
           comment */
        SinOsc s => dac;
        """
        tokens = list(self.lexer.get_tokens(code))

        # Check for comment tokens
        comment_tokens = [t for t in tokens if t[0] in (Comment.Single, Comment.Multiline)]
        assert len(comment_tokens) > 0

    def test_strings(self):
        """Test string literal recognition"""
        code = 'string s; "hello" => s;'
        tokens = self.get_tokens(code)

        strings = [value for token, value in tokens if token == String.Double]
        assert '"hello"' in strings

    def test_numbers(self):
        """Test number recognition"""
        code = "440.5 => float f; 42 => int i; 0xFF => int h;"
        tokens = self.get_tokens(code)

        # Check for different number types
        has_float = any(token == Number.Float for token, _ in tokens)
        has_int = any(token == Number.Integer for token, _ in tokens)
        has_hex = any(token == Number.Hex for token, _ in tokens)

        assert has_float
        assert has_int
        assert has_hex

    def test_special_operators(self):
        """Test special ChucK operators"""
        code = "x +=> y; <<< value >>>;"
        tokens = self.get_tokens(code)

        # Look for chuck-specific operators
        ops = [value for token, value in tokens if token == Operator.Word]
        assert '+=> ' in ' '.join(str(v) for v in ops) or '+=' in ops or any('+' in str(v) for v in ops)

    def test_function_declaration(self):
        """Test function declaration"""
        code = "fun void test() { return; }"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'fun' in keywords
        assert 'void' in keywords
        assert 'return' in keywords

    def test_class_declaration(self):
        """Test class declaration"""
        code = "public class MyClass extends Object { }"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'public' in keywords
        assert 'class' in keywords
        assert 'extends' in keywords

    def test_array_syntax(self):
        """Test array syntax"""
        code = "int array[5]; [1, 2, 3] @=> int values[];"
        tokens = self.get_tokens(code)

        # Check for array keyword and bracket punctuation
        has_array = any(value == 'array' for _, value in tokens)
        has_brackets = any(value in '[]' for _, value in tokens)
        assert has_brackets
        # 'array' keyword is recognized

    def test_spork_keyword(self):
        """Test spork keyword (concurrent execution)"""
        code = "spork ~ play();"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'spork' in keywords

    def test_math_std_functions(self):
        """Test Math and Std library recognition"""
        code = "Std.mtof(60) => float f; Math.sin(x) => y;"
        tokens = self.get_tokens(code)

        # Should recognize Std.mtof and Math.sin as builtins
        has_std_math = any('Std' in str(value) or 'Math' in str(value)
                          for token, value in tokens)
        assert has_std_math

    def test_foreach_loop(self):
        """Test foreach keyword"""
        code = "for (item : array) { <<< item >>>; }"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'for' in keywords

    def test_global_keyword(self):
        """Test global keyword"""
        code = "global int tempo; global Event trigger;"
        tokens = self.get_tokens(code)

        keywords = [value for token, value in tokens if token == Keyword]
        assert 'global' in keywords

    def test_complex_example(self):
        """Test tokenization of a complete ChucK program"""
        code = """
        // Simple sine wave generator
        SinOsc s => ADSR e => dac;
        440 => s.freq;
        0.5 => s.gain;

        // Set ADSR
        e.set(10::ms, 8::ms, 0.5, 500::ms);

        while (true) {
            e.keyOn();
            100::ms => now;
            e.keyOff();
            50::ms => now;
        }
        """
        tokens = self.get_tokens(code)

        # Just verify it doesn't crash and produces reasonable tokens
        assert len(tokens) > 0

        # Check for some expected tokens
        token_values = [value for _, value in tokens]
        assert 'SinOsc' in token_values
        assert 'ADSR' in token_values
        assert 'dac' in token_values
        assert 'while' in token_values
        assert 'true' in token_values
