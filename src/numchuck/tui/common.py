"""
Shared TUI components for editor and REPL.

Provides base class with common functionality:
- ChucK instance management
- Audio lifecycle management
- Session tracking
- Shared UI components (help, shreds table, log)
- Common key bindings
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.filters import Condition
from prompt_toolkit.widgets import TextArea

from .._numchuck import (
    ChucK,
    PARAM_SAMPLE_RATE,
    PARAM_OUTPUT_CHANNELS,
    PARAM_INPUT_CHANNELS,
    start_audio,
    stop_audio,
    shutdown_audio,
)
from .session import ChuckSession


def format_elapsed_time(elapsed_sec: float) -> str:
    """Format elapsed time in human-readable format.

    Args:
        elapsed_sec: Elapsed time in seconds

    Returns:
        Formatted string like "5.2s", "2m30.5s", or "1h05m"
    """
    if elapsed_sec < 60:
        return f"{elapsed_sec:.1f}s"
    elif elapsed_sec < 3600:
        mins = int(elapsed_sec / 60)
        secs = elapsed_sec % 60
        return f"{mins}m{secs:04.1f}s"
    else:
        hours = int(elapsed_sec / 3600)
        mins = int((elapsed_sec % 3600) / 60)
        return f"{hours}h{mins:02d}m"


def format_shred_name(full_name: str, max_len: int = 56) -> str:
    """Format shred name for display, showing parent/filename.

    Args:
        full_name: Full path or name of the shred
        max_len: Maximum length for the name

    Returns:
        Formatted name truncated to max_len
    """
    try:
        path = Path(full_name)
        if path.parent.name:
            name = f"{path.parent.name}/{path.name}"
        else:
            name = path.name
    except (ValueError, TypeError):
        name = full_name
    return name[:max_len]


def generate_shreds_table(
    shreds: dict,
    chuck,
    use_pipes: bool = False,
) -> str:
    """Generate formatted table of active shreds.

    Args:
        shreds: Dictionary of shred_id -> shred info
        chuck: ChucK instance for querying VM time and sample rate
        use_pipes: If True, use pipe separators; if False, use spaces

    Returns:
        Formatted table string
    """
    if not shreds:
        return "No active shreds"

    lines = []

    # Header
    if use_pipes:
        lines.append(
            "ID   | Name                                                    | Elapsed"
        )
        lines.append("-" * 78)
    else:
        lines.append(
            "ID    Name                                                    Elapsed"
        )
        lines.append("\u2500" * 78)  # Unicode box drawing character

    # Get current VM time for elapsed calculation
    try:
        current_time = chuck.now()
    except (RuntimeError, AttributeError):
        current_time = 0.0

    # Get sample rate
    try:
        sample_rate = chuck.get_param_int(PARAM_SAMPLE_RATE)
    except (RuntimeError, AttributeError, ValueError):
        sample_rate = 44100

    for shred_id, info in sorted(shreds.items()):
        name = format_shred_name(info["name"])

        # Calculate elapsed time in seconds
        spork_time = info.get("time", 0.0)
        elapsed_samples = current_time - spork_time
        elapsed_sec = elapsed_samples / sample_rate if sample_rate > 0 else 0.0
        time_str = format_elapsed_time(elapsed_sec)

        if use_pipes:
            lines.append(f"{shred_id:<5d} | {name:<56s} | {time_str}")
        else:
            lines.append(f"{shred_id:<5} {name:<56} {time_str}")

    return "\n".join(lines)


class ChuckApplication:
    """Base application managing ChucK instance and shared state.

    Provides common functionality for both REPL and Editor:
    - ChucK instance lifecycle management
    - Audio start/stop/shutdown
    - Output capture (chout/cherr)
    - Session tracking with optional project support
    - Shared UI components
    """

    def __init__(
        self,
        project_name: str | None = None,
        sample_rate: int = 44100,
        output_channels: int = 2,
        input_channels: int = 0,
        auto_init: bool = False,
    ):
        """Initialize the application.

        Args:
            project_name: Optional project name for file versioning
            sample_rate: Audio sample rate in Hz
            output_channels: Number of output audio channels
            input_channels: Number of input audio channels
            auto_init: If True, initialize ChucK immediately
        """
        self.chuck = ChucK()
        self._sample_rate = sample_rate
        self._output_channels = output_channels
        self._input_channels = input_channels

        self.session = ChuckSession(self.chuck, project_name=project_name)
        self.audio_running = False

        # Shared UI state
        self.show_help = False
        self.show_shreds = False
        self.show_log = False

        # Log tracking
        self.log_messages: list[str] = []
        self._log_callback: Callable[[str], None] | None = None

        if auto_init:
            self.setup()

    def setup(self) -> None:
        """Initialize ChucK with configured parameters.

        Call this before using the ChucK instance.
        """
        self.chuck.set_param(PARAM_SAMPLE_RATE, self._sample_rate)
        self.chuck.set_param(PARAM_OUTPUT_CHANNELS, self._output_channels)
        self.chuck.set_param(PARAM_INPUT_CHANNELS, self._input_channels)
        self.chuck.init()

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for log messages.

        Args:
            callback: Function to call with log messages
        """
        self._log_callback = callback

    def setup_output_capture(self) -> None:
        """Set up ChucK output capture to log messages.

        Captures both chout and cherr output.
        """

        def log_callback(msg: str) -> None:
            self.log_messages.append(msg)
            if self._log_callback:
                self._log_callback(msg)

        self.chuck.set_chout_callback(log_callback)
        self.chuck.set_cherr_callback(log_callback)

    def start_audio_playback(self) -> bool:
        """Start real-time audio playback.

        Returns:
            True if audio started successfully, False otherwise
        """
        if self.audio_running:
            return True

        try:
            start_audio(self.chuck)
            self.audio_running = True
            self.session.audio_running = True
            return True
        except Exception as e:
            print(f"Warning: Could not start audio: {e}", file=sys.stderr)
            return False

    def stop_audio_playback(self) -> None:
        """Stop real-time audio playback."""
        if not self.audio_running:
            return

        try:
            stop_audio()
        except (RuntimeError, OSError) as e:
            print(f"Warning: Error stopping audio: {e}", file=sys.stderr)

        try:
            shutdown_audio(500)
        except (RuntimeError, OSError) as e:
            print(f"Warning: Error shutting down audio: {e}", file=sys.stderr)

        self.audio_running = False
        self.session.audio_running = False

    def get_common_key_bindings(self):
        """Common key bindings shared across editor and REPL."""
        kb = KeyBindings()

        @kb.add("c-q")
        def exit_app(event):
            """Exit application"""
            event.app.exit()

        @kb.add("f1")
        def toggle_help(event):
            """Toggle help window"""
            self.show_help = not self.show_help
            event.app.invalidate()

        @kb.add("f2")
        def toggle_shreds(event):
            """Toggle shreds table"""
            self.show_shreds = not self.show_shreds
            event.app.invalidate()

        @kb.add("f3")
        def toggle_log(event):
            """Toggle log window"""
            self.show_log = not self.show_log
            event.app.invalidate()

        return kb

    def create_help_window(self, help_text):
        """Create help window that toggles with F1."""
        help_area = TextArea(
            text=help_text,
            scrollbar=True,
            focusable=False,
            read_only=True,
            wrap_lines=True,
        )

        return ConditionalContainer(
            Window(
                content=help_area.control, height=D(min=10, max=30), wrap_lines=True
            ),
            filter=Condition(lambda: self.show_help),
        )

    def create_shreds_table(self):
        """Create shreds table that toggles with F2."""

        def get_text():
            return generate_shreds_table(
                self.session.shreds, self.chuck, use_pipes=True
            )

        return ConditionalContainer(
            Window(content=FormattedTextControl(get_text), height=D(min=5, max=15)),
            filter=Condition(lambda: self.show_shreds),
        )

    def create_log_window(self, log_area: TextArea | None = None):
        """Create log window that toggles with F3.

        Args:
            log_area: Optional pre-created TextArea. If None, creates one.

        Returns:
            ConditionalContainer with log window
        """
        if log_area is None:
            log_area = TextArea(
                text="", scrollbar=True, focusable=False, read_only=True
            )

        def log_callback(msg: str) -> None:
            """Callback for ChucK output"""
            log_area.text += msg
            if len(self.log_messages) > 1000:
                # Trim old messages
                self.log_messages = self.log_messages[-500:]
                log_area.text = "".join(self.log_messages[-500:])

        # Set up output capture with the log callback
        self.set_log_callback(log_callback)
        self.setup_output_capture()

        return ConditionalContainer(log_area, filter=Condition(lambda: self.show_log))

    def create_status_bar(self, status_text_func: Callable[[], str]):
        """Create status bar at bottom of screen.

        Args:
            status_text_func: Function returning status bar text

        Returns:
            Window with status bar
        """
        return Window(
            content=FormattedTextControl(status_text_func),
            height=1,
            style="bg:#444444 fg:#ffffff",
        )

    def cleanup(self) -> None:
        """Cleanup ChucK and audio resources.

        This method:
        1. Removes all shreds
        2. Stops audio if running
        3. Breaks circular references for garbage collection
        """
        # Remove all shreds first
        try:
            self.chuck.remove_all_shreds()
        except (RuntimeError, AttributeError):
            pass

        # Stop audio if running
        if self.audio_running:
            self.stop_audio_playback()

        # Break circular references to allow proper garbage collection
        if hasattr(self, "session"):
            self.session.chuck = None
            del self.session
        if hasattr(self, "chuck"):
            del self.chuck
