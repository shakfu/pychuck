from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .parser import CommandParser
from .commands import CommandExecutor
from ..paths import get_history_file, ensure_numchuck_directories
from .common import ChuckApplication, generate_shreds_table
from .completer import ChuckCompleter

if TYPE_CHECKING:
    from prompt_toolkit.buffer import Buffer


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
    ) -> None:
        self.app_state = ChuckApplication(project_name=project_name)
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
            self.executor._chuck = None  # type: ignore[assignment]
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
    ) -> None:
        # Use ChuckApplication for shared ChucK management
        self.app_state = ChuckApplication(project_name=project_name)
        self.chuck = self.app_state.chuck  # Convenience reference
        self.session = self.app_state.session  # Convenience reference
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session)
        self.smart_enter = smart_enter  # Enable smart Enter behavior
        self.show_sidebar = show_sidebar  # Show/hide sidebar

        # Import prompt_toolkit (now a required dependency)
        from prompt_toolkit import Application
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.lexers import PygmentsLexer
        from prompt_toolkit.styles import Style
        from prompt_toolkit.formatted_text import HTML
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

        # Try to import ChucK lexer, fall back to C lexer
        lexer_class: Any
        try:
            from ..lang import ChuckLexer

            lexer_class = ChuckLexer
        except ImportError:
            from pygments.lexers.c_cpp import CLexer

            lexer_class = CLexer

        # Create context-aware completer using the session and chuck instance
        self.completer = ChuckCompleter(self.session, self.chuck)

        # Error message state
        self.error_message = ""

        # Help window visibility
        self.show_help_window = False

        # Shreds table window visibility
        self.show_shreds_window = False

        # Log window visibility and buffer
        self.show_log_window = False
        self.log_lines: list[str] = []
        self.max_log_lines = 100  # Keep last 100 messages

        # Create topbar content function (simplified to show just IDs)
        def get_topbar_text():
            """Generate topbar content showing active shred IDs"""
            if self.session.shreds:
                shred_ids = " ".join(
                    f"[{sid}]" for sid in sorted(self.session.shreds.keys())
                )
                return f"Shreds: {shred_ids}  (F2: table)"
            else:
                return "No active shreds  (F2: table)"

        # Create error bar function
        def get_error_text():
            """Show error message if any"""
            if self.error_message:
                return f"✗ {self.error_message}"
            return ""

        # Create help text content
        help_text = """\
SHRED MANAGEMENT                        STATUS & INFO
  + <file.ck>    Spork file               ?         List shreds
  + "<code>"     Spork code               ? <id>    Shred info
  - <id>         Remove shred             ?g        List globals
  - all          Remove all               ?a        Audio info
  edit <id>      Edit shred               .         Current time

GLOBALS                                 EVENTS
  <name>::<val>  Set global               <ev>!     Signal event
  <name>?        Get global               <ev>!!    Broadcast event

AUDIO CONTROL                           VM CONTROL
  >              Start audio              clear     Clear VM
  ||             Stop audio               reset     Reset shred ID
  X              Shutdown                 cls       Clear screen

OTHER COMMANDS                          KEYBOARD SHORTCUTS
  : <file>       Compile only             F1        Toggle help
  $ <cmd>        Shell cmd                F2        Shreds table
  edit           Open editor              F3        Toggle log
  @<name>        Load snippet             Ctrl+Q    Exit REPL
                                          Ctrl+R    History search
                                          Esc+Enter Submit code
                                          Tab       Auto-complete"""

        # Create help TextArea (non-scrollable, fits exactly)
        self.help_area = TextArea(
            text=help_text,
            read_only=True,
            scrollbar=False,
            focusable=False,
            height=D.exact(20),  # Exact height to fit help text
            style="class:help-area",
        )

        # Create log TextArea (scrollable, for VM messages)
        self.log_area = TextArea(
            text="",
            read_only=True,
            scrollbar=True,
            focusable=False,
            height=D(min=0, max=30),  # Scrollable log area
            style="class:log-area",
        )

        # Create shreds table function
        def get_shreds_table():
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
        def get_bottom_toolbar():
            try:
                audio_status = "ON" if self.session.audio_running else "OFF"
                now = self.chuck.now()
                shred_count = len(self.session.shreds)
                return f"Audio: {audio_status} | Now: {now:.2f} | Shreds: {shred_count}"
            except (RuntimeError, AttributeError):
                return "Audio: -- | Now: -- | Shreds: --"

        # Custom style for syntax highlighting and prompt
        repl_style = Style.from_dict(
            {
                "bottom-toolbar": "#ffffff bg:#333333",
                "top-toolbar": "#00ffff bg:#000033",  # cyan on dark blue for topbar
                "error-toolbar": "#ffffff bg:#cc0000",  # white on red for errors
                "help-area": "#aaaaaa bg:#222222",  # gray on dark gray for help
                "log-area": "#cccccc bg:#111111",  # lighter gray for log
                "shreds-area": "#00ffff bg:#001133",  # cyan on dark blue for shreds table
                "prompt-bracket": "#ff8800",  # orange for brackets
                "prompt-chuck": "#00ff00",  # green for =>
            }
        )

        # Key bindings for enhanced history search and multiline
        kb = KeyBindings()

        # Topbar visibility condition
        @Condition
        def topbar_visible():
            return self.show_sidebar

        @kb.add("c-s")
        def _(event):
            """Forward history search with Ctrl+S"""
            event.current_buffer.history_forward()

        @kb.add("f2")
        def _(event):
            """Toggle shreds table window with F2"""
            self.show_shreds_window = not self.show_shreds_window
            # Update shreds table content when opening
            if self.show_shreds_window:
                self.shreds_area.text = self.get_shreds_table()
            event.app.invalidate()  # Force redraw

        @kb.add("f1")
        def _(event):
            """Toggle help window with F1"""
            self.show_help_window = not self.show_help_window
            event.app.invalidate()  # Force redraw

        @kb.add("f3")
        def _(event):
            """Toggle log window with F3"""
            self.show_log_window = not self.show_log_window
            event.app.invalidate()  # Force redraw

        @kb.add("c-q")
        def _(event):
            """Exit with Ctrl-Q"""
            event.app.exit()

        # Ensure numchuck directories exist
        ensure_numchuck_directories()

        # Prompt continuation for multiline input
        def get_continuation(width, line_number, is_soft_wrap):
            return "... " if line_number > 0 else ""

        # Smart multiline filter - determines if we should stay in multiline mode
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.application import get_app

        @Condition
        def should_continue_multiline():
            if not self.smart_enter:
                return True  # Always multiline, require Esc+Enter/Ctrl+Enter

            # Get current buffer text
            app = get_app()
            text = app.current_buffer.text

            # If there's already a newline, we're in multiline mode
            if "\n" in text:
                return True

            # Single line - check if it's a REPL command
            text_stripped = text.strip()
            if not text_stripped:
                return False

            # Known single-line commands should submit on Enter
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
            ]
            if text_stripped in single_line_cmds:
                return False  # Don't continue, accept on Enter

            # Patterns that start REPL commands
            if text_stripped.startswith(
                ("+", "-", "~", "?", ":", "!", "$", "@", "edit")
            ):
                return False  # REPL command, accept on Enter

            # If it contains ChucK code markers, stay multiline
            if any(marker in text_stripped for marker in ["=>", ";", "{"]):
                return True  # Likely ChucK code, require Esc+Enter

            # Default: single-line input without ChucK markers, accept on Enter
            return False

        # Create input buffer
        self.input_buffer = Buffer(
            history=FileHistory(str(get_history_file())),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            complete_while_typing=False,
            multiline=should_continue_multiline,
            on_text_insert=lambda _: None,  # Could be used for live updates
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

        # Create main input window with prompt
        def get_prompt_text():
            prompt_html = HTML(
                "<prompt-bracket>[</prompt-bracket><prompt-chuck>=></prompt-chuck><prompt-bracket>]</prompt-bracket> "
            )
            return prompt_html

        input_window = Window(
            content=BufferControl(
                buffer=self.input_buffer,
                lexer=PygmentsLexer(lexer_class),
                include_default_input_processors=True,
            ),
            get_line_prefix=lambda line_number, wrap_count: get_continuation(
                0, line_number, False
            )
            if line_number > 0
            else get_prompt_text(),
            wrap_lines=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

        # Create error bar window (conditional)
        @Condition
        def error_visible():
            return bool(self.error_message)

        error_window = ConditionalContainer(
            Window(
                height=D.exact(1),
                content=FormattedTextControl(text=get_error_text),
                style="class:error-toolbar",
            ),
            filter=error_visible,
        )

        # Create help window (conditional)
        @Condition
        def help_visible():
            return self.show_help_window

        help_window = ConditionalContainer(self.help_area, filter=help_visible)

        # Create shreds table window (conditional)
        @Condition
        def shreds_visible():
            return self.show_shreds_window

        shreds_window = ConditionalContainer(self.shreds_area, filter=shreds_visible)

        # Create log window (conditional)
        @Condition
        def log_visible():
            return self.show_log_window

        log_window = ConditionalContainer(self.log_area, filter=log_visible)

        # Create layout with top toolbar (shreds) and bottom toolbar (status)
        root_container = HSplit(
            [
                topbar_window,  # Top: shows active shreds (IDs only)
                Window(height=D.exact(1)),  # Gap between topbar and input
                input_window,  # Middle: REPL input
                error_window,  # Error bar (only shown when there's an error)
                help_window,  # Help window (toggle with F1)
                shreds_window,  # Shreds table window (toggle with F2)
                log_window,  # Log window (toggle with F3)
                Window(
                    height=D.exact(1),
                    content=FormattedTextControl(text=get_bottom_toolbar),
                    style="class:bottom-toolbar",
                ),  # Bottom: VM status
            ]
        )

        # Create application
        self.app: Any = Application(
            layout=Layout(root_container),
            key_bindings=kb,
            style=repl_style,
            full_screen=True,
            mouse_support=True,  # Enable mouse for scrolling
        )

        self.prompt_html = HTML  # Store HTML class for later use

    def add_to_log(self, msg: str) -> None:
        """Capture ChucK VM messages to log window.

        Args:
            msg: Message to add to log
        """
        msg = msg.rstrip("\n")
        if msg:
            self.log_lines.append(msg)
            # Keep only recent messages
            if len(self.log_lines) > self.max_log_lines:
                self.log_lines.pop(0)
            # Update the log area
            self.log_area.text = "\n".join(self.log_lines)
            # Scroll to bottom
            self.log_area.buffer.cursor_position = len(self.log_area.text)
            self.app.invalidate()

    def setup(self) -> None:
        """Initialize ChucK with sensible defaults."""
        from .._numchuck import ChucK as ChucKClass

        # Use ChucK's stdout callback to capture VM messages (must be set before init)
        ChucKClass.set_stdout_callback(self.add_to_log)
        ChucKClass.set_stderr_callback(self.add_to_log)

        # Initialize ChucK through app_state
        self.app_state.setup()

        # Set up output capture with our log function
        self.app_state.set_log_callback(lambda msg: self.add_to_log(f"[out] {msg}"))
        self.app_state.setup_output_capture()

    def process_input(self, buff: Buffer) -> bool:
        """Process input when user presses Enter.

        Args:
            buff: Input buffer containing user text

        Returns:
            True to clear the buffer after processing
        """
        text = buff.text.strip()

        # Clear previous error
        self.error_message = ""

        if not text:
            return True

        if text in ["quit", "exit", "q"]:
            self.app.exit()
            return True

        if text == "help":
            self.show_help_window = not self.show_help_window
            self.app.invalidate()
            return True

        # Parse and execute
        cmd = self.parser.parse(text)
        if cmd:
            # Only print newline for commands that produce output
            # Silent commands: audio start/stop, shred add/remove
            silent_cmds = [
                "start_audio",
                "stop_audio",
                "shutdown_audio",
                "spork_file",
                "spork_code",
                "remove_shred",
                "remove_all",
                "edit_shred",
            ]
            if cmd.type not in silent_cmds:
                print()  # newline for output
            # Execute command and get error if any
            error = self.executor.execute(cmd)
            if error:
                self.error_message = error
        else:
            # If not a recognized command, treat as ChucK code
            # Check if it looks like ChucK code (contains =>, ;, or multiline)
            if "\n" in text or "=>" in text or ";" in text or "{" in text:
                # Use ShredService for code compilation
                result = self.app_state.shred_service.spork_code(text, name="repl")
                if not result.success:
                    self.error_message = result.error or "Failed to compile code"
            else:
                # Not a recognized command and doesn't look like ChucK code
                self.error_message = f"Unknown command: {text}"

        # Force redraw to update topbar/toolbar/error
        self.app.invalidate()
        return True

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

            # Set accept handler for buffer
            self.input_buffer.accept_handler = self.process_input

            # Run the application
            self.app.run()

        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Shutdown cleanly."""
        import gc

        print("\nShutting down...")

        # Clear convenience references FIRST (before app_state.cleanup closes ChucK)
        self.chuck = None  # type: ignore[assignment]
        self.session = None  # type: ignore[assignment]

        # Break completer references (it holds chuck and session)
        if hasattr(self, "completer") and self.completer is not None:
            self.completer.chuck = None  # type: ignore[assignment]
            self.completer.session = None  # type: ignore[assignment]
            self.completer = None  # type: ignore[assignment]

        # Break executor references
        if hasattr(self, "executor") and self.executor is not None:
            self.executor._chuck = None  # type: ignore[assignment]
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
