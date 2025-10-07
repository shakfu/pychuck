"""
ChucK live coding editor with project versioning.

Features:
- Multi-tab editing
- F5 to spork (compile and run)
- F6 to replace running shred
- Project-based versioning (file.ck → file-1.ck → file-1-1.ck)
- Tab names show shred IDs
"""
from pathlib import Path

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.layout.dimension import Dimension as D

from .common import ChuckApplication


class EditorTab:
    """Represents a single file being edited."""

    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else None
        self.modified = False
        self.shred_id = None  # Set when sporked

        # Load content
        if self.file_path and self.file_path.exists():
            content = self.file_path.read_text()
        else:
            content = "// New ChucK file\n"

        # Try to load ChucK lexer
        try:
            from .chuck_lexer import ChuckLexer
            lexer = PygmentsLexer(ChuckLexer)
        except ImportError:
            from pygments.lexers.c_cpp import CLexer
            lexer = PygmentsLexer(CLexer)

        # Create text area
        self.text_area = TextArea(
            text=content,
            multiline=True,
            scrollbar=True,
            lexer=lexer,
            wrap_lines=False
        )

        # Track modifications
        def on_change(_):
            self.modified = True
        self.text_area.buffer.on_text_changed += on_change

    @property
    def display_name(self):
        """Tab display name with shred ID and modified indicator."""
        if self.file_path:
            name = self.file_path.name
        else:
            name = "untitled.ck"

        # Add shred ID if sporked
        if self.shred_id is not None:
            # Remove .ck extension and add shred ID
            base = name.rsplit('.', 1)[0]
            ext = name.rsplit('.', 1)[1] if '.' in name else 'ck'
            name = f"{base}-{self.shred_id}.{ext}"

        # Add modified indicator
        if self.modified:
            name += "*"

        return name

    @property
    def content(self):
        """Get current buffer content."""
        return self.text_area.text

    @content.setter
    def content(self, value):
        """Set buffer content and mark as unmodified."""
        self.text_area.text = value
        self.modified = False


