"""
Pygments lexer for the ChucK audio programming language.

See:
- https://chuck.stanford.edu/doc/language/
- https://pygments.org/docs/lexerdevelopment/
"""

from pygments.lexer import RegexLexer, bygroups, words
from pygments.token import (
    Comment, Keyword, Name, Number, Operator, Punctuation,
    String, Text, Whitespace
)

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

            # Keywords
            (words((
                # Control flow
                'if', 'else', 'while', 'until', 'for', 'repeat', 'break', 'continue',
                'return', 'switch', 'case', 'default',
                # Special keywords
                'now', 'me', 'this', 'super', 'null', 'NULL',
                # Class/Function keywords
                'class', 'extends', 'public', 'static', 'pure', 'const',
                'function', 'fun', 'spork', 'new',
                # Types
                'int', 'float', 'time', 'dur', 'void', 'same',
                'string', 'Object', 'array', 'Event', 'UGen', 'UAna',
                'complex', 'polar', 'vec3', 'vec4',
                # Other
                'global', 'extern',
            ), suffix=r'\b'), Keyword),

            # Special time keywords (foreach is special syntax)
            (r'\bforeach\b', Keyword),

            # Boolean literals
            (words(('true', 'false'), suffix=r'\b'), Keyword.Constant),

            # Built-in types (common UGens and classes)
            (words((
                # Oscillators
                'SinOsc', 'PulseOsc', 'SqrOsc', 'TriOsc', 'SawOsc', 'Phasor',
                'Blit', 'BlitSaw', 'BlitSquare',
                # Filters
                'LPF', 'HPF', 'BPF', 'BRF', 'ResonZ', 'BiQuad', 'OnePole', 'TwoPole',
                'OneZero', 'TwoZero', 'PoleZero',
                # Effects
                'JCRev', 'NRev', 'PRCRev', 'Chorus', 'Modulate', 'PitShift',
                'SubNoise', 'Dyno', 'LimitGain', 'Gain', 'Pan2',
                # Envelopes
                'ADSR', 'Envelope', 'Step', 'Impulse',
                # Delay
                'Delay', 'DelayL', 'DelayA', 'Echo',
                # Noise
                'Noise', 'CNoise',
                # I/O
                'dac', 'adc', 'blackhole',
                # Files
                'SndBuf', 'SndBuf2', 'WvIn', 'WvIn2', 'WvOut', 'WvOut2',
                # STK instruments
                'Mandolin', 'Saxofony', 'StifKarp', 'Sitar', 'BandedWG', 'BlowBotl',
                'BlowHole', 'Bowed', 'Brass', 'Clarinet', 'Flute', 'Moog', 'Rhodey',
                'Shakers', 'VoicForm', 'FM', 'BeeThree', 'FMVoices', 'HevyMetl',
                'PercFlut', 'TubeBell', 'Wurley',
                # Standard library
                'Math', 'Std', 'Machine', 'StringTokenizer', 'ConsoleInput',
                'FileIO', 'SerialIO', 'HidIn', 'HidOut', 'KBHit',
                # MIDI
                'MidiIn', 'MidiOut', 'MidiMsg', 'MidiFileIn',
                # OSC
                'OscIn', 'OscOut', 'OscMsg', 'OscSend', 'OscRecv', 'OscEvent',
                # Analysis
                'FFT', 'IFFT', 'DCT', 'IDCT', 'Windowing', 'Flip',
                'pilF', 'AutoCorr', 'XCorr', 'Centroid', 'Flux', 'RMS', 'RollOff',
                'FeatureCollector', 'Chroma',
                # Other
                'StkInstrument', 'WarpBuf', 'GenX', 'CurveTable', 'WinFuncEnv',
            ), suffix=r'\b'), Name.Builtin),

            # Standard library functions (commonly used)
            (r'\b(Std|Math|Machine)\s*\.\s*[a-zA-Z_][a-zA-Z0-9_]*', Name.Builtin),

            # Time durations (very important in ChucK)
            (r'\b\d+(\.\d+)?\s*::\s*(samp|ms|second|minute|hour|day|week)\b', Number.Float),
            (r'::(samp|ms|second|minute|hour|day|week)\b', Keyword.Type),

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
