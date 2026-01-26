"""
numchuck: Python bindings for ChucK audio programming language

This module provides comprehensive Python bindings for the ChucK audio
programming language, enabling real-time audio synthesis, live coding,
and programmatic control of ChucK from Python.

Example:
    >>> from numchuck import Chuck
    >>> chuck = Chuck(sample_rate=48000, output_channels=2)
    >>> chuck.sample_rate
    48000
    >>> success, shreds = chuck.compile("SinOsc s => dac;")
    >>> output = chuck.run(1000)  # Returns numpy array

Error Handling:
    All ChucK operations that can fail will raise exceptions:
    - ValueError: Invalid input parameters (empty strings, zero/negative values)
    - RuntimeError: ChucK not initialized or operation failed
    - TypeError: Incorrect type passed to function
"""

from ._version import __version__, __version_info__
from .api import Chuck, GlobalFloat, GlobalInt, GlobalString, Shred
from .config import Config, load_config, get_config, save_config

__all__ = [
    "__version__",
    "__version_info__",
    "Chuck",
    "Shred",
    "GlobalInt",
    "GlobalFloat",
    "GlobalString",
    "Config",
    "load_config",
    "get_config",
    "save_config",
]