class ChuckEditor:
    """Multi-tab editor with project versioning."""

    def __init__(self, project_name=None, start_audio=False):
        self.app_state = ChuckApplication(project_name=project_name)
        self.tabs = []
        self.current_tab_index = 0
        self.start_audio_flag = start_audio
        self.audio_started = False
        self.status_message = ""

        # Initialize ChucK
        from .. import PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
        self.app_state.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.app_state.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.app_state.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.app_state.chuck.init()

        # Create application
        self.app = None

    def create_key_bindings(self):
        """Create editor key bindings."""
        kb = self.app_state.get_common_key_bindings()

        @kb.add('c-o')
        def open_file(event):
            """Open file (Ctrl-O)"""
            self._show_open_file_dialog()

        @kb.add('c-s')
        def save_file(event):
            """Save current file (Ctrl-S)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]
            if tab.file_path:
                try:
                    tab.file_path.write_text(tab.content)
                    tab.modified = False
                    self.status_message = f"Saved {tab.file_path.name}"
                except Exception as e:
                    self.status_message = f"Save failed: {e}"
            else:
                self.status_message = "No filename (will auto-save on spork)"
            event.app.invalidate()

        @kb.add('f5')
        @kb.add('c-r')
        def spork_code(event):
            """Spork current buffer (F5 or Ctrl-R)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]
            success, shred_ids = self.app_state.chuck.compile_code(tab.content)

            if success and shred_ids:
                shred_id = shred_ids[0]
                tab.shred_id = shred_id

                # Save to project with versioning
                filename = tab.file_path.name if tab.file_path else "untitled.ck"
                self.app_state.session.add_shred(
                    shred_id,
                    filename,
                    content=tab.content,
                    shred_type='file' if tab.file_path else 'code'
                )

                self.status_message = f"Sporked shred {shred_id}"
                tab.modified = False
            else:
                self.status_message = "Compilation failed"
            event.app.invalidate()

        @kb.add('f6')
        def replace_shred(event):
            """Replace existing shred (F6)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]

            if tab.shred_id is None:
                self.status_message = "No shred to replace (F5 to spork first)"
                event.app.invalidate()
                return

            try:
                old_id = tab.shred_id
                new_id = self.app_state.chuck.replace_shred(old_id, tab.content)

                if new_id > 0:
                    # Save replacement version to project
                    if self.app_state.session.project:
                        self.app_state.session.replace_shred(old_id, tab.content)

                    # Update session tracking
                    self.app_state.session.shreds.pop(old_id, None)
                    filename = tab.file_path.name if tab.file_path else "untitled.ck"
                    self.app_state.session.add_shred(
                        new_id,
                        filename,
                        content=tab.content,
                        shred_type='file' if tab.file_path else 'code'
                    )

                    tab.shred_id = new_id
                    tab.modified = False

                    self.status_message = f"Replaced {old_id} → {new_id}"
                else:
                    self.status_message = "Replace failed"
            except Exception as e:
                self.status_message = f"Replace failed: {e}"
            event.app.invalidate()

        @kb.add('c-t')
        def new_tab(event):
            """New tab (Ctrl-T)"""
            self.add_tab()
            event.app.invalidate()

        @kb.add('c-w')
        def close_tab(event):
            """Close tab (Ctrl-W)"""
            if len(self.tabs) > 1:
                self.tabs.pop(self.current_tab_index)
                self.current_tab_index = min(self.current_tab_index, len(self.tabs) - 1)
                event.app.invalidate()

        @kb.add('c-pagedown')
        @kb.add('c-n')
        def next_tab(event):
            """Next tab (Ctrl-PageDown or Ctrl-N)"""
            if len(self.tabs) > 1:
                self.current_tab_index = (self.current_tab_index + 1) % len(self.tabs)
                event.app.invalidate()

        @kb.add('c-pageup')
        @kb.add('c-p')
        def prev_tab(event):
            """Previous tab (Ctrl-PageUp or Ctrl-P)"""
            if len(self.tabs) > 1:
                self.current_tab_index = (self.current_tab_index - 1) % len(self.tabs)
                event.app.invalidate()

        @kb.add('c-a')
        def start_audio(event):
            """Start audio (Ctrl-A)"""
            if not self.audio_started:
                try:
                    from .. import start_audio
                    start_audio(self.app_state.chuck)
                    self.audio_started = True
                    self.status_message = "Audio started"
                except Exception as e:
                    self.status_message = f"Audio start failed: {e}"
                event.app.invalidate()

        return kb

    def _show_open_file_dialog(self):
        """Show a dialog to open a file with tab completion."""
        from prompt_toolkit.completion import PathCompleter
        from prompt_toolkit.layout.containers import Float, HSplit, Window
        from prompt_toolkit.layout.controls import BufferControl
        from prompt_toolkit.widgets import Button, Dialog, Label
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.key_binding import KeyBindings

        # Create buffer with path completion
        input_buffer = Buffer(
            completer=PathCompleter(
                expanduser=True,
                # Don't filter by .ck - let user see all files/dirs
            ),
            complete_while_typing=False,  # Only complete on Tab
            multiline=False
        )

        # Define handlers first
        def ok_handler():
            file_path = input_buffer.text.strip()
            if self.app.layout.container.floats:
                self.app.layout.container.floats.pop()  # Remove dialog

            # Process the file path
            if file_path:
                path = Path(file_path).expanduser()
                if path.exists():
                    self.add_tab(str(path))
                    self.status_message = f"Opened {path.name}"
                else:
                    self.status_message = f"File not found: {file_path}"
            else:
                self.status_message = "Open cancelled"

            self.app.invalidate()

        def cancel_handler():
            if self.app.layout.container.floats:
                self.app.layout.container.floats.pop()  # Remove dialog
            self.status_message = "Open cancelled"
            self.app.invalidate()

        # Create custom key bindings for the input buffer
        input_kb = KeyBindings()

        @input_kb.add('tab')
        def _(event):
            """Trigger completion on Tab - insert common prefix or cycle"""
            b = event.app.current_buffer
            if b.complete_state:
                # Already showing completions, cycle to next
                b.complete_next()
            else:
                # Start completion and insert common prefix if any
                b.start_completion(insert_common_part=True, select_first=False)

        @input_kb.add('s-tab')
        def _(event):
            """Previous completion on Shift-Tab"""
            b = event.app.current_buffer
            if b.complete_state:
                b.complete_previous()

        @input_kb.add('enter')
        def _(event):
            """Accept completion or submit"""
            b = event.app.current_buffer
            if b.complete_state:
                # Accept the current completion
                b.complete_state = None
            else:
                # Submit the form
                ok_handler()

        @input_kb.add('escape')
        def _(event):
            """Cancel dialog"""
            cancel_handler()

        # Create window with buffer control and completions menu
        from prompt_toolkit.layout.menus import CompletionsMenu
        from prompt_toolkit.layout.containers import FloatContainer, VSplit

        input_control = BufferControl(
            buffer=input_buffer,
            key_bindings=input_kb,
            focus_on_click=True
        )

        input_window = Window(
            content=input_control,
            height=1,
            dont_extend_height=True
        )

        # Create dialog body with completions support
        dialog_body = FloatContainer(
            content=HSplit([
                Label(text='File path (Tab to complete, Enter to open, Esc to cancel):'),
                input_window,
            ]),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=10)
                )
            ]
        )

        # Create dialog
        dialog = Dialog(
            title='Open File',
            body=dialog_body,
            buttons=[
                Button(text='OK', handler=ok_handler),
                Button(text='Cancel', handler=cancel_handler),
            ],
            width=70,
            modal=True
        )

        # Add as floating window
        float_container = Float(content=dialog)
        self.app.layout.container.floats.append(float_container)

        # Focus the input buffer
        self.app.layout.focus(input_window)
        self.app.invalidate()

    def add_tab(self, file_path=None):
        """Add new tab."""
        tab = EditorTab(file_path)
        self.tabs.append(tab)
        self.current_tab_index = len(self.tabs) - 1

        # Set focus to the new tab's text area if app is running
        if self.app:
            self.app.layout.focus(tab.text_area)

    def create_tab_bar(self):
        """Create tab bar showing all open tabs."""
        def get_text():
            if not self.tabs:
                return ""

            parts = []
            for i, tab in enumerate(self.tabs):
                name = tab.display_name
                if i == self.current_tab_index:
                    # Current tab - highlighted
                    parts.append(f" [{name}] ")
                else:
                    # Other tabs
                    parts.append(f"  {name}  ")
            return "".join(parts)

        return Window(
            content=FormattedTextControl(get_text),
            height=1,
            style='bg:#3366cc fg:#ffffff'
        )

    def create_layout(self):
        """Create editor layout."""
        if not self.tabs:
            self.add_tab()

        # Use a dynamic container that updates based on current_tab_index
        from prompt_toolkit.layout.containers import DynamicContainer, FloatContainer

        def get_current_editor():
            if self.tabs and 0 <= self.current_tab_index < len(self.tabs):
                return self.tabs[self.current_tab_index].text_area
            return Window()  # Fallback empty window

        # Main content
        root_container = HSplit([
            self.create_tab_bar(),
            DynamicContainer(get_current_editor),
            self.app_state.create_help_window(self.get_help_text()),
            self.app_state.create_shreds_table(),
            self.app_state.create_log_window(),
            self.app_state.create_status_bar(lambda: self.get_status_text())
        ])

        # Wrap in FloatContainer to support floating dialogs
        return FloatContainer(
            content=root_container,
            floats=[]
        )

    def get_help_text(self):
        """Get help text for F1 window."""
        project_info = (
            f"Project: {self.app_state.session.project.name}"
            if self.app_state.session.project
            else "No project (use: pychuck edit --project <name>)"
        )

        project_dir = (
            str(self.app_state.session.project.project_dir)
            if self.app_state.session.project
            else "N/A"
        )

        return f"""ChucK Editor - {project_info}

