# Refined Implementation Plan

**Date**: 2025-10-07
**Based on**: REFACTOR.md + REFACTOR_FEEDBACK.md with user answers
**Timeline**: 10-15 days

---

## Overview

This document provides the **definitive implementation plan** incorporating all user clarifications. The plan focuses on:

1. **Project-based versioning system** for livecoding session preservation
2. **Tab-shred ID mapping** for clear visual indication
3. **Chuck-consistent commands** in REPL (add/remove/replace)
4. **Clean separation** of editor and REPL modes
5. **Proper cleanup** on application exit

---

## Key Design Decisions (Confirmed)

### 1. Project-Based Versioning System

**Location**: `~/.pychuck/projects/<project_name>/`

**Versioning Scheme**:
```
mysynth.ck                    # Original file
mysynth-1.ck                  # After first spork (shred ID 1)
mysynth-1-1.ck                # After first replace of shred 1
mysynth-1-2.ck                # After second replace of shred 1
mysynth-2.ck                  # Second spork of same file (shred ID 2)
mysynth-2-1.ck                # First replace of shred 2
```

**Benefits**:
- Preserves complete livecoding history
- Order of sporking captured in filename
- Iterative changes tracked
- Easy to reconstruct session timeline

**Example Session**:
```
1. Edit mysynth.ck
2. Spork → saves mysynth-1.ck (shred ID 1)
3. Modify code
4. Replace → saves mysynth-1-1.ck (replacement version 1)
5. Modify more
6. Replace → saves mysynth-1-2.ck (replacement version 2)
7. Open mysynth.ck again
8. Spork → saves mysynth-2.ck (shred ID 2, different instance)
```

### 2. Tab Numbering

**Display Format**: `[filename-shredID]` or `[filename]` if not sporked

**Examples**:
- `[bass.ck]` - Not yet sporked
- `[bass-1]` - Sporked as shred 1
- `[bass-2*]` - Sporked as shred 2, modified (asterisk = unsaved)

### 3. REPL Commands

**Chuck-style commands** (consistent with chuck executable):
- `add <file>` - Spork a file as new shred
- `remove <id>` - Remove shred by ID
- `remove all` - Remove all shreds
- `replace <id> <file>` - Replace shred with file content
- `status` - Show VM status
- `time` - Show current ChucK time

**Also support shorthand**:
- `+ <file>` - Alias for `add`
- `- <id>` - Alias for `remove`
- `= <id> <file>` - Alias for `replace`

### 4. Directory Structure (Confirmed)

```
pychuck/
  __init__.py
  __main__.py
  _pychuck.so
  chuck_lang.py
  cli/                        # CLI argument parsing & execution
    __init__.py
    main.py                   # Argument parsing
    executor.py               # File execution
  tui/                        # Terminal UI components
    __init__.py
    common.py                 # Shared base classes
    editor.py                 # Editor mode (NEW)
    repl.py                   # REPL mode (REFACTORED)
    chuck_lexer.py
    commands.py               # Command execution
    parser.py                 # Command parsing
    paths.py                  # Path utilities (EXTENDED)
    session.py                # Session management (EXTENDED)
    project.py                # Project management (NEW)
```

### 5. Keybindings (Confirmed)

**Shared** (Editor + REPL):
- `Ctrl-Q` - Exit application
- `F1` - Toggle help window
- `F2` - Toggle shreds table
- `F3` - Toggle log window

**Editor-specific**:
- `F5` or `Ctrl-R` - Spork current buffer as new shred
- `F6` or `Ctrl-Shift-R` - Replace existing shred with current buffer
- `Ctrl-S` - Save file to disk (explicit save)
- `Ctrl-T` - New tab
- `Ctrl-W` - Close current tab
- `Ctrl-Tab` - Next tab
- `Ctrl-Shift-Tab` - Previous tab

---

## Phase 1: Foundation & Restructure (2-3 days)

