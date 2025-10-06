"""
Simplified ChucK TUI for debugging - no external CSS, minimal widgets
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, Input, RichLog
from textual.binding import Binding

from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
)
import sys

from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor


class ChuckSimpleTUI(App):
    """Simplified ChucK REPL TUI - for debugging"""

    # Inline CSS - keep it simple
    CSS = """
    #log {
        height: 1fr;
        border: solid green;
    }

    #input-area {
        height: 3;
        dock: bottom;
    }
    """

    TITLE = "ChucK REPL (Simple)"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_log", "Clear", show=True),
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
        """Simple layout"""
        yield Header()
        yield RichLog(id="log", highlight=True, markup=True)
        with Container(id="input-area"):
            yield Input(placeholder="Enter ChucK command...", id="cmd-input")
        yield Footer()

    async def on_mount(self) -> None:
        """Setup ChucK"""
        log = self.query_one("#log", RichLog)

        try:
            log.write("[dim]Initializing ChucK...[/dim]")
            self.chuck = ChucK()
            self.session = REPLSession(self.chuck)
            self.executor = CommandExecutor(self.session)

            self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
            self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
            self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
            self.chuck.init()

            # Capture output
            self.chuck.set_chout_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[cyan]{msg}[/cyan]", end='')
            ))
            self.chuck.set_cherr_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[red]{msg}[/red]", end='')
            ))

            log.write("[bold green]ChucK REPL (Simple)[/bold green]")
            log.write("[dim]Type commands and press Enter. Ctrl+C to quit.[/dim]\n")
        except Exception as e:
            log.write(f"[bold red]Error:[/bold red] {e}")
            import traceback
            log.write(f"[dim]{traceback.format_exc()}[/dim]")

        # Focus input
        self.query_one("#cmd-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command"""
        text = event.value.strip()
        event.input.value = ""

        if not text:
            return

        log = self.query_one("#log", RichLog)
        log.write(f"[bold]chuck>[/bold] {text}")

        if not self.chuck or not self.executor:
            log.write("[yellow]ChucK not initialized[/yellow]")
            return

        if text in ['quit', 'exit', 'q']:
            self.action_quit()
            return

        if text == 'help':
            log.write("[cyan]Simple TUI - just type ChucK commands[/cyan]")
            return

        try:
            cmd = self.parser.parse(text)
            if cmd:
                # Execute with output capture
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
                        log.write(stdout_out.rstrip())
                    if stderr_out:
                        log.write(f"[red]{stderr_out.rstrip()}[/red]")
                finally:
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
        except Exception as e:
            log.write(f"[bold red]Error:[/bold red] {e}")

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
        self.query_one("#log", RichLog).clear()
