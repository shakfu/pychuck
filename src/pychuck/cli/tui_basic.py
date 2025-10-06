"""
Ultra-basic ChucK TUI - no colors, no fancy features
For terminals with escape sequence issues
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Log, Static
from textual.containers import Container

from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
)
import sys

from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor


class ChuckBasicTUI(App):
    """Ultra-basic ChucK REPL TUI - no colors, minimal features"""

    # Minimal CSS - no colors
    CSS = """
    #log {
        height: 1fr;
        border: solid;
    }

    #input-area {
        height: 3;
        dock: bottom;
    }
    """

    TITLE = "ChucK REPL"

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_log", "Clear"),
    ]

    def __init__(self):
        super().__init__()
        self.chuck = None
        self.session = None
        self.parser = CommandParser()
        self.executor = None
        self._cleaned_up = False

    @property
    def mouse_enabled(self):
        """Disable mouse"""
        return False

    def compose(self) -> ComposeResult:
        """Simple layout - no colors"""
        yield Header()
        yield Log(id="log")  # Use Log instead of RichLog to avoid color codes
        with Container(id="input-area"):
            yield Input(placeholder="Enter ChucK command...", id="cmd-input")
        yield Footer()

    async def on_mount(self) -> None:
        """Setup ChucK"""
        log = self.query_one("#log", Log)

        try:
            log.write_line("Initializing ChucK...")
            self.chuck = ChucK()
            self.session = REPLSession(self.chuck)
            self.executor = CommandExecutor(self.session)

            self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
            self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
            self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
            self.chuck.init()

            # Capture output - no color codes
            self.chuck.set_chout_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[chout] {msg}")
            ))
            self.chuck.set_cherr_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[cherr] {msg}")
            ))

            log.write_line("ChucK REPL initialized")
            log.write_line("Type commands and press Enter. Ctrl+C to quit.")
            log.write_line("")
        except Exception as e:
            log.write_line(f"ERROR: {e}")
            import traceback
            log.write_line(traceback.format_exc())

        # Focus input
        self.query_one("#cmd-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command"""
        text = event.value.strip()
        event.input.value = ""

        if not text:
            return

        log = self.query_one("#log", Log)
        log.write_line(f"chuck> {text}")

        if not self.chuck or not self.executor:
            log.write_line("ChucK not initialized")
            return

        if text in ['quit', 'exit', 'q']:
            self.action_quit()
            return

        if text == 'help':
            log.write_line("Basic TUI - type ChucK commands")
            log.write_line("Ctrl+C to quit, Ctrl+L to clear")
            return

        try:
            cmd = self.parser.parse(text)
            if cmd:
                # Execute with output capture - no colors
                import io
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()

                try:
                    self.executor.execute(cmd)
                    stdout_out = sys.stdout.getvalue()
                    stderr_out = sys.stderr.getvalue()

                    if stdout_out:
                        for line in stdout_out.rstrip().split('\n'):
                            log.write_line(line)
                    if stderr_out:
                        for line in stderr_out.rstrip().split('\n'):
                            log.write_line(f"ERROR: {line}")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
        except Exception as e:
            log.write_line(f"ERROR: {e}")

    def _cleanup(self):
        """Cleanup ChucK resources"""
        if self._cleaned_up:
            return
        self._cleaned_up = True

        try:
            shutdown_audio(500)
        except:
            pass

        if hasattr(self, 'chuck') and self.chuck:
            try:
                self.chuck.remove_all_shreds()
            except:
                pass

        # Break circular references
        if hasattr(self, 'session') and self.session:
            self.session.chuck = None
            del self.session
        if hasattr(self, 'executor') and self.executor:
            self.executor.chuck = None
            self.executor.session = None
            del self.executor
        if hasattr(self, 'chuck') and self.chuck:
            del self.chuck

    def on_unmount(self) -> None:
        """Called when app is unmounting - cleanup here"""
        self._cleanup()

    def action_quit(self) -> None:
        """Quit with cleanup"""
        self._cleanup()
        self.exit()

    def action_clear_log(self) -> None:
        """Clear log"""
        self.query_one("#log", Log).clear()