### 1.1 Directory Restructure

**Tasks**:
1. Create `cli/` and move CLI logic
2. Rename `cli/` to `tui/`
3. Update all imports

**Commands**:
```bash
cd src/pychuck

# Create cli directory
mkdir -p cli
touch cli/__init__.py

# Rename existing cli → tui
mv cli tui

# Create new files
touch cli/main.py
touch cli/executor.py
touch tui/common.py
touch tui/project.py
```

**Update imports** in:
- `__main__.py`
- All files in `tui/`
- Test files

### 1.2 Create Project Management System

**New file: `tui/project.py`**

```python
"""
Project management for livecoding sessions.

Handles versioning scheme: file.ck → file-1.ck → file-1-1.ck
"""
from pathlib import Path
from typing import Optional, Tuple
import time

class ProjectVersion:
    """Represents a versioned file in a project."""

    def __init__(self, base_name: str, shred_id: Optional[int] = None,
                 replace_version: Optional[int] = None):
        self.base_name = base_name  # e.g., "mysynth.ck"
        self.shred_id = shred_id     # e.g., 1 (from first spork)
        self.replace_version = replace_version  # e.g., 2 (from second replace)

    def filename(self) -> str:
        """Generate filename based on versioning scheme."""
        name, ext = self.base_name.rsplit('.', 1) if '.' in self.base_name else (self.base_name, 'ck')

        if self.shred_id is None:
            return f"{name}.{ext}"
        elif self.replace_version is None:
            return f"{name}-{self.shred_id}.{ext}"
        else:
            return f"{name}-{self.shred_id}-{self.replace_version}.{ext}"

    def next_replace(self) -> 'ProjectVersion':
        """Get next replacement version."""
        next_ver = 1 if self.replace_version is None else self.replace_version + 1
        return ProjectVersion(self.base_name, self.shred_id, next_ver)

    @classmethod
    def from_filename(cls, filename: str) -> 'ProjectVersion':
        """Parse filename to extract version info."""
        # Parse: mysynth-1-2.ck → base="mysynth.ck", shred=1, replace=2
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, 'ck')
        parts = name.split('-')

        if len(parts) == 1:
            return cls(f"{parts[0]}.{ext}", None, None)
        elif len(parts) == 2:
            return cls(f"{parts[0]}.{ext}", int(parts[1]), None)
        else:
            return cls(f"{parts[0]}.{ext}", int(parts[1]), int(parts[2]))


class Project:
    """Manages a livecoding project with versioned files."""

    def __init__(self, name: str, projects_dir: Path):
        self.name = name
        self.project_dir = projects_dir / name
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Track shred ID → current version for each file
        self.shred_versions = {}  # shred_id → ProjectVersion

    def save_on_spork(self, filename: str, content: str, shred_id: int) -> Path:
        """Save file when sporked with new shred ID."""
        version = ProjectVersion(filename, shred_id)
        self.shred_versions[shred_id] = version

        filepath = self.project_dir / version.filename()
        filepath.write_text(content)
        return filepath

    def save_on_replace(self, shred_id: int, content: str) -> Path:
        """Save file when shred is replaced."""
        if shred_id not in self.shred_versions:
            raise ValueError(f"Shred {shred_id} not found in project")

        # Get next replacement version
        current = self.shred_versions[shred_id]
        next_version = current.next_replace()
        self.shred_versions[shred_id] = next_version

        filepath = self.project_dir / next_version.filename()
        filepath.write_text(content)
        return filepath

    def save_original(self, filename: str, content: str) -> Path:
        """Save original file (not yet sporked)."""
        filepath = self.project_dir / filename
        filepath.write_text(content)
        return filepath

    def list_versions(self) -> list[Path]:
        """List all versioned files in project."""
        return sorted(self.project_dir.glob("*.ck"))

    def get_timeline(self) -> list[dict]:
        """Get chronological timeline of all versions."""
        files = []
        for path in self.list_versions():
            version = ProjectVersion.from_filename(path.name)
            files.append({
                'filename': path.name,
                'base': version.base_name,
                'shred_id': version.shred_id,
                'replace_version': version.replace_version,
                'mtime': path.stat().st_mtime
            })

        # Sort by modification time
        return sorted(files, key=lambda x: x['mtime'])
```

