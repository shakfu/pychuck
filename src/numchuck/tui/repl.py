from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING, Any

from prompt_toolkit.key_binding import KeyPressEvent

from .parser import CommandParser
from .commands import CommandExecutor
from ..paths import get_history_file, ensure_numchuck_directories
from .common import ChuckApplication, generate_shreds_table
from .completer import ChuckCompleter
from .waveform import format_waveform_bar

if TYPE_CHECKING:
    pass


class ChuckREPLStdin:
    """Non-interactive REPL that reads from stdin.

    Used when stdin is piped or redirected, allowing testing and scripting:
        echo '+ test.ck' | numchuck repl
        cat commands.txt | numchuck repl
        numchuck repl < script.txt
    """

    def __init__(
        self,
        project_name: str | None = None,
        otf_enable: bool = False,
        otf_port: int = 8888,
    ) -> None:
        self.app_state = ChuckApplication(
            project_name=project_name,
            otf_enable=otf_enable,
            otf_port=otf_port,
        )
        self.chuck = self.app_state.chuck
        self.session = self.app_state.session
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session)

    def setup(self) -> None:
        """Initialize ChucK with sensible defaults."""
        # Don't set static callbacks - they cause segfaults on cleanup
        # Instance callbacks are safer
        self.app_state.setup()

        # Capture output to stderr so it doesn't mix with command output
        def log_to_stderr(msg: str) -> None:
            sys.stderr.write(msg)
            sys.stderr.flush()

        self.app_state.set_log_callback(log_to_stderr)
        self.app_state.setup_output_capture()

    def process_line(self, line: str) -> str | None:
        """Process a single line of input.

        Args:
            line: Input line to process

        Returns:
            Error message if any, None on success
        """
        text = line.strip()

        if not text or text.startswith("#"):
            return None  # Skip empty lines and comments

        if text in ["quit", "exit", "q"]:
            return "EXIT"

        # Parse and execute
        try:
            cmd = self.parser.parse(text)
            if cmd:
                return self.executor.execute(cmd)
            else:
                # If not a recognized command, treat as ChucK code
                if "\n" in text or "=>" in text or ";" in text or "{" in text:
                    result = self.app_state.shred_service.spork_code(text, name="stdin")
                    if not result.success:
                        return result.error or "Failed to compile code"
                else:
                    return f"Unknown command: {text}"
        except Exception as e:
            return f"Error: {e}"

        return None

    def run(
        self,
        start_audio: bool = False,
        files: list[str] | None = None,
        input_stream: Any = None,
    ) -> int:
        """Run REPL reading from stdin.

        Args:
            start_audio: If True, start audio automatically
            files: Optional list of ChucK files to load on startup
            input_stream: Optional input stream (defaults to sys.stdin)

        Returns:
            Exit code (0 for success, 1 for error)
        """
        if input_stream is None:
            input_stream = sys.stdin

        exit_code = 0

        try:
            self.setup()

            if start_audio:
                self.app_state.start_audio_playback()

            # Load files if provided
            if files:
                for filepath in files:
                    cmd = self.parser.parse(f"+ {filepath}")
                    if cmd:
                        result = self.executor.execute(cmd)
                        if result:
                            sys.stderr.write(f"Error loading {filepath}: {result}\n")
                            exit_code = 1

            # Process each line from input
            for line in input_stream:
                error = self.process_line(line)
                if error == "EXIT":
                    break
                elif error:
                    sys.stderr.write(f"Error: {error}\n")
                    exit_code = 1

        finally:
            self.cleanup()

        return exit_code

    def cleanup(self) -> None:
        """Shutdown cleanly."""
        import gc

        # Clear convenience references FIRST (before app_state.cleanup closes ChucK)
        self.chuck = None  # type: ignore[assignment]
        self.session = None  # type: ignore[assignment]

        # Break executor references
        if hasattr(self, "executor") and self.executor is not None:
            self.executor._chuck = None
            self.executor.session = None  # type: ignore[assignment]
            self.executor = None  # type: ignore[assignment]

        # Now cleanup app_state (this closes ChucK instance)
        if hasattr(self, "app_state") and self.app_state is not None:
            self.app_state.cleanup()
            self.app_state = None  # type: ignore[assignment]

        # Force garbage collection multiple times to break all cycles
        # and release C++ objects before interpreter shutdown
        gc.collect()
        gc.collect()
        gc.collect()


