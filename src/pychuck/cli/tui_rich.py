"""
ChucK REPL with Textual rich TUI

Improved version with:
- External CSS file for styling
- File browser sidebar for .ck files
- Tree widgets for shreds and globals
- Better reactive UI updates
- Cleaner code organization
"""

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, RichLog, Tree, DirectoryTree, Label
from textual.widget import Widget
from textual.binding import Binding
from textual.reactive import reactive, var
from rich.text import Text

from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
)
import sys
import os

from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor

# Get the absolute path to the CSS file
_CSS_FILE = Path(__file__).parent / "tui_rich.tcss"


class FileSidebar(Widget):
    """Animated sidebar for browsing .ck files"""

    def compose(self) -> ComposeResult:
        """Compose sidebar contents"""
        path = os.getcwd()
        yield Label("ChucK Files (.ck)", classes="panel-title")
        yield DirectoryTree(path, id="file-tree")


class ChuckTUI(App):
    """ChucK REPL with rich TUI - Improved version"""

    # TEMPORARILY DISABLED - Debug CSS loading issue
    # CSS_PATH = str(_CSS_FILE)

    # Disable mouse until we debug the blank screen issue
    ENABLE_COMMAND_PALETTE = False

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+l", "clear_console", "Clear", show=True),
        Binding("ctrl+s", "toggle_audio", "Audio", show=True),
        Binding("ctrl+r", "remove_all", "Clear VM", show=True),
        Binding("ctrl+f", "toggle_files", "Files", show=True),
        Binding("ctrl+u", "refresh_ui", "Refresh", show=False),
        ("escape", "focus_input", "Focus input"),
    ]

    TITLE = "ChucK REPL"

    # Reactive properties - TEMPORARILY DISABLED FOR DEBUG
    # audio_running = reactive(False)
    # show_files = var(False)
    # shred_count = reactive(0)

    def __init__(self):
        import sys
        print("DEBUG: ChuckTUI.__init__ called", file=sys.stderr)
        super().__init__()
        print("DEBUG: super().__init__() complete", file=sys.stderr)
        self.chuck = None
        self.session = None
        print("DEBUG: about to create CommandParser", file=sys.stderr)
        self.parser = CommandParser()
        print("DEBUG: CommandParser created", file=sys.stderr)
        self.executor = None
        self._cleaned_up = False
        # Initialize non-reactive versions
        self.audio_running = False
        self.show_files = False
        self.shred_count = 0
        print("DEBUG: ChuckTUI.__init__ complete", file=sys.stderr)

    # Removed mouse_enabled property - use mouse=False in run() instead

    def watch_show_files(self, show_files: bool) -> None:
        """Called when show_files changes"""
        # DISABLED - sidebar not present
        # sidebar = self.query_one("#file-sidebar", FileSidebar)
        # sidebar.set_class(show_files, "-visible")
        pass

    def watch_shred_count(self, count: int) -> None:
        """Update subtitle when shred count changes"""
        self.sub_title = f"Shreds: {count} | Audio: {'ON' if self.audio_running else 'OFF'}"

    def watch_audio_running(self, running: bool) -> None:
        """Update subtitle when audio status changes"""
        self.sub_title = f"Shreds: {self.shred_count} | Audio: {'ON' if running else 'OFF'}"

    def compose(self) -> ComposeResult:
        """Compose UI"""
        import sys
        print("DEBUG: compose() called", file=sys.stderr)

        try:
            yield Header()
            print("DEBUG: Header yielded", file=sys.stderr)

            # File browser sidebar - TEMPORARILY DISABLED FOR DEBUG
            # yield FileSidebar(id="file-sidebar")
            # print("DEBUG: FileSidebar yielded", file=sys.stderr)

            # Main container
            with Container(id="main-container"):
                # Console on left
                with Vertical(id="console"):
                    yield Label("Console Output", classes="panel-title")
                    yield RichLog(id="log", highlight=True, markup=True, wrap=True)

                # Right panel with shreds and globals
                with Vertical(id="right-panel"):
                    # Shreds panel
                    with ScrollableContainer(id="shred-panel"):
                        yield Label("Running Shreds", classes="panel-title")
                        yield Tree("Shreds", id="shred-tree")

                    # Globals panel
                    with ScrollableContainer(id="globals-panel"):
                        yield Label("Global Variables", classes="panel-title")
                        yield Tree("Globals", id="globals-tree")

                # Input at bottom
                with Container(id="input-container"):
                    yield Input(placeholder="Enter ChucK command (type 'help' for commands)...", id="cmd-input")

            print("DEBUG: Main container complete", file=sys.stderr)

            yield Footer()
            print("DEBUG: Footer yielded", file=sys.stderr)

        except Exception as e:
            print(f"DEBUG: Exception in compose(): {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise

    async def on_mount(self) -> None:
        """Setup ChucK and callbacks"""
        import sys

        # Debug: print to stderr to see if this is even called
        print("DEBUG: on_mount called", file=sys.stderr)

        log = self.query_one("#log", RichLog)
        print("DEBUG: got log widget", file=sys.stderr)

        try:
            # Initialize ChucK
            log.write("[dim]Initializing ChucK...[/dim]")
            print("DEBUG: wrote initial message", file=sys.stderr)

            self.chuck = ChucK()
            print("DEBUG: ChucK() created", file=sys.stderr)

            self.session = REPLSession(self.chuck)
            self.executor = CommandExecutor(self.session)
            print("DEBUG: session and executor created", file=sys.stderr)

            self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
            self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
            self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
            print("DEBUG: params set", file=sys.stderr)

            self.chuck.init()
            print("DEBUG: chuck.init() called", file=sys.stderr)

            # Capture ChucK output
            self.chuck.set_chout_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[cyan][chout][/cyan] {msg}", end='')
            ))
            self.chuck.set_cherr_callback(lambda msg: self.call_from_thread(
                lambda: log.write(f"[red][cherr][/red] {msg}", end='')
            ))
            print("DEBUG: callbacks set", file=sys.stderr)

            # Welcome message
            log.write("[bold green]ChucK REPL v0.1.0[/bold green]")
            log.write("[dim]Type 'help' for commands. Ctrl+C to quit. Ctrl+F for file browser.[/dim]\n")
            print("DEBUG: welcome message written", file=sys.stderr)
        except Exception as e:
            print(f"DEBUG: Exception during init: {e}", file=sys.stderr)
            log.write(f"[bold red]Error initializing ChucK:[/bold red] {e}")
            import traceback
            log.write(f"[dim]{traceback.format_exc()}[/dim]")
            traceback.print_exc()

        # Focus input
        print("DEBUG: focusing input", file=sys.stderr)
        self.query_one("#cmd-input", Input).focus()

        # Initialize trees
        shred_tree = self.query_one("#shred-tree", Tree)
        shred_tree.show_root = False

        globals_tree = self.query_one("#globals-tree", Tree)
        globals_tree.show_root = False
        print("DEBUG: trees initialized", file=sys.stderr)

        # Initial UI update
        if self.chuck:
            print("DEBUG: calling refresh_ui_sync", file=sys.stderr)
            self.refresh_ui_sync()

        print("DEBUG: on_mount complete", file=sys.stderr)

    async def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection from tree (keyboard navigation)"""
        # Note: This works with keyboard (Enter key) even with mouse disabled
        file_path = str(event.path)
        if file_path.endswith('.ck'):
            # Auto-fill input with + command
            cmd_input = self.query_one("#cmd-input", Input)
            cmd_input.value = f"+ {file_path}"
            cmd_input.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input"""
        text = event.value.strip()
        event.input.value = ""

        if not text:
            return

        log = self.query_one("#log", RichLog)
        log.write(f"[bold]chuck>[/bold] {text}")

        # Check if ChucK is initialized
        if not self.chuck or not self.executor:
            log.write("[yellow]ChucK not initialized yet[/yellow]")
            return

        # Special commands
        if text in ['quit', 'exit', 'q']:
            self.action_quit()
            return

        if text == 'help':
            self.show_help()
            return

        # Parse and execute
        try:
            cmd = self.parser.parse(text)
            if cmd:
                # Execute and update UI
                self._execute_with_output(cmd)

                # Update UI for commands that affect state
                if cmd.type in ['spork_file', 'spork_code', 'remove_shred', 'remove_all',
                               'clear_vm', 'start_audio', 'stop_audio', 'shutdown_audio',
                               'set_global', 'get_global']:
                    self.refresh_ui_sync()
        except Exception as e:
            log.write(f"[bold red]Error:[/bold red] {e}")
            import traceback
            log.write(f"[dim]{traceback.format_exc()}[/dim]")

    def _execute_with_output(self, cmd):
        """Execute command and capture output"""
        log = self.query_one("#log", RichLog)

        # Redirect print to log
        import io
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        try:
            self.executor.execute(cmd)
            stdout_output = sys.stdout.getvalue()
            stderr_output = sys.stderr.getvalue()

            if stdout_output:
                log.write(stdout_output.rstrip())
            if stderr_output:
                log.write(f"[red]{stderr_output.rstrip()}[/red]")

            # Update audio status if needed
            if cmd.type in ['start_audio', 'stop_audio', 'shutdown_audio']:
                self.audio_running = self.session.audio_running
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def refresh_ui_sync(self):
        """Refresh UI - update shred and globals trees"""
        if not self.chuck or not self.session:
            return

        try:
            # Update shreds tree
            shred_tree = self.query_one("#shred-tree", Tree)
            shred_tree.clear()

            all_shreds = self.chuck.get_all_shred_ids()
            self.shred_count = len(all_shreds)

            for shred_id in all_shreds:
                try:
                    info = self.chuck.get_shred_info(shred_id)
                    if info:
                        node = shred_tree.root.add(f"Shred {shred_id}")
                        node.add_leaf(f"Name: {info.get('name', 'N/A')}")
                        node.add_leaf(f"Start: {info.get('start', 'N/A')}")
                except:
                    shred_tree.root.add_leaf(f"Shred {shred_id}")

            # Update globals tree
            globals_tree = self.query_one("#globals-tree", Tree)
            globals_tree.clear()

            try:
                globals_list = self.chuck.get_all_globals()
                if globals_list:
                    for global_var in globals_list:
                        globals_tree.root.add_leaf(str(global_var))
            except:
                pass  # Globals may not be available

        except Exception as e:
            pass  # Silent failure for UI updates

    def show_help(self):
        """Display help in console"""
        log = self.query_one("#log", RichLog)
        log.write("""
[bold cyan]ChucK REPL Commands:[/bold cyan]

[bold]Shred Management:[/bold]
  [cyan]+[/cyan] <file.ck>           Spork file
  [cyan]+[/cyan] "<code>"            Spork code
  [cyan]-[/cyan] <id>                Remove shred
  [cyan]-[/cyan] all                 Remove all shreds
  [cyan]~[/cyan] <id> "<code>"       Replace shred

[bold]Status:[/bold]
  [cyan]?[/cyan]                     List shreds
  [cyan]?[/cyan] <id>                Show shred info
  [cyan]?g[/cyan]                    List globals
  [cyan]?a[/cyan]                    Audio info
  [cyan].[/cyan]                     Current time

[bold]Globals:[/bold]
  <name>::<value>       Set global
  <name>?               Get global (async)

[bold]Events:[/bold]
  <event>!              Signal event
  <event>!!             Broadcast event

[bold]Audio:[/bold]
  [cyan]>[/cyan]                     Start audio
  [cyan]||[/cyan]                    Stop audio
  [cyan]X[/cyan]                     Shutdown audio

[bold]VM:[/bold]
  clear                 Clear VM
  reset                 Reset shred ID

[bold]Other:[/bold]
  : <file>              Compile only
  ! "<code>"            Execute immediately
  $ <cmd>               Shell command
  help                  Show this help
  quit                  Exit

[bold]Keybindings:[/bold]
  Ctrl+C                Quit
  Ctrl+L                Clear console
  Ctrl+S                Toggle audio
  Ctrl+R                Remove all shreds
  Ctrl+F                Toggle file browser (keyboard nav only)
  Escape                Focus input
  Tab                   Cycle through widgets
  Arrow keys            Navigate in file tree
""")

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
        """Quit application with proper cleanup"""
        self._cleanup()
        self.exit()

    def action_clear_console(self) -> None:
        """Clear console"""
        self.query_one("#log", RichLog).clear()

    def action_toggle_audio(self) -> None:
        """Toggle audio on/off"""
        log = self.query_one("#log", RichLog)
        if self.audio_running:
            try:
                stop_audio()
                self.audio_running = False
                self.session.audio_running = False
                log.write("[yellow]Audio stopped[/yellow]")
            except Exception as e:
                log.write(f"[red]Error stopping audio: {e}[/red]")
        else:
            try:
                start_audio(self.chuck)
                self.audio_running = True
                self.session.audio_running = True
                log.write("[green]Audio started[/green]")
            except Exception as e:
                log.write(f"[red]Error starting audio: {e}[/red]")

    def action_remove_all(self) -> None:
        """Remove all shreds"""
        if not self.chuck or not self.session:
            return
        self.chuck.remove_all_shreds()
        self.session.clear_shreds()
        self.query_one("#log", RichLog).write("[yellow]All shreds removed[/yellow]")
        self.refresh_ui_sync()

    def action_toggle_files(self) -> None:
        """Toggle file browser sidebar"""
        self.show_files = not self.show_files

    def action_refresh_ui(self) -> None:
        """Manually refresh UI"""
        self.refresh_ui_sync()

    def action_focus_input(self) -> None:
        """Focus command input"""
        self.query_one("#cmd-input", Input).focus()
