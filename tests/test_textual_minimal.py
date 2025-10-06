#!/usr/bin/env python3
"""
Test to reproduce the pychuck TUI structure - incrementally add complexity
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Input, RichLog
from textual.containers import Container, Vertical
from textual.binding import Binding

class TestApp(App):
    """Test app mimicking pychuck TUI structure"""

    ENABLE_COMMAND_PALETTE = False
    TITLE = "Test TUI"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Compose UI - step by step"""
        yield Header()

        with Container(id="main-container"):
            with Vertical(id="console"):
                yield Static("Console Output", classes="panel-title")
                yield RichLog(id="log", highlight=True, markup=True, wrap=True)

            with Container(id="input-container"):
                yield Input(placeholder="Enter command...", id="cmd-input")

        yield Footer()

    async def on_mount(self) -> None:
        """Setup"""
        log = self.query_one("#log", RichLog)
        log.write("[bold green]Test TUI v0.1.0[/bold green]")
        log.write("[dim]Type something and press Enter. Ctrl+C to quit.[/dim]\n")
        self.query_one("#cmd-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input"""
        text = event.value.strip()
        event.input.value = ""

        if not text:
            return

        log = self.query_one("#log", RichLog)
        log.write(f"[bold]you>[/bold] {text}")

        if text in ['quit', 'exit', 'q']:
            self.action_quit()

if __name__ == "__main__":
    app = TestApp()
    try:
        app.run(mouse=False)
    except KeyboardInterrupt:
        print("\nExited cleanly")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
