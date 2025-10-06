"""
ChucK Language Constants

This module provides the single source of truth for ChucK language elements:
keywords, operators, built-in types, UGens, standard library, REPL commands, etc.

All components of pychuck that need to reference ChucK language elements should
import from this module to ensure consistency across:
- Syntax highlighting (chuck_lexer.py)
- REPL command completion (repl.py)
- Documentation generation
- Language validation

References:
- ChucK Language Specification: https://chuck.stanford.edu/doc/
- ChucK Source: https://github.com/ccrma/chuck
"""

# ChucK Keywords
KEYWORDS = {
    # Control flow
    'if', 'else', 'while', 'until', 'for', 'repeat', 'break', 'continue', 'return',

    # Object-oriented
    'class', 'extends', 'public', 'static', 'pure', 'this', 'super', 'interface',
    'implements', 'protected', 'private',

    # Function/operator
    'fun', 'function', 'spork', 'const', 'new',

    # Special
    'now', 'true', 'false', 'maybe', 'null', 'NULL', 'me', 'samp', 'ms', 'second',
    'minute', 'hour', 'day', 'week',

    # Advanced
    'foreach', 'chout', 'cherr', 'global', 'event', 'auto',
}

# ChucK Types
TYPES = {
    # Primitive types
    'int', 'float', 'time', 'dur', 'void', 'same',

    # Complex types
    'complex', 'polar',

    # Reference types
    'Object', 'array', 'Event', 'UGen', 'string',

    # Collections
    'Vec3', 'Vec4',
}

# ChucK Operators
OPERATORS = {
    # ChucK operator (the most important one!)
    '=>',

    # ChucK assignment operators
    '+=>', '-=>', '*=>', '/=>', '&=>', '|=>', '^=>',
    '>>=>', '<<=>', '%=>', '@=>',

    # Unchuck operator
    '=<', '+<=', '-<=', '*<=', '/<=', '&<=', '|<=', '^<=',
    '>>=<', '<<<=', '%<=', '@<=',

    # Comparison
    '==', '!=', '<', '<=', '>', '>=',

    # Logical
    '&&', '||', '!',

    # Arithmetic
    '+', '-', '*', '/', '%',

    # Bitwise
    '&', '|', '^', '~', '<<', '>>',

    # Increment/Decrement
    '++', '--',

    # Assignment
    '=',

    # Special
    '::', ':::', '$',
}

# Time/Duration Units
TIME_UNITS = {
    'samp', 'ms', 'second', 'minute', 'hour', 'day', 'week',
}

# Built-in UGens (Unit Generators)
UGENS = {
    # Basic oscillators
    'SinOsc', 'PulseOsc', 'SqrOsc', 'TriOsc', 'SawOsc', 'Phasor', 'Noise',

    # FM/Additive synthesis
    'Blit', 'BlitSaw', 'BlitSquare', 'GenX', 'Gen5', 'Gen7', 'Gen9', 'Gen10', 'Gen17',
    'CurveTable', 'WarpTable',

    # Filters
    'LPF', 'HPF', 'BPF', 'BRF', 'ResonZ', 'BiQuad', 'OnePole', 'TwoPole', 'OneZero',
    'TwoZero', 'PoleZero', 'Dyno',

    # Delay/Echo
    'Delay', 'DelayA', 'DelayL', 'Echo',

    # Reverb
    'JCRev', 'NRev', 'PRCRev',

    # Dynamics
    'Gain', 'Envelope', 'ADSR', 'Dyno', 'LiSa',

    # STK Instruments
    'Mandolin', 'Saxofony', 'Flute', 'BowTable', 'Bowed', 'Brass', 'Clarinet', 'BlowHole',
    'Wurley', 'Rhodey', 'TubeBell', 'HevyMetl', 'PercFlut', 'BeeThree', 'FMVoices',
    'VoicForm', 'Moog', 'Shakers', 'ModalBar', 'Sitar', 'StifKarp', 'Drummer',

    # Special/IO
    'dac', 'adc', 'blackhole',  # Special global audio endpoints
    'DAC', 'ADC', 'Chubgraph', 'Chugen', 'Pan2', 'Mix2', 'SndBuf', 'SndBuf2', 'Dyno',
    'HalfRect', 'FullRect', 'ZeroX', 'Flip', 'SubNoise', 'Impulse', 'Step',

    # Chugins (commonly available)
    'ABSaturator', 'AmbPan', 'Bitcrusher', 'Elliptic', 'ExpDelay', 'ExpEnv',
    'FIR', 'Faust', 'FoldbackSaturator', 'GVerb', 'KasFilter', 'MagicSine',
    'Mesh2D', 'Multicomb', 'NHHall', 'PanN', 'Perlin', 'PitchTrack', 'PowerADSR',
    'Random', 'RegEx', 'Sigmund', 'Spectacle', 'WinFuncEnv', 'WPDiodeLadder',
    'WPKorg35', 'Wavetable',
}

