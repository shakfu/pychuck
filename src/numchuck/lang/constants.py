"""
ChucK Language Constants

This module provides the single source of truth for ChucK language elements:
keywords, operators, built-in types, UGens, standard library, REPL commands, etc.

All components of numchuck that need to reference ChucK language elements should
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
    "if",
    "else",
    "while",
    "until",
    "for",
    "repeat",
    "break",
    "continue",
    "return",
    # Object-oriented
    "class",
    "extends",
    "public",
    "static",
    "pure",
    "this",
    "super",
    "interface",
    "implements",
    "protected",
    "private",
    # Function/operator
    "fun",
    "function",
    "spork",
    "const",
    "new",
    # Special
    "now",
    "true",
    "false",
    "maybe",
    "null",
    "NULL",
    "me",
    "samp",
    "ms",
    "second",
    "minute",
    "hour",
    "day",
    "week",
    # Advanced
    "foreach",
    "chout",
    "cherr",
    "global",
    "event",
    "auto",
}

# ChucK Types
TYPES = {
    # Primitive types
    "int",
    "float",
    "time",
    "dur",
    "void",
    "same",
    # Complex types
    "complex",
    "polar",
    # Reference types
    "Object",
    "array",
    "Event",
    "UGen",
    "string",
    # Collections
    "Vec3",
    "Vec4",
}

# ChucK Operators
OPERATORS = {
    # ChucK operator (the most important one!)
    "=>",
    # ChucK assignment operators
    "+=>",
    "-=>",
    "*=>",
    "/=>",
    "&=>",
    "|=>",
    "^=>",
    ">>=>",
    "<<=>",
    "%=>",
    "@=>",
    # Unchuck operator
    "=<",
    "+<=",
    "-<=",
    "*<=",
    "/<=",
    "&<=",
    "|<=",
    "^<=",
    ">>=<",
    "<<<=",
    "%<=",
    "@<=",
    # Comparison
    "==",
    "!=",
    "<",
    "<=",
    ">",
    ">=",
    # Logical
    "&&",
    "||",
    "!",
    # Arithmetic
    "+",
    "-",
    "*",
    "/",
    "%",
    # Bitwise
    "&",
    "|",
    "^",
    "~",
    "<<",
    ">>",
    # Increment/Decrement
    "++",
    "--",
    # Assignment
    "=",
    # Special
    "::",
    ":::",
    "$",
}

# Time/Duration Units
TIME_UNITS = {
    "samp",
    "ms",
    "second",
    "minute",
    "hour",
    "day",
    "week",
}

# Built-in UGens (Unit Generators)
UGENS = {
    # Basic oscillators
    "SinOsc",
    "PulseOsc",
    "SqrOsc",
    "TriOsc",
    "SawOsc",
    "Phasor",
    "Noise",
    # FM/Additive synthesis
    "Blit",
    "BlitSaw",
    "BlitSquare",
    "GenX",
    "Gen5",
    "Gen7",
    "Gen9",
    "Gen10",
    "Gen17",
    "CurveTable",
    "WarpTable",
    # Filters
    "LPF",
    "HPF",
    "BPF",
    "BRF",
    "ResonZ",
    "BiQuad",
    "OnePole",
    "TwoPole",
    "OneZero",
    "TwoZero",
    "PoleZero",
    "Dyno",
    # Delay/Echo
    "Delay",
    "DelayA",
    "DelayL",
    "Echo",
    # Reverb
    "JCRev",
    "NRev",
    "PRCRev",
    # Dynamics
    "Gain",
    "Envelope",
    "ADSR",
    "Dyno",
    "LiSa",
    # STK Instruments
    "Mandolin",
    "Saxofony",
    "Flute",
    "BowTable",
    "Bowed",
    "Brass",
    "Clarinet",
    "BlowHole",
    "Wurley",
    "Rhodey",
    "TubeBell",
    "HevyMetl",
    "PercFlut",
    "BeeThree",
    "FMVoices",
    "VoicForm",
    "Moog",
    "Shakers",
    "ModalBar",
    "Sitar",
    "StifKarp",
    "Drummer",
    # Special/IO
    "dac",
    "adc",
    "blackhole",  # Special global audio endpoints
    "DAC",
    "ADC",
    "Chubgraph",
    "Chugen",
    "Pan2",
    "Mix2",
    "SndBuf",
    "SndBuf2",
    "Dyno",
    "HalfRect",
    "FullRect",
    "ZeroX",
    "Flip",
    "SubNoise",
    "Impulse",
    "Step",
    # Chugins (commonly available)
    "ABSaturator",
    "AmbPan",
    "Bitcrusher",
    "Elliptic",
    "ExpDelay",
    "ExpEnv",
    "FIR",
    "Faust",
    "FoldbackSaturator",
    "GVerb",
    "KasFilter",
    "MagicSine",
    "Mesh2D",
    "Multicomb",
    "NHHall",
    "PanN",
    "Perlin",
    "PitchTrack",
    "PowerADSR",
    "Random",
    "RegEx",
    "Sigmund",
    "Spectacle",
    "WinFuncEnv",
    "WPDiodeLadder",
    "WPKorg35",
    "Wavetable",
}

# Standard Library - Math
MATH_FUNCTIONS = {
    "abs",
    "fabs",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "atan2",
    "sinh",
    "cosh",
    "tanh",
    "hypot",
    "pow",
    "sqrt",
    "exp",
    "log",
    "log2",
    "log10",
    "floor",
    "ceil",
    "round",
    "trunc",
    "fmod",
    "remainder",
    "min",
    "max",
    "nextpow2",
    "isinf",
    "isnan",
    "pi",
    "twopi",
    "e",
    "i",  # Constants
}

# Standard Library - Std
STD_FUNCTIONS = {
    "abs",
    "fabs",
    "rand",
    "rand2",
    "randf",
    "rand2f",
    "randSeed",
    "sgn",
    "system",
    "atoi",
    "atof",
    "itoa",
    "ftoa",
    "ftoi",
    "getenv",
    "setenv",
    "mtof",
    "ftom",
    "powtodb",
    "rmstodb",
    "dbtopow",
    "dbtorms",
    "clamp",
    "clampf",
    "scale",
    "scalef",
}

# Standard Library Classes
STD_CLASSES = {
    # Core classes
    "Object",
    "Event",
    "Shred",
    "RegEx",
    "String",
    # Math classes
    "Math",
    "Complex",
    "Polar",
    # Standard library
    "Std",
    "Machine",
    "ConsoleInput",
    # Collections
    "Array",
    "AssocArray",
    # File I/O
    "FileIO",
    "StdIn",
    "StdOut",
    "StdErr",
    # MIDI
    "MidiIn",
    "MidiOut",
    "MidiMsg",
    "MidiFileIn",
    # OSC
    "OscIn",
    "OscOut",
    "OscMsg",
    "OscSend",
    "OscRecv",
    "OscEvent",
    # Serial
    "SerialIO",
    # HID
    "Hid",
    "HidMsg",
}

# Machine/Shred Management
MACHINE_METHODS = {
    "add",
    "spork",
    "remove",
    "replace",
    "status",
    "crash",
}

# REPL Commands (numchuck-specific)
REPL_COMMANDS = {
    # Shred management
    "+",
    "-",
    "~",
    "?",
    # Info
    "?g",
    "?a",
    ".",
    # Audio control
    ">",
    "||",
    "X",
    # VM control
    "clear",
    "reset",
    # Screen
    "cls",
    # Special
    ":",
    "!",
    "$",
    "@",
    "edit",
    "watch",
    "help",
    "quit",
    "exit",
}

# UGen parameters by category
# Common parameters shared by most UGens
UGEN_PARAMS_COMMON = {"gain", "last", "op", "channels", "chan"}

# Oscillator parameters
UGEN_PARAMS_OSC = {"freq", "phase", "sync", "width"}

# Filter parameters
UGEN_PARAMS_FILTER = {"freq", "Q", "set"}

# Envelope parameters
UGEN_PARAMS_ENV = {
    "attackTime",
    "decayTime",
    "sustainLevel",
    "releaseTime",
    "attackRate",
    "decayRate",
    "releaseRate",
    "target",
    "value",
    "duration",
    "keyOn",
    "keyOff",
}

# Delay parameters
UGEN_PARAMS_DELAY = {"delay", "max"}

# Buffer parameters (SndBuf)
UGEN_PARAMS_BUFFER = {
    "read",
    "write",
    "samples",
    "frames",
    "length",
    "channels",
    "rate",
    "pos",
    "loop",
    "interp",
    "valueAt",
}

# LiSa parameters
UGEN_PARAMS_LISA = {
    "duration",
    "maxVoices",
    "record",
    "play",
    "loop",
    "loopStart",
    "loopEnd",
    "loopEndRec",
    "recPos",
    "playPos",
    "rate",
    "voiceRate",
    "rampUp",
    "rampDown",
    "bi",
    "voice",
    "track",
    "feedback",
    "clear",
    "getVoice",
}

# Pan2 parameters
UGEN_PARAMS_PAN = {"pan"}

# STK instrument parameters
UGEN_PARAMS_STK = {
    "freq",
    "noteOn",
    "noteOff",
    "pluck",
    "startBowing",
    "stopBowing",
    "bowPressure",
    "bowPosition",
    "vibratoFreq",
    "vibratoGain",
    "controlChange",
    "afterTouch",
    "volume",
    "clear",
}

# UGen-specific parameter mappings
UGEN_PARAMS: dict[str, set[str]] = {
    # Oscillators
    "SinOsc": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "PulseOsc": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "SqrOsc": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "TriOsc": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "SawOsc": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "Phasor": UGEN_PARAMS_COMMON | UGEN_PARAMS_OSC,
    "Noise": UGEN_PARAMS_COMMON,
    "Impulse": UGEN_PARAMS_COMMON | {"next"},
    "Step": UGEN_PARAMS_COMMON | {"next", "value"},
    # Filters
    "LPF": UGEN_PARAMS_COMMON | UGEN_PARAMS_FILTER,
    "HPF": UGEN_PARAMS_COMMON | UGEN_PARAMS_FILTER,
    "BPF": UGEN_PARAMS_COMMON | UGEN_PARAMS_FILTER,
    "BRF": UGEN_PARAMS_COMMON | UGEN_PARAMS_FILTER,
    "ResonZ": UGEN_PARAMS_COMMON | UGEN_PARAMS_FILTER,
    "BiQuad": UGEN_PARAMS_COMMON | {"pfreq", "prad", "zfreq", "zrad", "norm", "eqzs"},
    "OnePole": UGEN_PARAMS_COMMON | {"a1", "b0", "pole"},
    "TwoPole": UGEN_PARAMS_COMMON | {"a1", "a2", "b0", "freq", "radius", "norm"},
    "OneZero": UGEN_PARAMS_COMMON | {"a1", "b0", "b1", "zero"},
    "TwoZero": UGEN_PARAMS_COMMON | {"a0", "a1", "a2", "freq", "radius"},
    "PoleZero": UGEN_PARAMS_COMMON | {"a1", "b0", "b1", "allpass", "blockZero"},
    # Envelopes
    "Envelope": UGEN_PARAMS_COMMON | UGEN_PARAMS_ENV,
    "ADSR": UGEN_PARAMS_COMMON | UGEN_PARAMS_ENV | {"set", "state"},
    # Delays
    "Delay": UGEN_PARAMS_COMMON | UGEN_PARAMS_DELAY,
    "DelayA": UGEN_PARAMS_COMMON | UGEN_PARAMS_DELAY,
    "DelayL": UGEN_PARAMS_COMMON | UGEN_PARAMS_DELAY,
    "Echo": UGEN_PARAMS_COMMON | UGEN_PARAMS_DELAY | {"mix"},
    # Reverbs
    "JCRev": UGEN_PARAMS_COMMON | {"mix"},
    "NRev": UGEN_PARAMS_COMMON | {"mix"},
    "PRCRev": UGEN_PARAMS_COMMON | {"mix"},
    # Dynamics
    "Gain": UGEN_PARAMS_COMMON,
    "Dyno": UGEN_PARAMS_COMMON
    | {
        "thresh",
        "attack",
        "release",
        "ratio",
        "slopeBelow",
        "slopeAbove",
        "externalSideInput",
        "sideInput",
        "limit",
        "compress",
        "gate",
        "expand",
        "duck",
    },
    # Buffer/Sampling
    "SndBuf": UGEN_PARAMS_COMMON | UGEN_PARAMS_BUFFER,
    "SndBuf2": UGEN_PARAMS_COMMON | UGEN_PARAMS_BUFFER,
    "LiSa": UGEN_PARAMS_COMMON | UGEN_PARAMS_LISA,
    # Panning/Mixing
    "Pan2": UGEN_PARAMS_COMMON | UGEN_PARAMS_PAN,
    "Mix2": UGEN_PARAMS_COMMON | UGEN_PARAMS_PAN,
    # STK Instruments (shared params)
    "Mandolin": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"bodySize", "pluckPos", "stringDamping", "stringDetune"},
    "Bowed": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK,
    "Brass": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"lip"},
    "Clarinet": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"reed", "noiseGain"},
    "Flute": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"jetDelay", "jetReflection", "endReflection"},
    "Saxofony": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"stiffness", "aperture", "noiseGain", "pressure"},
    "Wurley": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK,
    "Rhodey": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK,
    "Moog": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"filterQ", "filterSweepRate", "lfoSpeed", "lfoDepth"},
    "ModalBar": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"preset", "stickHardness", "strikePosition", "directGain", "masterGain"},
    "Shakers": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"preset", "energy", "decay", "objects"},
    "StifKarp": UGEN_PARAMS_COMMON | UGEN_PARAMS_STK | {"pickupPosition", "sustain", "stretch"},
    # Special
    "dac": UGEN_PARAMS_COMMON,
    "adc": UGEN_PARAMS_COMMON,
    "blackhole": UGEN_PARAMS_COMMON,
}

# All UGen parameters (for general completion when UGen type unknown)
ALL_UGEN_PARAMS = set()
for params in UGEN_PARAMS.values():
    ALL_UGEN_PARAMS |= params

# All identifiers (for completions)
ALL_KEYWORDS = KEYWORDS | TYPES | TIME_UNITS
ALL_BUILTINS = UGENS | STD_CLASSES | MATH_FUNCTIONS | STD_FUNCTIONS
ALL_IDENTIFIERS = ALL_KEYWORDS | ALL_BUILTINS

# Grouped by category for documentation
CATEGORIES = {
    "keywords": KEYWORDS,
    "types": TYPES,
    "operators": OPERATORS,
    "time_units": TIME_UNITS,
    "ugens": UGENS,
    "math": MATH_FUNCTIONS,
    "std": STD_FUNCTIONS,
    "classes": STD_CLASSES,
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
    return "unknown"