### 1.3 Update `paths.py`

**Add functions**:

```python
def get_projects_dir() -> Path:
    """Get the projects directory."""
    projects_dir = get_pychuck_home() / 'projects'
    projects_dir.mkdir(parents=True, exist_ok=True)
    return projects_dir

def list_projects() -> list[str]:
    """List all projects."""
    projects_dir = get_projects_dir()
    return [d.name for d in projects_dir.iterdir() if d.is_dir()]

def create_project(name: str) -> Path:
    """Create a new project directory."""
    from .project import Project
    projects_dir = get_projects_dir()
    project = Project(name, projects_dir)
    return project.project_dir
```

### 1.4 Extend `session.py`

**Add project awareness**:

```python
from .project import Project, ProjectVersion
from .paths import get_projects_dir

class ChuckSession:
    """Extended session with project support."""

    def __init__(self, chuck, project_name: Optional[str] = None):
        self.chuck = chuck
        self.shreds = {}
        self.project = None

        if project_name:
            projects_dir = get_projects_dir()
            self.project = Project(project_name, projects_dir)

    def add_shred(self, shred_id: int, name: str, content: Optional[str] = None):
        """Add shred and save to project if applicable."""
        self.shreds[shred_id] = {
            'id': shred_id,
            'name': name,
            'time': self.chuck.now()
        }

        # If we have a project and content, save versioned file
        if self.project and content:
            self.project.save_on_spork(name, content, shred_id)

    def replace_shred(self, shred_id: int, content: str):
        """Replace shred and save new version to project."""
        if self.project:
            self.project.save_on_replace(shred_id, content)
```

**Deliverables**:
- ✅ New directory structure
- ✅ `project.py` with versioning system
- ✅ `paths.py` extended for projects
- ✅ `session.py` with project support
- ✅ All imports updated
- ✅ Existing tests pass

---

## Phase 2: CLI Refactor (1-2 days)

### 2.1 Create `cli/main.py`

**Implement subcommand-based CLI**:

```python
"""Main CLI entry point."""
import argparse

def create_parser():
    parser = argparse.ArgumentParser(prog='pychuck')
    subparsers = parser.add_subparsers(dest='command')

    # edit - Launch editor
    edit_parser = subparsers.add_parser('edit')
    edit_parser.add_argument('files', nargs='*')
    edit_parser.add_argument('--project', help='Project name')
    edit_parser.add_argument('--start-audio', action='store_true')

    # repl - Launch REPL
    repl_parser = subparsers.add_parser('repl')
    repl_parser.add_argument('files', nargs='*')
    repl_parser.add_argument('--start-audio', action='store_true')
    repl_parser.add_argument('--no-smart-enter', action='store_true')

    # exec - Execute files
    exec_parser = subparsers.add_parser('exec')
    exec_parser.add_argument('files', nargs='+')
    exec_parser.add_argument('--srate', type=int, default=44100)
    exec_parser.add_argument('--channels', type=int, default=2)
    exec_parser.add_argument('--bufsize', type=int, default=512)
    exec_parser.add_argument('--silent', action='store_true')
    exec_parser.add_argument('--loop', action='store_true')

    # version, info
    version_parser = subparsers.add_parser('version')
    info_parser = subparsers.add_parser('info')

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'edit':
        from ..tui.editor import main as editor_main
        editor_main(files=args.files,
                   project_name=args.project,
                   start_audio=args.start_audio)

    elif args.command == 'repl':
        from ..tui.repl import main as repl_main
        repl_main(files=args.files,
                 start_audio=args.start_audio,
                 smart_enter=not args.no_smart_enter)

    elif args.command == 'exec':
        from .executor import execute_files
        execute_files(args.files, **vars(args))

    # ... handle version, info ...
```

