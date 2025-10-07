"""
Shared TUI components for editor and REPL.

Provides base class with common functionality:
- ChucK instance management
- Session tracking
- Shared UI components (help, shreds table, log)
- Common key bindings
"""
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.filters import Condition
from prompt_toolkit.widgets import TextArea


class ChuckApplication:
    """Base application managing ChucK instance and shared state."""

    def __init__(self, project_name=None):
        from .. import ChucK
        from .session import ChuckSession

        self.chuck = ChucK()
        self.session = ChuckSession(self.chuck, project_name=project_name)

        # Shared UI state
        self.show_help = False
        self.show_shreds = False
        self.show_log = False

        # Log tracking
        self.log_messages = []

    def get_common_key_bindings(self):
        """Common key bindings shared across editor and REPL."""
        kb = KeyBindings()

        @kb.add('c-q')
        def exit_app(event):
            """Exit application"""
            event.app.exit()

        @kb.add('f1')
        def toggle_help(event):
            """Toggle help window"""
            self.show_help = not self.show_help
            event.app.invalidate()

        @kb.add('f2')
        def toggle_shreds(event):
            """Toggle shreds table"""
            self.show_shreds = not self.show_shreds
            event.app.invalidate()

        @kb.add('f3')
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
            wrap_lines=True
        )

        return ConditionalContainer(
            Window(
                content=help_area.control,
                height=D(min=10, max=30),
                wrap_lines=True
            ),
            filter=Condition(lambda: self.show_help)
        )

    def create_shreds_table(self):
        """Create shreds table that toggles with F2."""
        def get_text():
            if not self.session.shreds:
                return "No active shreds"

            lines = ["ID   | Name                                                    | Elapsed"]
            lines.append("-" * 78)

            # Get current VM time for elapsed calculation
            try:
                current_time = self.chuck.now()
            except:
                current_time = 0.0

            for sid, info in sorted(self.session.shreds.items()):
                # Extract parent folder + filename from path
                from pathlib import Path
                full_name = info['name']
                try:
                    path = Path(full_name)
                    # Show parent/filename if it's a path, otherwise just the name
                    if path.parent.name:
                        name = f"{path.parent.name}/{path.name}"
                    else:
                        name = path.name
                except:
                    name = full_name
                name = name[:56]  # Wider column for better readability

                # Calculate elapsed time in seconds
                spork_time = info.get('time', 0.0)
                elapsed_samples = current_time - spork_time
                # Get sample rate from ChucK (default 44100)
                try:
                    srate = self.chuck.get_param('SAMPLE_RATE')
                except:
                    srate = 44100
                elapsed_sec = elapsed_samples / srate if srate > 0 else 0.0

                lines.append(f"{sid:<5d} | {name:<56s} | {elapsed_sec:.1f}s")
            return "\n".join(lines)

        return ConditionalContainer(
            Window(
                content=FormattedTextControl(get_text),
                height=D(min=5, max=15)
            ),
            filter=Condition(lambda: self.show_shreds)
        )

    def create_log_window(self):
        """Create log window that toggles with F3."""
        log_area = TextArea(
            text="",
            scrollbar=True,
            focusable=False,
            read_only=True
        )

        def log_callback(msg):
            """Callback for ChucK output"""
            self.log_messages.append(msg)
            log_area.text += msg
            if len(self.log_messages) > 1000:
                # Trim old messages
                self.log_messages = self.log_messages[-500:]
                log_area.text = "".join(self.log_messages[-500:])

        # Set ChucK output callbacks
        self.chuck.set_chout_callback(log_callback)
        self.chuck.set_cherr_callback(log_callback)

        return ConditionalContainer(
            log_area,
            filter=Condition(lambda: self.show_log)
        )

    def create_status_bar(self, status_text_func):
        """Create status bar at bottom of screen."""
        return Window(
            content=FormattedTextControl(status_text_func),
            height=1,
            style='bg:#444444 fg:#ffffff'
        )

    def cleanup(self):
        """Cleanup ChucK resources."""
        try:
            self.chuck.remove_all_shreds()
        except:
            pass

        # Break circular references to allow proper garbage collection
        if hasattr(self, 'session'):
            self.session.chuck = None
            del self.session
        if hasattr(self, 'chuck'):
            del self.chuck
