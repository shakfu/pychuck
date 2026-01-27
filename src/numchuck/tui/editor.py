"""
ChucK live coding editor with project versioning.

Features:
- Multi-tab editing
- F5 to spork (compile and run)
- F6 to replace running shred
- Project-based versioning (file.ck -> file-1.ck -> file-1-1.ck)
- Tab names show shred IDs
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.containers import FloatContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.lexers import PygmentsLexer

from .common import ChuckApplication

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent


class EditorTab:
    """Represents a single file being edited."""

    def __init__(self, file_path: str | Path | None = None) -> None:
        """Initialize an editor tab.

        Args:
            file_path: Optional path to file to load
        """
        self.file_path: Path | None = Path(file_path) if file_path else None
        self.modified: bool = False
        self.shred_id: int | None = None  # Set when sporked

        # Load content
        if self.file_path and self.file_path.exists():
            content = self.file_path.read_text()
        else:
            content = "// New ChucK file\n"

        # Try to load ChucK lexer
        try:
            from ..lang import ChuckLexer

            lexer = PygmentsLexer(ChuckLexer)
        except ImportError:
            from pygments.lexers.c_cpp import CLexer

            lexer = PygmentsLexer(CLexer)

        # Create text area
        self.text_area = TextArea(
            text=content, multiline=True, scrollbar=True, lexer=lexer, wrap_lines=False
        )

        # Track modifications
        def on_change(_: Any) -> None:
            self.modified = True

        self.text_area.buffer.on_text_changed += on_change

    @property
    def display_name(self) -> str:
        """Tab display name with shred ID and modified indicator."""
        if self.file_path:
            name = self.file_path.name
        else:
            name = "untitled.ck"

        # Add shred ID if sporked
        if self.shred_id is not None:
            # Remove .ck extension and add shred ID
            base = name.rsplit(".", 1)[0]
            ext = name.rsplit(".", 1)[1] if "." in name else "ck"
            name = f"{base}-{self.shred_id}.{ext}"

        # Add modified indicator
        if self.modified:
            name += "*"

        return name

    @property
    def content(self) -> str:
        """Get current buffer content."""
        return self.text_area.text

    @content.setter
    def content(self, value: str) -> None:
        """Set buffer content and mark as unmodified."""
        self.text_area.text = value
        self.modified = False


class ChuckEditor:
    """Multi-tab editor with project versioning.

    Note on thread safety:
        The tabs list and current_tab_index are accessed from both key handlers
        and the rendering system (via DynamicContainer). This is safe because
        prompt_toolkit is single-threaded: key handlers, rendering, and all
        callbacks execute sequentially on the same event loop thread. The
        app.invalidate() call schedules a redraw but does not cause concurrent
        access.
    """

    def __init__(
        self, project_name: str | None = None, start_audio: bool = False
    ) -> None:
        """Initialize the editor.

        Args:
            project_name: Optional project name for versioning
            start_audio: Whether to start audio on launch
        """
        self.app_state = ChuckApplication(project_name=project_name, auto_init=True)
        self.tabs: list[EditorTab] = []
        self.current_tab_index: int = 0  # Safe: prompt_toolkit is single-threaded
        self.start_audio_flag = start_audio
        self.status_message = ""

        # Create application
        self.app: Application[None] | None = None

    def create_key_bindings(self) -> KeyBindings:
        """Create editor key bindings.

        Returns:
            KeyBindings with all editor shortcuts
        """
        kb = self.app_state.get_common_key_bindings()

        @kb.add("c-o")
        def open_file(event: KeyPressEvent) -> None:
            """Open file (Ctrl-O)"""
            self._show_open_file_dialog()

        @kb.add("c-s")
        def save_file(event: KeyPressEvent) -> None:
            """Save current file (Ctrl-S)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]
            if tab.file_path:
                try:
                    tab.file_path.write_text(tab.content)
                    tab.modified = False
                    self.status_message = f"Saved {tab.file_path.name}"
                except OSError as e:
                    self.status_message = f"Save failed: {e}"
            else:
                self.status_message = "No filename (will auto-save on spork)"
            event.app.invalidate()

        @kb.add("f5")
        @kb.add("c-r")
        def spork_code(event: KeyPressEvent) -> None:
            """Spork current buffer (F5 or Ctrl-R)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]
            filename = tab.file_path.name if tab.file_path else "untitled.ck"

            # Use ShredService for sporking
            result = self.app_state.shred_service.spork_code(
                tab.content,
                name=filename,
            )

            if result.success and result.shred_id is not None:
                tab.shred_id = result.shred_id
                self.status_message = f"Sporked shred {result.shred_id}"
                tab.modified = False
            else:
                self.status_message = result.error or "Compilation failed"
            event.app.invalidate()

        @kb.add("f6")
        def replace_shred(event: "KeyPressEvent") -> None:
            """Replace existing shred (F6)"""
            if not self.tabs:
                return

            tab = self.tabs[self.current_tab_index]

            if tab.shred_id is None:
                self.status_message = "No shred to replace (F5 to spork first)"
                event.app.invalidate()
                return

            old_id = tab.shred_id
            filename = tab.file_path.name if tab.file_path else "untitled.ck"

            # Use ShredService for replacing
            result = self.app_state.shred_service.replace_shred(
                old_id,
                tab.content,
                name=filename,
            )

            if result.success and result.shred_id is not None:
                tab.shred_id = result.shred_id
                tab.modified = False
                self.status_message = f"Replaced {old_id} -> {result.shred_id}"
            else:
                self.status_message = result.error or "Replace failed"
            event.app.invalidate()

        @kb.add("c-t")
        def new_tab(event: "KeyPressEvent") -> None:
            """New tab (Ctrl-T)"""
            self.add_tab()
            event.app.invalidate()

        @kb.add("c-w")
        def close_tab(event: "KeyPressEvent") -> None:
            """Close tab (Ctrl-W)"""
            if len(self.tabs) > 1:
                self.tabs.pop(self.current_tab_index)
                self.current_tab_index = min(self.current_tab_index, len(self.tabs) - 1)
                event.app.invalidate()

        @kb.add("c-pagedown")
        @kb.add("c-n")
        def next_tab(event: "KeyPressEvent") -> None:
            """Next tab (Ctrl-PageDown or Ctrl-N)"""
            if len(self.tabs) > 1:
                self.current_tab_index = (self.current_tab_index + 1) % len(self.tabs)
                event.app.invalidate()

        @kb.add("c-pageup")
        @kb.add("c-p")
        def prev_tab(event: "KeyPressEvent") -> None:
            """Previous tab (Ctrl-PageUp or Ctrl-P)"""
            if len(self.tabs) > 1:
                self.current_tab_index = (self.current_tab_index - 1) % len(self.tabs)
                event.app.invalidate()

        @kb.add("c-a")
        def start_audio_handler(event: "KeyPressEvent") -> None:
            """Start audio (Ctrl-A)"""
            if not self.app_state.audio_running:
                if self.app_state.start_audio_playback():
                    self.status_message = "Audio started"
                else:
                    self.status_message = "Audio start failed"
                event.app.invalidate()

        return kb

    def _show_open_file_dialog(self) -> None:
        """Show a dialog to open a file with tab completion."""
        from prompt_toolkit.completion import PathCompleter
        from prompt_toolkit.layout.containers import Float, HSplit, Window
        from prompt_toolkit.layout.controls import BufferControl
        from prompt_toolkit.widgets import Button, Dialog, Label
        from prompt_toolkit.buffer import Buffer

        # Create buffer with path completion
        input_buffer = Buffer(
            completer=PathCompleter(
                expanduser=True,
                # Don't filter by .ck - let user see all files/dirs
            ),
            complete_while_typing=False,  # Only complete on Tab
            multiline=False,
        )

        # Define handlers first
        def ok_handler() -> None:
            file_path = input_buffer.text.strip()
            if self.app:
                container = cast(FloatContainer, self.app.layout.container)
                if container.floats:
                    container.floats.pop()  # Remove dialog

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

            if self.app:
                self.app.invalidate()

        def cancel_handler() -> None:
            if self.app:
                container = cast(FloatContainer, self.app.layout.container)
                if container.floats:
                    container.floats.pop()  # Remove dialog
            self.status_message = "Open cancelled"
            if self.app:
                self.app.invalidate()

        # Create custom key bindings for the input buffer
        input_kb = KeyBindings()

        @input_kb.add("tab")
        def _(event: "KeyPressEvent") -> None:
            """Trigger completion on Tab - insert common prefix or cycle"""
            b = event.app.current_buffer
            if b.complete_state:
                # Already showing completions, cycle to next
                b.complete_next()
            else:
                # Start completion and insert common prefix if any
                b.start_completion(insert_common_part=True, select_first=False)

        @input_kb.add("s-tab")
        def _(event: "KeyPressEvent") -> None:
            """Previous completion on Shift-Tab"""
            b = event.app.current_buffer
            if b.complete_state:
                b.complete_previous()

        @input_kb.add("enter")
        def _(event: "KeyPressEvent") -> None:
            """Accept completion or submit"""
            b = event.app.current_buffer
            if b.complete_state:
                # Accept the current completion
                b.complete_state = None
            else:
                # Submit the form
                ok_handler()

        @input_kb.add("escape")
        def _(event: "KeyPressEvent") -> None:
            """Cancel dialog"""
            cancel_handler()

        # Create window with buffer control and completions menu
        from prompt_toolkit.layout.menus import CompletionsMenu
        from prompt_toolkit.layout.containers import FloatContainer

        input_control = BufferControl(
            buffer=input_buffer, key_bindings=input_kb, focus_on_click=True
        )

        input_window = Window(content=input_control, height=1, dont_extend_height=True)

        # Create dialog body with completions support
        dialog_body = FloatContainer(
            content=HSplit(
                [
                    Label(
                        text="File path (Tab to complete, Enter to open, Esc to cancel):"
                    ),
                    input_window,
                ]
            ),
            floats=[
                Float(
                    xcursor=True, ycursor=True, content=CompletionsMenu(max_height=10)
                )
            ],
        )

        # Create dialog
        dialog = Dialog(
            title="Open File",
            body=dialog_body,
            buttons=[
                Button(text="OK", handler=ok_handler),
                Button(text="Cancel", handler=cancel_handler),
            ],
            width=70,
            modal=True,
        )

        # Add as floating window
        float_container = Float(content=dialog)
        if self.app:
            container = cast(FloatContainer, self.app.layout.container)
            container.floats.append(float_container)

            # Focus the input buffer
            self.app.layout.focus(input_window)
            self.app.invalidate()

    def add_tab(self, file_path: str | Path | None = None) -> None:
        """Add new tab.

        Args:
            file_path: Optional path to file to open in new tab
        """
        tab = EditorTab(file_path)
        self.tabs.append(tab)
        self.current_tab_index = len(self.tabs) - 1

        # Set focus to the new tab's text area if app is running
        if self.app:
            self.app.layout.focus(tab.text_area)

    def create_tab_bar(self) -> Window:
        """Create tab bar showing all open tabs.

        Returns:
            Window with tab bar
        """

        def get_text() -> str:
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
            style="bg:#3366cc fg:#ffffff",
        )

    def create_layout(self) -> FloatContainer:
        """Create editor layout.

        Returns:
            FloatContainer with complete editor layout
        """
        if not self.tabs:
            self.add_tab()

        # Use a dynamic container that updates based on current_tab_index
        from prompt_toolkit.layout.containers import DynamicContainer, FloatContainer

        def get_current_editor() -> TextArea | Window:
            if self.tabs and 0 <= self.current_tab_index < len(self.tabs):
                return self.tabs[self.current_tab_index].text_area
            return Window()  # Fallback empty window

        # Main content
        root_container = HSplit(
            [
                self.create_tab_bar(),
                DynamicContainer(get_current_editor),
                self.app_state.create_help_window(self.get_help_text()),
                self.app_state.create_shreds_table(),
                self.app_state.create_log_window(),
                self.app_state.create_status_bar(lambda: self.get_status_text()),
            ]
        )

        # Wrap in FloatContainer to support floating dialogs
        return FloatContainer(content=root_container, floats=[])

    def get_help_text(self) -> str:
        """Get help text for F1 window.

        Returns:
            Help text string
        """
        project_info = (
            f"Project: {self.app_state.session.project.name}"
            if self.app_state.session.project
            else "No project (use: numchuck edit --project <name>)"
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
Versioning: file.ck -> file-1.ck (spork) -> file-1-1.ck (replace)
"""

    def get_status_text(self) -> str:
        """Get status bar text.

        Returns:
            Status text string
        """
        # Shred count
        shred_count = len(self.app_state.session.shreds)
        audio_status = "[ON]" if self.app_state.audio_running else "[OFF]"

        # Current file info
        if self.tabs:
            tab = self.tabs[self.current_tab_index]
            file_info = tab.display_name
        else:
            file_info = "No tabs"

        return f" {audio_status} {shred_count} shreds | {file_info} | {self.status_message} | F1:Help "

    def cleanup(self) -> None:
        """Cleanup on exit."""
        # Clean up app state (handles audio stop and ChucK cleanup)
        self.app_state.cleanup()

        # Break circular references
        if hasattr(self, "tabs"):
            for tab in self.tabs:
                if hasattr(tab, "text_area"):
                    del tab.text_area
            self.tabs.clear()
            del self.tabs

        if hasattr(self, "app_state"):
            del self.app_state

        if hasattr(self, "app"):
            self.app = None

    def run(self, files: list[str] | None = None) -> None:
        """Run editor.

        Args:
            files: Optional list of file paths to open
        """
        # Load files or create empty tab
        if files:
            for f in files:
                self.add_tab(f)
        else:
            self.add_tab()

        # Start audio if requested
        if self.start_audio_flag:
            if self.app_state.start_audio_playback():
                self.status_message = "Audio started"
            else:
                self.status_message = "Audio start failed"

        # Create application
        self.app = Application(
            layout=Layout(self.create_layout()),
            key_bindings=self.create_key_bindings(),
            full_screen=True,
            mouse_support=True,
        )

        try:
            self.app.run()
        finally:
            self.cleanup()


def main(
    files: list[str] | None = None,
    project_name: str | None = None,
    start_audio: bool = False,
) -> None:
    """Main entry point for editor.

    Args:
        files: Optional list of files to open
        project_name: Optional project name for versioning
        start_audio: Whether to start audio on launch
    """
    editor = ChuckEditor(project_name=project_name, start_audio=start_audio)
    editor.run(files=files)


if __name__ == "__main__":
    main()