### 2.2 Create `cli/executor.py`

**Execute ChucK files from CLI**:

```python
"""Execute ChucK files from command line."""
import sys
import time
from pathlib import Path

def execute_files(files, sample_rate=44100, channels=2, buffer_size=512,
                 silent=False, loop=False, **kwargs):
    """Execute ChucK file(s) with specified parameters."""
    from .. import ChucK, start_audio, stop_audio, shutdown_audio
    from .. import PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS

    chuck = ChucK()
    chuck.set_param(PARAM_SAMPLE_RATE, sample_rate)
    chuck.set_param(PARAM_OUTPUT_CHANNELS, channels)
    chuck.set_param(PARAM_INPUT_CHANNELS, 0)
    chuck.init()

    # Compile files
    for file_path in files:
        path = Path(file_path)
        if not path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)

        success, shred_ids = chuck.compile_file(str(path))
        if not success:
            print(f"Error: Failed to compile {file_path}", file=sys.stderr)
            sys.exit(1)

        print(f"Sporked shred {shred_ids[0]}: {path.name}")

    if not silent:
        start_audio(chuck, sample_rate=sample_rate,
                   num_dac_channels=channels,
                   buffer_size=buffer_size)
        print(f"Audio started (Ctrl-C to stop)")

        try:
            if loop:
                while True:
                    time.sleep(1)
            else:
                # Wait for shreds to complete
                while chuck.get_all_shred_ids():
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            stop_audio()
            shutdown_audio()
```

**Deliverables**:
- ✅ `cli/main.py` with subcommands
- ✅ `cli/executor.py` for file execution
- ✅ `__main__.py` updated
- ✅ All CLI commands work

---

## Phase 3: REPL Refactor (1-2 days)

### 3.1 Update REPL Commands

**Modify `tui/commands.py`** to support chuck-style commands:

```python
class CommandExecutor:
    """Execute REPL commands."""

    def execute(self, command_str: str):
        """Execute a command string."""
        parts = command_str.strip().split()
        if not parts:
            return

        cmd = parts[0]
        args = parts[1:]

        # Chuck-style shortcuts
        if cmd == '+':
            cmd = 'add'
        elif cmd == '-':
            cmd = 'remove'
        elif cmd == '=':
            cmd = 'replace'

        # Dispatch
        if cmd == 'add':
            return self.handle_add(args)
        elif cmd == 'remove':
            return self.handle_remove(args)
        elif cmd == 'replace':
            return self.handle_replace(args)
        elif cmd == 'status':
            return self.handle_status(args)
        elif cmd == 'time':
            return self.handle_time(args)
        # ... other commands ...

    def handle_add(self, args):
        """Add/spork a file: add <file>"""
        if not args:
            return "Usage: add <file>"

        filepath = args[0]
        success, shred_ids = self.session.chuck.compile_file(filepath)

        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, filepath)
            return f"Sporked shreds: {shred_ids}"
        else:
            return f"Failed to compile {filepath}"

    def handle_remove(self, args):
        """Remove shred(s): remove <id> or remove all"""
        if not args:
            return "Usage: remove <id> or remove all"

        if args[0] == 'all':
            self.session.chuck.remove_all_shreds()
            self.session.shreds.clear()
            return "Removed all shreds"
        else:
            shred_id = int(args[0])
            self.session.chuck.remove_shred(shred_id)
            self.session.shreds.pop(shred_id, None)
            return f"Removed shred {shred_id}"

    def handle_replace(self, args):
        """Replace shred: replace <id> <file>"""
        if len(args) < 2:
            return "Usage: replace <id> <file>"

        shred_id = int(args[0])
        filepath = args[1]

        code = Path(filepath).read_text()
        new_id = self.session.chuck.replace_shred(shred_id, code)

        self.session.shreds.pop(shred_id, None)
        self.session.add_shred(new_id, filepath)

        return f"Replaced shred {shred_id} → {new_id}"

    def handle_status(self, args):
        """Show VM status."""
        all_ids = self.session.chuck.get_all_shred_ids()
        ready = self.session.chuck.get_ready_shred_ids()
        blocked = self.session.chuck.get_blocked_shred_ids()

        lines = [
            f"Total shreds: {len(all_ids)}",
            f"Ready: {len(ready)}",
            f"Blocked: {len(blocked)}",
            f"ChucK time: {self.session.chuck.now()} samples"
        ]
        return "\n".join(lines)

    def handle_time(self, args):
        """Show current ChucK time."""
        return f"ChucK time: {self.session.chuck.now()} samples"
```