# Standard Library - Math
MATH_FUNCTIONS = {
    'abs', 'fabs', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
    'sinh', 'cosh', 'tanh', 'hypot', 'pow', 'sqrt', 'exp', 'log', 'log2',
    'log10', 'floor', 'ceil', 'round', 'trunc', 'fmod', 'remainder',
    'min', 'max', 'nextpow2', 'isinf', 'isnan',
    'pi', 'twopi', 'e', 'i',  # Constants
}

# Standard Library - Std
STD_FUNCTIONS = {
    'abs', 'fabs', 'rand', 'rand2', 'randf', 'rand2f', 'randSeed',
    'sgn', 'system', 'atoi', 'atof', 'itoa', 'ftoa', 'ftoi',
    'getenv', 'setenv', 'mtof', 'ftom', 'powtodb', 'rmstodb', 'dbtopow', 'dbtorms',
    'clamp', 'clampf', 'scale', 'scalef',
}

# Standard Library Classes
STD_CLASSES = {
    # Core classes
    'Object', 'Event', 'Shred', 'RegEx', 'String',

    # Math classes
    'Math', 'Complex', 'Polar',

    # Standard library
    'Std', 'Machine', 'ConsoleInput',

    # Collections
    'Array', 'AssocArray',

    # File I/O
    'FileIO', 'StdIn', 'StdOut', 'StdErr',

    # MIDI
    'MidiIn', 'MidiOut', 'MidiMsg', 'MidiFileIn',

    # OSC
    'OscIn', 'OscOut', 'OscMsg', 'OscSend', 'OscRecv', 'OscEvent',

    # Serial
    'SerialIO',

    # HID
    'Hid', 'HidMsg',
}

# Machine/Shred Management
MACHINE_METHODS = {
    'add', 'spork', 'remove', 'replace', 'status', 'crash',
}

# REPL Commands (pychuck-specific)
REPL_COMMANDS = {
    # Shred management
    '+', '-', '~', '?',

    # Info
    '?g', '?a', '.',

    # Audio control
    '>', '||', 'X',

    # VM control
    'clear', 'reset',

    # Screen
    'cls',

    # Special
    ':', '!', '$', '@', 'edit', 'watch', 'help', 'quit', 'exit',
}

# All identifiers (for completions)
ALL_KEYWORDS = KEYWORDS | TYPES | TIME_UNITS
ALL_BUILTINS = UGENS | STD_CLASSES | MATH_FUNCTIONS | STD_FUNCTIONS
ALL_IDENTIFIERS = ALL_KEYWORDS | ALL_BUILTINS

# Grouped by category for documentation
CATEGORIES = {
    'keywords': KEYWORDS,
    'types': TYPES,
    'operators': OPERATORS,
    'time_units': TIME_UNITS,
    'ugens': UGENS,
    'math': MATH_FUNCTIONS,
    'std': STD_FUNCTIONS,
    'classes': STD_CLASSES,
}

# Helper functions
def is_keyword(name: str) -> bool:
    """Check if a name is a ChucK keyword"""
    return name in KEYWORDS

def is_type(name: str) -> bool:
    """Check if a name is a ChucK type"""
    return name in TYPES

def is_ugen(name: str) -> bool:
    """Check if a name is a UGen"""
    return name in UGENS

def is_builtin(name: str) -> bool:
    """Check if a name is a built-in (UGen, class, or function)"""
    return name in ALL_BUILTINS

def get_category(name: str) -> str:
    """Get the category of a ChucK identifier"""
    for category, names in CATEGORIES.items():
        if name in names:
            return category
    return 'unknown'