class ChuckREPL:
    """Interactive REPL for ChucK with full-screen UI."""

    def __init__(
        self,
        smart_enter: bool = True,
        show_sidebar: bool = True,
        project_name: str | None = None,
        otf_enable: bool = False,
        otf_port: int = 8888,
    ) -> None:
        # Use ChuckApplication for shared ChucK management
        self.app_state = ChuckApplication(
            project_name=project_name,
            otf_enable=otf_enable,
            otf_port=otf_port,
        )
        self.chuck = self.app_state.chuck  # Convenience reference
        self.session = self.app_state.session  # Convenience reference
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session, log_callback=self.add_to_log)
        self.smart_enter = smart_enter  # Enable smart Enter behavior
        self.show_sidebar = show_sidebar  # Show/hide sidebar

        # Import prompt_toolkit (now a required dependency)
        from prompt_toolkit import Application
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.styles import Style
        from prompt_toolkit.layout.containers import (
            HSplit,
            Window,
            ConditionalContainer,
        )
        from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
        from prompt_toolkit.layout.layout import Layout
        from prompt_toolkit.layout.dimension import Dimension as D
        from prompt_toolkit.layout.margins import ScrollbarMargin
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.widgets import TextArea

        # Create context-aware completer using the session and chuck instance
        self.completer = ChuckCompleter(self.session, self.chuck)

        # Help window visibility
        self.show_help_window = False

        # Shreds table window visibility
        self.show_shreds_window = False

        # Meter display state
        self._meter_stop = threading.Event()
        self._meter_thread: threading.Thread | None = None
        self._current_meters: dict[str, float] = {
            "rms_left": 0.0,
            "rms_right": 0.0,
            "peak_left": 0.0,
            "peak_right": 0.0,
        }

        # Single-buffer transcript: all text lives here, user edits after prompt
        self.prompt_prefix = "[=>] "
        self.input_start = len(
            self.prompt_prefix
        )  # Position where editable text begins
        self.max_transcript_lines = 500

        # Create topbar content function (simplified to show just IDs)
        def get_topbar_text() -> str:
            """Generate topbar content showing active shred IDs"""
            if self.session.shreds:
                shred_ids = " ".join(
                    f"[{sid}]" for sid in sorted(self.session.shreds.keys())
                )
                return f"Shreds: {shred_ids}  (F2: table)"
            else:
                return "No active shreds  (F2: table)"

        # Create help text content
        help_text = """\
SHRED MANAGEMENT                        STATUS & INFO
  + <file.ck>  / add <file.ck>            ? / shreds       List shreds
  + "<code>"     Spork code               ? <id> / shred   Shred info
  - <id>       / remove <id>              ?g / globals     List globals
  - all        / remove all               ?a / audio       Audio info
  edit <id>      Edit shred               .                Current time

GLOBALS                                 EVENTS
  <name>::<val> / set <name> <val>        <ev>! / signal <ev>
  <name>?       / get <name>              <ev>!! / broadcast <ev>

AUDIO CONTROL                           VM CONTROL
  > / start      Start audio              clear     Clear VM
  || / stop      Stop audio               reset     Reset shred ID
  X / shutdown   Shutdown                 cls       Clear screen

RECORDING                               PLAYBACK
  record start [name]  Start recording    play <name> [speed]  Start
  record stop          Stop & save        play pause/resume    Pause/resume
  record save <name>   Save as name       play stop            Stop
  record discard       Discard            recordings           List all
  record status        Show status

MIDI                                    OSC
  midi learn <var> <cc> [ch] [min max]    osc start [port]  Start server
  midi list            List mappings      osc stop          Stop server
  midi start/stop      Listener on/off    osc status        Show status
  midi status          Show status
  midi monitor         Monitor CC input   WAVEFORM
  midi remove <var>    Remove mapping     wave              Toggle display
                                          wave on/off       Enable/disable

OTHER COMMANDS                          KEYBOARD SHORTCUTS
  : <file> / compile <file>               F1        Toggle help
  ! "code" / exec "code"                  F2        Shreds table
  $ <cmd>  / shell <cmd>                  Ctrl+Q    Exit REPL
  @<name>  / snippet <name>               Ctrl+R    History search
  edit           Open editor              Esc+Enter Submit code
  watch <file>   Auto-reload              Tab       Auto-complete
  unwatch <file> Stop watching
  watching       List watched"""

        # Create help TextArea (scrollable, adapts to terminal height)
        self.help_area = TextArea(
            text=help_text,
            read_only=True,
            scrollbar=True,
            focusable=False,
            height=D(min=10, preferred=30),
            style="class:help-area",
        )

        # Create shreds table function
        def get_shreds_table() -> str:
            """Generate formatted table of active shreds"""
            return generate_shreds_table(
                self.session.shreds, self.chuck, use_pipes=False
            )

        # Store the shreds table generator function
        self.get_shreds_table = get_shreds_table

        # Create shreds table TextArea (non-scrollable, auto-sized)
        self.shreds_area = TextArea(
            text="",
            read_only=True,
            scrollbar=False,
            focusable=False,
            height=D(min=0, max=20),  # Auto-size up to 20 lines
            style="class:shreds-area",
        )

        # Create bottom toolbar function (shows VM status)
        def get_bottom_toolbar() -> str:
            try:
                # Sync session shreds with VM (discovers OTF-added/removed shreds).
                # Runs on the event loop thread via refresh_interval=0.1.
                self.app_state.sync_shreds()
                audio_status = "ON" if self.session.audio_running else "OFF"
                now = self.chuck.now()
                shred_count = len(self.session.shreds)
                parts = [
                    f"Audio: {audio_status}",
                    f"Now: {now:.2f}",
                    f"Shreds: {shred_count}",
                ]
                if self.app_state.otf_enabled:
                    parts.append(f"OTF: {self.app_state.otf_port}")
                parts.append("F1: help")
                return " | ".join(parts)
            except Exception:
                return "Audio: -- | Now: -- | Shreds: --"

        # Custom style for syntax highlighting and prompt
        repl_style = Style.from_dict(
            {
                "bottom-toolbar": "#ffffff bg:#333333",
                "top-toolbar": "#00ffff bg:#000033",  # cyan on dark blue for topbar
                "help-area": "#aaaaaa bg:#222222",  # gray on dark gray for help
                "repl-buffer": "#cccccc bg:#111111",  # main REPL buffer
                "shreds-area": "#00ffff bg:#001133",  # cyan on dark blue for shreds table
                "waveform-area": "#00ff00 bg:#001100",  # green on dark green for meters
                "prompt-bracket": "#ff8800",  # orange for brackets
                "prompt-chuck": "#00ff00",  # green for =>
            }
        )

        # Key bindings
        kb = KeyBindings()

        # Topbar visibility condition
        @Condition
        def topbar_visible() -> bool:
            return self.show_sidebar

        @kb.add("f2")
        def _(event: KeyPressEvent) -> None:
            """Toggle shreds table window with F2"""
            self.show_shreds_window = not self.show_shreds_window
            if self.show_shreds_window:
                self.shreds_area.text = self.get_shreds_table()
            event.app.invalidate()

        @kb.add("f1")
        def _(event: KeyPressEvent) -> None:
            """Toggle help window with F1"""
            self.show_help_window = not self.show_help_window
            event.app.invalidate()

        @kb.add("c-q")
        def _(event: KeyPressEvent) -> None:
            """Exit with Ctrl-Q"""
            event.app.exit()

        # Guard: prevent cursor from moving into read-only transcript region
        @kb.add("left")
        @kb.add("backspace")
        def _(event: KeyPressEvent) -> None:
            """Prevent editing before input_start."""
            buf = event.current_buffer
            if buf.cursor_position <= self.input_start:
                return  # Block
            # Otherwise, do the default action
            if event.data == "\x7f":  # backspace
                buf.delete_before_cursor()
            else:
                buf.cursor_left()

        @kb.add("home")
        @kb.add("c-a")
        def _(event: KeyPressEvent) -> None:
            """Home goes to input_start, not beginning of buffer."""
            event.current_buffer.cursor_position = self.input_start

        @kb.add("c-u")
        def _(event: KeyPressEvent) -> None:
            """Clear current input line."""
            buf = event.current_buffer
            buf.text = buf.text[: self.input_start]
            buf.cursor_position = self.input_start

        @kb.add("up")
        def _(event: KeyPressEvent) -> None:
            """Navigate history (previous)."""
            self._history_navigate(-1)

        @kb.add("down")
        def _(event: KeyPressEvent) -> None:
            """Navigate history (next)."""
            self._history_navigate(1)

        @kb.add("enter")
        def _(event: KeyPressEvent) -> None:
            """Submit current input on Enter."""
            buf = event.current_buffer
            user_text = buf.text[self.input_start :]

            # Smart multiline: if ChucK code markers present, use Esc+Enter
            if self.smart_enter and self._should_continue_multiline(user_text):
                buf.insert_text("\n")
                return

            self._submit_input(user_text)

        @kb.add("escape", "enter")
        def _(event: KeyPressEvent) -> None:
            """Force-submit with Esc+Enter (bypass multiline detection)."""
            buf = event.current_buffer
            user_text = buf.text[self.input_start :]
            self._submit_input(user_text)

        # Ensure numchuck directories exist
        ensure_numchuck_directories()

        # History state
        self.history = FileHistory(str(get_history_file()))
        self._history_strings: list[str] = []
        self._history_index = 0
        self._history_tmp = ""  # Stash current input when browsing history

        # Create single REPL buffer with initial prompt
        self.buffer = Buffer(
            multiline=True,
            completer=self.completer,
            complete_while_typing=False,
        )
        self.buffer.text = self.prompt_prefix
        self.buffer.cursor_position = self.input_start

        # Main REPL window -- single buffer, fills available space
        repl_window = Window(
            content=BufferControl(buffer=self.buffer),
            wrap_lines=True,
            height=D(weight=1),
            style="class:repl-buffer",
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

        # Create topbar window
        topbar_window = ConditionalContainer(
            Window(
                content=FormattedTextControl(text=get_topbar_text),
                height=D.exact(1),
                style="class:top-toolbar",
            ),
            filter=topbar_visible,
        )

        # Create help window (conditional)
        @Condition
        def help_visible() -> bool:
            return self.show_help_window

        help_window = ConditionalContainer(self.help_area, filter=help_visible)

        # Create shreds table window (conditional)
        @Condition
        def shreds_visible() -> bool:
            return self.show_shreds_window

        shreds_window = ConditionalContainer(self.shreds_area, filter=shreds_visible)

        # Meter display -- L and R bars in separate 1-line windows
        def get_meter_left() -> str:
            m = self._current_meters
            return f"L {format_waveform_bar(m.get('peak_left', 0.0), width=40)}"

        def get_meter_right() -> str:
            m = self._current_meters
            return f"R {format_waveform_bar(m.get('peak_right', 0.0), width=40)}"

        @Condition
        def waveform_visible() -> bool:
            return self.session.show_waveform

        meter_window = ConditionalContainer(
            HSplit(
                [
                    Window(
                        content=FormattedTextControl(text=get_meter_left),
                        height=D.exact(1),
                        style="class:waveform-area",
                    ),
                    Window(
                        content=FormattedTextControl(text=get_meter_right),
                        height=D.exact(1),
                        style="class:waveform-area",
                    ),
                ]
            ),
            filter=waveform_visible,
        )

        # Layout: topbar, repl buffer (fills space), toggles, meters, status bar
        root_container = HSplit(
            [
                topbar_window,
                repl_window,
                help_window,
                shreds_window,
                meter_window,
                Window(
                    height=D.exact(1),
                    content=FormattedTextControl(text=get_bottom_toolbar),
                    style="class:bottom-toolbar",
                ),
            ]
        )

        # Create application.
        # refresh_interval drives meter redraws from the event loop thread
        # (no background thread invalidation needed).
        self.app: Any = Application(
            layout=Layout(root_container),
            key_bindings=kb,
            style=repl_style,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.1,
        )

    def _should_continue_multiline(self, text: str) -> bool:
        """Check if Enter should insert a newline instead of submitting."""
        if "\n" in text:
            return True
        stripped = text.strip()
        if not stripped:
            return False
        single_line_cmds = [
            "quit",
            "exit",
            "q",
            "help",
            "clear",
            "reset",
            "cls",
            "watch",
            "?",
            "?g",
            "?a",
            ".",
            ">",
            "||",
            "X",
            "shreds",
            "globals",
            "audio",
            "start",
            "stop",
            "shutdown",
        ]
        if stripped in single_line_cmds:
            return False
        if stripped.startswith(
            (
                "+",
                "-",
                "~",
                "?",
                ":",
                "!",
                "$",
                "@",
                "edit",
                "shred ",
                "compile ",
                "exec ",
                "shell ",
                "snippet ",
                "get ",
                "set ",
                "signal ",
                "broadcast ",
            )
        ):
            return False
        if any(marker in stripped for marker in ["=>", ";", "{"]):
            return True
        return False

    def _history_navigate(self, direction: int) -> None:
        """Navigate command history. direction: -1=older, +1=newer."""
        if not self._history_strings:
            return
        if self._history_index == len(self._history_strings):
            self._history_tmp = self.buffer.text[self.input_start :]
        new_index = self._history_index + direction
        if new_index < 0 or new_index > len(self._history_strings):
            return
        self._history_index = new_index
        if new_index == len(self._history_strings):
            replacement = self._history_tmp
        else:
            replacement = self._history_strings[new_index]
        self.buffer.text = self.buffer.text[: self.input_start] + replacement
        self.buffer.cursor_position = len(self.buffer.text)

    def _trim_transcript(self) -> None:
        """Trim buffer to max_transcript_lines."""
        lines = self.buffer.text.split("\n")
        if len(lines) > self.max_transcript_lines:
            trimmed = lines[-self.max_transcript_lines :]
            self.buffer.text = "\n".join(trimmed)
            self.input_start = len(self.buffer.text) - len(
                self.buffer.text.split("\n")[-1]
            )
            # Recalculate: input_start is after the last prompt prefix
            last_line = self.buffer.text.split("\n")[-1]
            self.input_start = (
                len(self.buffer.text) - len(last_line) + len(self.prompt_prefix)
            )

    def _append_line(self, text: str) -> None:
        """Append a line to the buffer before the current prompt line."""
        # Insert text before the current prompt line
        before_prompt = self.buffer.text[: self.input_start - len(self.prompt_prefix)]
        if before_prompt and not before_prompt.endswith("\n"):
            before_prompt += "\n"
        before_prompt += text + "\n"
        current_input = self.buffer.text[self.input_start :]
        self.buffer.text = before_prompt + self.prompt_prefix + current_input
        self.input_start = len(before_prompt) + len(self.prompt_prefix)
        self.buffer.cursor_position = len(self.buffer.text)
        self._trim_transcript()
        self.app.invalidate()

    def add_to_log(self, msg: str) -> None:
        """Capture ChucK VM messages inline in transcript.

        Args:
            msg: Message to add to transcript
        """
        msg = msg.rstrip("\n")
        if msg:
            self._append_line(f"  {msg}")

    def _echo_error(self, msg: str) -> None:
        """Append an error inline in the transcript."""
        self._append_line(f"  [!] {msg}")

    def _meter_update_loop(self) -> None:
        """Poll audio meters (daemon thread).

        Only updates _current_meters data. Redraws are driven by
        Application(refresh_interval=0.1) on the event loop thread.
        """
        from .._numchuck import get_audio_meters, is_audio_running

        _zero_meters = {
            "rms_left": 0.0,
            "rms_right": 0.0,
            "peak_left": 0.0,
            "peak_right": 0.0,
        }

        while not self._meter_stop.is_set():
            try:
                if self.session.show_waveform and is_audio_running():
                    meters = get_audio_meters()
                    self._current_meters = {
                        "rms_left": float(meters["rms_left"]),
                        "rms_right": float(meters["rms_right"]),
                        "peak_left": float(meters["peak_left"]),
                        "peak_right": float(meters["peak_right"]),
                    }
                else:
                    self._current_meters = _zero_meters.copy()
            except Exception:
                pass
            self._meter_stop.wait(0.1)

    def setup(self) -> None:
        """Initialize ChucK with sensible defaults.

        Uses only instance-level callbacks (chout/cherr), not static
        stdout/stderr callbacks. Static callbacks cause segfaults on
        cleanup because they outlive the Python objects they reference.
        """
        self.app_state.setup()

        # Use instance-level output capture (cleaned up by chuck.shutdown())
        self.app_state.set_log_callback(self.add_to_log)
        self.app_state.setup_output_capture()

        # Start meter polling thread
        self._meter_stop.clear()
        self._meter_thread = threading.Thread(
            target=self._meter_update_loop, daemon=True, name="numchuck-meters"
        )
        self._meter_thread.start()

    def _submit_input(self, user_text: str) -> None:
        """Process submitted input and prepare a new prompt line."""
        text = user_text.strip()

        # Freeze the current input into transcript: remove prompt, re-add as echo
        # The buffer already shows "[=>] <input>" on the current line(s).
        # Just move to a new prompt.
        if not text:
            # Empty enter: just add a new prompt line
            self.buffer.text = self.buffer.text + "\n" + self.prompt_prefix
            self.input_start = len(self.buffer.text)
            self.buffer.cursor_position = self.input_start
            self._trim_transcript()
            self.app.invalidate()
            return

        # Add to history
        self._history_strings.append(text)
        self._history_index = len(self._history_strings)
        self._history_tmp = ""
        # Persist to file history
        self.history.append_string(text)

        # Freeze current input and immediately set up new prompt.
        # This ensures _append_line / _echo_error can insert output
        # between the frozen input and the new prompt.
        self.buffer.text = self.buffer.text + "\n" + self.prompt_prefix
        self.input_start = len(self.buffer.text)
        self.buffer.cursor_position = self.input_start

        if text in ["quit", "exit", "q"]:
            self.app.exit()
            return

        if text == "help":
            self.show_help_window = not self.show_help_window

        elif text == "cls":
            # Clear screen: reset buffer to just a prompt
            self.buffer.text = self.prompt_prefix
            self.input_start = len(self.prompt_prefix)
            self.buffer.cursor_position = self.input_start
            self.app.invalidate()
            return
        else:
            # Parse and execute
            try:
                cmd = self.parser.parse(text)
                if cmd:
                    error = self.executor.execute(cmd)
                    if error:
                        self._echo_error(error)
                else:
                    if "\n" in text or "=>" in text or ";" in text or "{" in text:
                        result = self.app_state.shred_service.spork_code(
                            text, name="repl"
                        )
                        if not result.success:
                            self._echo_error(result.error or "Failed to compile code")
                    else:
                        self._echo_error(f"Unknown command: {text}")
            except Exception as e:
                self._echo_error(f"Error: {e}")

        self._trim_transcript()
        self.app.invalidate()

    def run(self, start_audio: bool = False, files: list[str] | None = None) -> None:
        """Main REPL loop.

        Args:
            start_audio: If True, start audio automatically on startup
            files: Optional list of ChucK files to load on startup
        """
        try:
            self.setup()

            # Start audio if requested
            if start_audio:
                self.app_state.start_audio_playback()

            # Load files if provided
            if files:
                for filepath in files:
                    try:
                        cmd = self.parser.parse(f"+ {filepath}")
                        if cmd:
                            result = self.executor.execute(cmd)
                            if result:
                                self.add_to_log(result)
                    except Exception as e:
                        self.add_to_log(f"Error loading {filepath}: {e}")

            # Disable terminal mouse tracking and other escape sequences
            # that might be left over from previous programs
            sys.stdout.write("\033[?1000l")  # Disable mouse tracking
            sys.stdout.write("\033[?1003l")  # Disable all mouse tracking
            sys.stdout.write("\033[?1006l")  # Disable SGR mouse mode
            sys.stdout.flush()

            # Load command history from file
            self._history_strings = list(self.history.load_history_strings())
            self._history_index = len(self._history_strings)

            # Run the application
            self.app.run()

        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Shutdown cleanly."""
        import gc

        print("\nShutting down...")

        # Stop meter polling thread
        self._meter_stop.set()
        if self._meter_thread is not None:
            self._meter_thread.join(timeout=1.0)
            self._meter_thread = None

        # Neutralize instance-level callbacks BEFORE anything else.
        # These closures reference self -> add_to_log -> buffer, and if
        # ChucK fires them during shutdown we get a double-free.
        if hasattr(self, "app_state") and self.app_state is not None:
            self.app_state._log_callback = None

        def _noop(msg: str) -> None:
            pass

        try:
            if hasattr(self, "chuck") and self.chuck is not None:
                self.chuck.set_chout_callback(_noop)
                self.chuck.set_cherr_callback(_noop)
        except (RuntimeError, AttributeError):
            pass

        # Break completer -> chuck/session refs (Buffer holds completer)
        if hasattr(self, "completer") and self.completer is not None:
            self.completer.chuck = None  # type: ignore[assignment]
            self.completer.session = None  # type: ignore[assignment]
            self.completer = None  # type: ignore[assignment]

        # Clear convenience references
        self.chuck = None  # type: ignore[assignment]
        self.session = None  # type: ignore[assignment]

        # Break executor references
        if hasattr(self, "executor") and self.executor is not None:
            self.executor._chuck = None
            self.executor.session = None  # type: ignore[assignment]
            self.executor = None  # type: ignore[assignment]

        # Force GC to release cycles BEFORE shutting down C++ objects
        gc.collect()
        gc.collect()

        # Now cleanup app_state (calls chuck.shutdown() and destroys C++ object)
        if hasattr(self, "app_state") and self.app_state is not None:
            self.app_state.cleanup()
            self.app_state = None  # type: ignore[assignment]

        gc.collect()