### 3.2 Update `tui/repl.py`

**Key changes**:
1. Use `ChuckApplication` base from `common.py`
2. Support file loading on startup
3. Change log toggle to F3
4. Ensure cleanup on exit

```python
from .common import ChuckApplication

class ChuckREPL:
    def __init__(self, smart_enter=True, files=None):
        self.app = ChuckApplication()
        self.smart_enter = smart_enter
        self.files_to_load = files or []
        # ... rest of initialization ...

    def initialize(self):
        """Initialize and load files if provided."""
        from .. import PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS

        self.app.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.app.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.app.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.app.chuck.init()

        # Load files (like python -i)
        for file_path in self.files_to_load:
            success, ids = self.app.chuck.compile_file(file_path)
            if success:
                for sid in ids:
                    self.app.session.add_shred(sid, file_path)
                print(f"Loaded {file_path}: {ids}")

    def cleanup(self):
        """Cleanup on exit."""
        from .. import stop_audio, shutdown_audio
        if hasattr(self, 'audio_started') and self.audio_started:
            stop_audio()
            shutdown_audio()
        self.app.chuck.remove_all_shreds()

def main(files=None, start_audio=False, smart_enter=True):
    """Main entry point."""
    repl = ChuckREPL(smart_enter=smart_enter, files=files)
    repl.initialize()

    if start_audio:
        repl.start_audio()

    try:
        repl.run()
    finally:
        repl.cleanup()
```

**Deliverables**:
- ✅ Chuck-style commands (add/remove/replace)
- ✅ File loading on startup
- ✅ Log toggle changed to F3
- ✅ Proper cleanup on exit
- ✅ Tests updated

---

## Phase 4: Implement Editor (4-5 days)

This is the most complex phase, implementing the new editor with project versioning.

### 4.1 Create `tui/common.py`

**Shared base class** for editor and REPL:

```python
"""Shared TUI components."""
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

    def get_common_key_bindings(self):
        """Common key bindings."""
        kb = KeyBindings()

        @kb.add('c-q')
        def exit_app(event):
            event.app.exit()

        @kb.add('f1')
        def toggle_help(event):
            self.show_help = not self.show_help

        @kb.add('f2')
        def toggle_shreds(event):
            self.show_shreds = not self.show_shreds

        @kb.add('f3')
        def toggle_log(event):
            self.show_log = not self.show_log

        return kb

    def create_help_window(self, help_text):
        """Create help window."""
        return ConditionalContainer(
            Window(
                content=FormattedTextControl(text=help_text),
                height=D(min=3, max=20),
                wrap_lines=True
            ),
            filter=Condition(lambda: self.show_help)
        )

    def create_shreds_table(self):
        """Create shreds table."""
        def get_text():
            if not self.session.shreds:
                return "No active shreds"

            lines = ["ID | Name | Time"]
            lines.append("-" * 50)
            for sid, info in sorted(self.session.shreds.items()):
                name = info['name'][:30]
                lines.append(f"{sid:3d} | {name:30s} | {info['time']:.2f}s")
            return "\n".join(lines)

        return ConditionalContainer(
            Window(
                content=FormattedTextControl(get_text),
                height=D(min=5, max=15)
            ),
            filter=Condition(lambda: self.show_shreds)
        )

    def create_log_window(self):
        """Create log window."""
        log_area = TextArea(
            text="",
            scrollbar=True,
            focusable=False,
            read_only=True,
            height=D(min=5, max=15)
        )

        def log_callback(msg):
            log_area.text += msg

        self.chuck.set_chout_callback(log_callback)
        self.chuck.set_cherr_callback(log_callback)

        return ConditionalContainer(
            log_area,
            filter=Condition(lambda: self.show_log)
        )

    def create_status_bar(self, status_text_func):
        """Create status bar."""
        return Window(
            content=FormattedTextControl(status_text_func),
            height=1,
            style='bg:#444444 fg:#ffffff'
        )

    def cleanup(self):
        """Cleanup ChucK resources."""
        self.chuck.remove_all_shreds()
```