AUDIO & EXECUTION
  F5 / Ctrl-R     Spork current buffer (compile and run)
  F6              Replace existing shred with current buffer
  Ctrl-A          Start audio

FILE OPERATIONS
  Ctrl-O          Open file
  Ctrl-S          Save file
  Ctrl-T          New tab
  Ctrl-W          Close tab
  Ctrl-N          Next tab
  Ctrl-P          Previous tab

UI
  F1              Toggle this help
  F2              Toggle shreds table
  F3              Toggle log window
  Ctrl-Q          Exit editor

PROJECT VERSIONING
Files saved to: {project_dir}
Versioning: file.ck → file-1.ck (spork) → file-1-1.ck (replace)
"""

    def get_status_text(self):
        """Get status bar text."""
        # Shred count
        shred_count = len(self.app_state.session.shreds)
        audio_status = "♪" if self.audio_started else "⏸"

        # Current file info
        if self.tabs:
            tab = self.tabs[self.current_tab_index]
            file_info = tab.display_name
        else:
            file_info = "No tabs"

        return f" {audio_status} {shred_count} shreds | {file_info} | {self.status_message} | F1:Help "

    def cleanup(self):
        """Cleanup on exit."""
        # Stop audio if running
        if self.audio_started:
            try:
                from .. import stop_audio, shutdown_audio
                stop_audio()
                shutdown_audio(500)
            except:
                pass

        # Clean up app state (ChucK instance and session)
        self.app_state.cleanup()

        # Break circular references
        if hasattr(self, 'tabs'):
            for tab in self.tabs:
                if hasattr(tab, 'text_area'):
                    del tab.text_area
            self.tabs.clear()
            del self.tabs

        if hasattr(self, 'app_state'):
            del self.app_state

        if hasattr(self, 'app'):
            self.app = None

    def run(self, files=None):
        """Run editor."""
        # Load files or create empty tab
        if files:
            for f in files:
                self.add_tab(f)
        else:
            self.add_tab()

        # Start audio if requested
        if self.start_audio_flag:
            try:
                from .. import start_audio
                start_audio(self.app_state.chuck)
                self.audio_started = True
                self.status_message = "Audio started"
            except Exception as e:
                self.status_message = f"Audio start failed: {e}"

        # Create application
        self.app = Application(
            layout=Layout(self.create_layout()),
            key_bindings=self.create_key_bindings(),
            full_screen=True,
            mouse_support=True
        )

        try:
            self.app.run()
        finally:
            self.cleanup()


def main(files=None, project_name=None, start_audio=False):
    """Main entry point for editor."""
    editor = ChuckEditor(project_name=project_name, start_audio=start_audio)
    editor.run(files=files)


if __name__ == '__main__':
    main()
