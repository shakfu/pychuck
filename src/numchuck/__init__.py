"""
numchuck: Python bindings for ChucK audio programming language

This module provides comprehensive Python bindings for the ChucK audio
programming language, enabling real-time audio synthesis, live coding,
and programmatic control of ChucK from Python.

Example:
    >>> import numchuck
    >>>
    >>> # High-level rendering API
    >>> audio = numchuck.render("SinOsc s => dac; 1::second => now;", duration=1.0)
    >>> numchuck.to_wav("output.wav", code="SinOsc s => dac;", duration=5.0)
    >>>
    >>> # Low-level Chuck class
    >>> chuck = numchuck.Chuck(sample_rate=48000)
    >>> chuck.compile("SinOsc s => dac;")
    >>> output = chuck.run(48000)  # Returns numpy array

Specialized modules (require explicit imports):
    >>> from numchuck.osc import OSCServer, OSCClient
    >>> from numchuck.midi import MIDIMapping, MIDIMappings
    >>> from numchuck.watcher import FileWatcher
    >>> from numchuck.recorder import SessionRecorder, SessionPlayer
    >>> from numchuck.lang import ChuckLexer, KEYWORDS, UGENS

Error Handling:
    - RenderError: Compilation or rendering failed
    - ValueError: Invalid input parameters
    - RuntimeError: ChucK not initialized or operation failed
    - FileNotFoundError: ChucK file not found
"""

from ._version import __version__, __version_info__

# Core API
from .api import Chuck, GlobalFloat, GlobalInt, GlobalString, Shred

# Rendering
from .render import RenderError, render, render_file, to_wav

# Configuration
from .config import Config, get_config, load_config, save_config

__all__ = [
    # Version
    "__version__",
    "__version_info__",
    # Core
    "Chuck",
    "Shred",
    "GlobalInt",
    "GlobalFloat",
    "GlobalString",
    # Rendering
    "render",
    "render_file",
    "to_wav",
    "RenderError",
    # Config
    "Config",
    "load_config",
    "get_config",
    "save_config",
]