### 4.2 Create `tui/editor.py`

**Full editor implementation**:

```python
"""ChucK live coding editor with project versioning."""

from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import TextArea
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.layout.dimension import Dimension as D
from pathlib import Path

from .common import ChuckApplication
from .chuck_lexer import ChuckLexer

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

        # Create text area
        self.text_area = TextArea(
            text=content,
            multiline=True,
            scrollbar=True,
            lexer=PygmentsLexer(ChuckLexer),
            wrap_lines=False
        )

        # Track modifications
        def on_change(_):
            self.modified = True
        self.text_area.buffer.on_text_changed += on_change

    @property
    def display_name(self):
        """Tab display name with shred ID."""
        name = self.file_path.name if self.file_path else "untitled"

        # Add shred ID if sporked
        if self.shred_id is not None:
            name = f"{name.rsplit('.', 1)[0]}-{self.shred_id}"

        # Add modified indicator
        if self.modified:
            name += "*"

        return name

    @property
    def content(self):
        return self.text_area.text

    @content.setter
    def content(self, value):
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

        # Create key bindings
        self.kb = self.create_key_bindings()

    def create_key_bindings(self):
        """Create editor key bindings."""
        kb = self.app_state.get_common_key_bindings()

        @kb.add('c-s')
        def save_file(event):
            """Save current file."""
            tab = self.tabs[self.current_tab_index]
            if tab.file_path:
                tab.file_path.write_text(tab.content)
                tab.modified = False
                self.status_message = f"Saved {tab.file_path}"
            else:
                self.status_message = "No filename (will auto-save on spork)"

        @kb.add('f5')
        @kb.add('c-r')
        def spork_code(event):
            """Spork current buffer."""
            tab = self.tabs[self.current_tab_index]
            success, shred_ids = self.app_state.chuck.compile_code(tab.content)

            if success:
                shred_id = shred_ids[0]
                tab.shred_id = shred_id

                # Save to project with versioning
                filename = tab.file_path.name if tab.file_path else "untitled.ck"
                self.app_state.session.add_shred(shred_id, filename, tab.content)

                self.status_message = f"Sporked shred {shred_id}"
                tab.modified = False
            else:
                self.status_message = "Compilation failed"

        @kb.add('f6')
        @kb.add('c-S-r')
        def replace_shred(event):
            """Replace existing shred."""
            tab = self.tabs[self.current_tab_index]

            if tab.shred_id is None:
                self.status_message = "No shred to replace (F5 to spork first)"
                return

            try:
                new_id = self.app_state.chuck.replace_shred(tab.shred_id, tab.content)
                old_id = tab.shred_id

                # Save replacement version to project
                self.app_state.session.replace_shred(tab.shred_id, tab.content)

                # Update tab
                self.app_state.session.shreds.pop(old_id, None)
                filename = tab.file_path.name if tab.file_path else "untitled.ck"
                self.app_state.session.add_shred(new_id, filename, tab.content)

                tab.shred_id = new_id
                tab.modified = False

                self.status_message = f"Replaced {old_id} → {new_id}"
            except Exception as e:
                self.status_message = f"Replace failed: {e}"

        @kb.add('c-t')
        def new_tab(event):
            """New tab."""
            self.add_tab()

        @kb.add('c-w')
        def close_tab(event):
            """Close tab."""
            if len(self.tabs) > 1:
                self.tabs.pop(self.current_tab_index)
                self.current_tab_index = min(self.current_tab_index, len(self.tabs) - 1)

        @kb.add('c-tab')
        def next_tab(event):
            """Next tab."""
            self.current_tab_index = (self.current_tab_index + 1) % len(self.tabs)

        @kb.add('c-s-tab')
        def prev_tab(event):
            """Previous tab."""
            self.current_tab_index = (self.current_tab_index - 1) % len(self.tabs)

        return kb

    def add_tab(self, file_path=None):
        """Add new tab."""
        tab = EditorTab(file_path)
        self.tabs.append(tab)
        self.current_tab_index = len(self.tabs) - 1

    def create_tab_bar(self):
        """Create tab bar."""
        def get_text():
            parts = []
            for i, tab in enumerate(self.tabs):
                if i == self.current_tab_index:
                    parts.append(f" [{tab.display_name}] ")
                else:
                    parts.append(f"  {tab.display_name}  ")
            return "".join(parts)

        return Window(
            content=FormattedTextControl(get_text),
            height=1,
            style='bg:#3366cc fg:#ffffff'
        )

    def create_layout(self):
        """Create layout."""
        current_tab = self.tabs[self.current_tab_index]

        return HSplit([
            self.create_tab_bar(),
            current_tab.text_area,
            self.app_state.create_help_window(self.get_help_text()),
            self.app_state.create_shreds_table(),
            self.app_state.create_log_window(),
            self.app_state.create_status_bar(lambda:
                f" F1:Help F2:Shreds F3:Log F5:Spork F6:Replace Ctrl-S:Save | {self.status_message} "
            )
        ])

    def get_help_text(self):
        """Help text."""
        project_info = f"Project: {self.app_state.session.project.name}" if self.app_state.session.project else "No project"

        return f"""
ChucK Editor Help - {project_info}

F1              Toggle help
F2              Toggle shreds table
F3              Toggle log
F5 / Ctrl-R     Spork current buffer
F6 / Ctrl-Shift-R  Replace existing shred

Ctrl-S          Save file
Ctrl-T          New tab
Ctrl-W          Close tab
Ctrl-Tab        Next tab
Ctrl-Shift-Tab  Previous tab
Ctrl-Q          Exit

Files versioned in: {self.app_state.session.project.project_dir if self.app_state.session.project else 'N/A'}
"""

    def cleanup(self):
        """Cleanup on exit."""
        if self.audio_started:
            from .. import stop_audio, shutdown_audio
            stop_audio()
            shutdown_audio()
        self.app_state.cleanup()

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
            from .. import start_audio
            start_audio(self.app_state.chuck)
            self.audio_started = True
            self.status_message = "Audio started"

        # Run application
        app = Application(
            layout=Layout(self.create_layout()),
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )

        try:
            app.run()
        finally:
            self.cleanup()


def main(files=None, project_name=None, start_audio=False):
    """Main entry point for editor."""
    editor = ChuckEditor(project_name=project_name, start_audio=start_audio)
    editor.run(files=files)
```

