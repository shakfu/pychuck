"""Centralized constants for numchuck.

This module contains all magic numbers and configuration defaults used
throughout the numchuck codebase. Import from here rather than hardcoding
values in individual modules.
"""

# =============================================================================
# Audio Defaults
# =============================================================================

DEFAULT_SAMPLE_RATE = 44100  # Hz
DEFAULT_OUTPUT_CHANNELS = 2  # Stereo output
DEFAULT_INPUT_CHANNELS = 2  # Stereo input (for API, 0 for real-time)
DEFAULT_BUFFER_SIZE = 512  # Frames per audio buffer
DEFAULT_NUM_BUFFERS = 8  # Number of audio buffers
DEFAULT_RUN_FRAMES = 256  # Frames to run for async callback execution
DEFAULT_ADAPTIVE_BLOCK_SIZE = 512  # Max block size when adaptive mode is on
DEFAULT_TAP_CAPACITY_FRAMES = 8192  # History kept per global UGen tap

# =============================================================================
# Network Ports
# =============================================================================

DEFAULT_WEB_PORT = 8080  # Web IDE server port
DEFAULT_OTF_PORT = 8888  # On-the-fly programming port
DEFAULT_OSC_PORT = 9000  # OSC (Open Sound Control) server port

# Listen addresses. Both servers accept arbitrary control of the VM, so they
# bind loopback unless the caller explicitly widens them -- and the web server
# demands an auth token whenever they do.
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_OSC_HOST = "127.0.0.1"
WEB_TOKEN_BYTES = 24  # Entropy in the generated web auth token

# =============================================================================
# Timeouts and Intervals (seconds unless noted)
# =============================================================================

# Audio
AUDIO_SHUTDOWN_TIMEOUT_MS = 500  # Audio system shutdown timeout (ms)

# File watching
FILE_DEBOUNCE_MS = 100  # Debounce time for file changes (ms)
FILE_OBSERVER_SHUTDOWN_TIMEOUT = 2.0  # File observer join timeout

# Polling/sleep intervals
POLL_INTERVAL = 0.1  # General polling delay (shred checks, etc.)
SHUTDOWN_DELAY = 0.5  # Clean shutdown delay
WATCHER_POLL_INTERVAL = 0.5  # File watcher polling delay

# Shell command
SHELL_COMMAND_TIMEOUT = 30  # Shell command timeout (seconds)

# OSC
OSC_SOCKET_TIMEOUT = 0.5  # Socket timeout for clean shutdown
OSC_THREAD_SHUTDOWN_TIMEOUT = 1.0  # OSC thread join timeout

# =============================================================================
# Limits and Sizes
# =============================================================================

MAX_CONSOLE_LINES = 100  # Maximum console log entries
WEB_MAX_CONSOLE_LINES = 300  # Web UI console log limit (larger for browser)

# =============================================================================
# MIDI Protocol Constants
# =============================================================================

MIDI_MAX_CHANNEL = 15  # MIDI channels 0-15
MIDI_MAX_CC = 127  # MIDI CC values 0-127
MIDI_CC_NORMALIZE = 127.0  # Divisor to normalize CC to 0.0-1.0

# =============================================================================
# OSC Protocol Constants
# =============================================================================

OSC_ALIGNMENT = 4  # OSC message 4-byte alignment