**Deliverables**:
- ✅ Multi-tab editor
- ✅ Project versioning system working
- ✅ Spork (F5) and Replace (F6)
- ✅ Tab names show shred IDs
- ✅ Shared F1/F2/F3 windows
- ✅ Proper cleanup on exit

---

## Phase 5: Testing & Documentation (2-3 days)

### 5.1 Manual Testing

**Test matrix**:

```bash
# CLI commands
pychuck edit
pychuck edit --project myproject
pychuck edit file1.ck file2.ck
pychuck repl
pychuck repl file1.ck
pychuck exec examples/basic/blit2.ck

# Editor workflow
1. Launch: pychuck edit --project livetest
2. Write code in tab
3. F5 to spork → verify file-1.ck created
4. Modify code
5. F6 to replace → verify file-1-1.ck created
6. F6 again → verify file-1-2.ck created
7. Check ~/.pychuck/projects/livetest/ for files

# REPL workflow
1. Launch: pychuck repl examples/basic/blit2.ck
2. Verify file loaded
3. Test: add examples/basic/pulse.ck
4. Test: remove 1
5. Test: status
6. Test: time
```

### 5.2 Automated Testing

**Add tests**:

```python
# tests/test_project_versioning.py
def test_project_creation():
    """Test project creation."""
    from pychuck.tui.project import Project
    from pychuck.tui.paths import get_projects_dir

    project = Project("test", get_projects_dir())
    assert project.project_dir.exists()

def test_spork_versioning():
    """Test file versioning on spork."""
    project = Project("test", get_projects_dir())

    # Spork creates file-1.ck
    path = project.save_on_spork("myfile.ck", "// code", 1)
    assert path.name == "myfile-1.ck"

    # Replace creates file-1-1.ck
    path = project.save_on_replace(1, "// modified")
    assert path.name == "myfile-1-1.ck"

# tests/test_cli.py
def test_cli_parsing():
    """Test CLI argument parsing."""
    from pychuck.cli.main import create_parser

    parser = create_parser()
    args = parser.parse_args(['edit', '--project', 'test'])
    assert args.command == 'edit'
    assert args.project == 'test'
```

### 5.3 Documentation Updates

**Update**:
1. README.md - Add editor section, update CLI examples
2. CLAUDE.md - Update with new structure
3. Docstrings - Ensure all new code has docstrings

**Deliverables**:
- ✅ All tests passing
- ✅ Manual testing complete
- ✅ Documentation updated
- ✅ No regressions

---

## Timeline Summary

| Phase | Tasks | Duration | Dependencies |
|-------|-------|----------|--------------|
| Phase 1 | Foundation & Restructure | 2-3 days | None |
| Phase 2 | CLI Refactor | 1-2 days | Phase 1 |
| Phase 3 | REPL Refactor | 1-2 days | Phase 1, 2 |
| Phase 4 | Editor Implementation | 4-5 days | Phase 1, 2, 3 |
| Phase 5 | Testing & Documentation | 2-3 days | All phases |
| **Total** | | **10-15 days** | |

---

## Success Criteria

**Must Have**:
- ✅ Editor with multi-tab support
- ✅ Project versioning: file.ck → file-1.ck → file-1-1.ck
- ✅ Tab names show shred IDs
- ✅ Spork (F5) and Replace (F6) work correctly
- ✅ REPL with file loading and chuck commands
- ✅ Shared F1/F2/F3 windows across modes
- ✅ Proper cleanup on Ctrl-Q
- ✅ All existing tests pass

**Nice to Have**:
- Timeline view of project versions
- Project import/export
- Diff view between versions
- Search across project files

---

## Risk Mitigation

**Risks**:
1. **Complex versioning logic** - Mitigate with comprehensive tests
2. **Tab-shred ID synchronization** - Mitigate with clear data flow
3. **File system race conditions** - Mitigate with proper locking (if needed)

**Testing Strategy**:
- Unit tests for versioning logic
- Integration tests for editor workflow
- Manual testing of full user scenarios

---

## Next Steps

1. **Review this plan** - Confirm all details
2. **Create feature branch** - `git checkout -b refactor-editor-repl`
3. **Start Phase 1** - Foundation work
4. **Daily check-ins** - Track progress, adjust as needed

Ready to proceed? 🚀
