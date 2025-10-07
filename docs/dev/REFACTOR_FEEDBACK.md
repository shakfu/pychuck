# Refactor Feedback & Implementation Plan

**Date**: 2025-10-07
**Reviewer**: Claude Code (Sonnet 4.5)
**Source Document**: REFACTOR.md

---

## Executive Summary

**Overall Assessment**: ✅ **Excellent refactoring plan** with clear architectural vision.

The proposed separation of editor and REPL modes is well-motivated, and the CLI design following Chuck conventions is user-friendly. The plan requires clarifications on several implementation details before proceeding.

**Estimated Timeline**: 8-13 days
**Risk Level**: Low (non-breaking restructuring first, incremental additions)

---

## Strengths of the Plan

1. **Clear Separation of Concerns**: Editor vs REPL as distinct modes makes architectural sense
2. **Shared Infrastructure**: Common keyboard shortcuts (F1, F2, F3) provide consistency
3. **CLI Design**: Following Chuck's CLI conventions benefits existing Chuck users
4. **Code Organization**: Moving from `cli/` to `tui/` and extracting `common.py` improves modularity
5. **File Persistence**: Auto-save to `~/.pychuck/editor/` for version tracking

---

## Feedback & Clarifications Needed

### 1. Editor Mode Design

**Status**: ⚠️ Needs Clarification

**Questions**:

- Should the editor support **multiple tabs** (like demo0.py) for editing multiple files simultaneously?

> Yes, it should support multiple tabs. Indeed, the tabs are numbered to reflect the shred-id.

- How should file persistence work? Auto-save on every change or explicit save command?

> The ideal scenario is to create a named `project`, which is a folder, as in `~/.pychuck/projects/<name>`. In this folder, initial chuck files are saved as normal. However, when they are **sporked** or added a shred, they get given an integer id (an indication of the order of sporking) which becomes its suffix, and the file is saved again so `<name>.ck` becomes `<name>-1.ck`. When the same file is modified and a **replace** instruction is triggered, `<name>-1.ck` becomes `<name>-1-1.ck` and if replaced again `<name>-1-2.ck` etc.. Hence the order of sporking is preserved and iterative capture of livecoding changes is preservered. Perhaps a series of diffs would be more space efficient, but that is an optimization for another day.

- What's the workflow for "spork" vs "replace"? Keyboard shortcuts?

> **spork** adds the file/code in buffer/current tab as a shred where it is given an id.

> **replace** replaces an existing shred with the file/code in buffer/current tab

- Should it show audio output/errors inline or in separate pane?

> Logging should be in separate pane which can be opened and closed (F3)

**Recommended Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ [file1.ck] [file2.ck*] [+]        Ctrl-Q: Exit          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  // ChucK code editor with syntax highlighting          │
│  SinOsc s => dac;                                       │
│  440 => s.freq;                                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ F1: Help | F2: Shreds | F3: Log | F5: Spork | F6: Replace
└─────────────────────────────────────────────────────────┘
```

**Suggested Keybindings**:
- `F5` or `Ctrl-R`: Spork current buffer as new shred
- `F6` or `Ctrl-Shift-R`: Replace existing shred with current buffer
- `Ctrl-S`: Save file to disk
- `Ctrl-W`: Close current tab
- `Ctrl-T`: New tab
- `Ctrl-PageUp/PageDown`: Switch between tabs (or ctrl-tab, ctrl-shift-tab)

**Recommendation**: Implement multi-tab editor with explicit save (Ctrl-S) + auto-saving of replaced shred codes.

---

### 2. REPL Improvements

**Status**: ⚠️ Needs Specification

The current REPL (as of latest review) already has:
- ✅ Syntax highlighting (ChuckLexer)
- ✅ Help window (F1)
- ✅ Shreds table (F2)
- ✅ Log window (Ctrl-L, should be F3 for consistency)
- ✅ Smart enter mode
- ✅ Tab completion (commands + ChucK keywords)

**Questions**:

- What specific improvements are needed beyond current features?

> TBD

- Should REPL support loading files (spec mentions `pychuck repl [<file>, ..]`)?

> Yes. (like `python3 -i <file.py>`)

- Multi-line editing improvements?

> Yes by default (this is already in place)

- Additional command support?

> TBD

**Recommendations**:

1. Change log toggle from `Ctrl-L` → `F3` (for consistency with editor)

> Agreed

2. Add file loading: `pychuck repl file1.ck file2.ck` should load and spork files on startup

> Agreed

3. Add command: `load <file>` to load files during REPL session

> I would prefer consistency with chuck's:`add`, `remove`, `replace`
4. Ensure all features work with `ChuckApplication` base class


---

### 3. CLI API Design

**Status**: ⚠️ Needs Refinement

**Issue**: The proposed `pychuck [<file>, ...]` pattern conflicts with subcommand-based CLI design.

**Current (in code)**: `pychuck <subcommand> [options]`
**Proposed (in REFACTOR.md)**: `pychuck [<file>, ...]` with Chuck-style flags

**Two Options**:

#### Option A: Explicit Subcommands (Recommended)

```bash
# Launch modes
pychuck edit [<file>, ...]              # Launch editor
pychuck repl [<file>, ...]              # Launch REPL

# Execute files
pychuck exec <file> [options]           # Execute ChucK file(s)
  --srate=44100                          # Sample rate
  --channels=2                           # Output channels
  --bufsize=512                          # Buffer size
  --silent                               # Offline mode (no audio)
  --loop                                 # Loop indefinitely

# On-the-fly commands (when VM running)
pychuck add <file>                      # Add/spork shred
pychuck replace <id> <file>             # Replace shred
pychuck remove <id>                     # Remove shred
pychuck status                          # Show VM status

# Info
pychuck version                         # Show version
pychuck info                            # Show ChucK info
```

**Pros**: Clear, unambiguous, follows modern CLI conventions
**Cons**: Not exactly like Chuck executable

#### Option B: Chuck-Compatible with Fallback

```bash
# Execute mode (default if no subcommand)
pychuck file.ck [--channels=2 --srate=44100]

# Chuck-style shortcuts
pychuck + file.ck                       # Add shred
pychuck - 1                             # Remove shred 1
pychuck = 1 file.ck                     # Replace shred 1

# Explicit subcommands
pychuck edit file.ck                    # Launch editor
pychuck repl                            # Launch REPL
```

**Pros**: Familiar to Chuck users
**Cons**: Ambiguous parsing (what if file named "edit.ck"?), harder to maintain

**Recommendation**: **Use Option A** for clarity and maintainability. Add Chuck-style shortcuts as aliases if strongly desired.

---

### 4. Directory Structure

**Status**: ⚠️ Minor Issue

**Proposed in REFACTOR.md**:
```
pychuck/
  cli.py          # ← Single file at package root
  tui/            # ← TUI subdirectory
```

**Issue**: Having `cli.py` at root while `tui/` is a directory creates asymmetry.

**Recommended Structure**:
```
pychuck/
  __init__.py
  __main__.py
  _pychuck.so
  chuck_lang.py
  cli/                      # ← CLI as directory
    __init__.py
    main.py                 # CLI argument parsing
    executor.py             # Execute chuck files
  tui/                      # ← TUI components
    __init__.py
    common.py               # Shared base classes
    editor.py               # Editor mode
    repl.py                 # REPL mode
    chuck_lexer.py
    commands.py
    parser.py
    paths.py
    session.py
```

**Rationale**: Both `cli/` and `tui/` are organized as directories, maintaining symmetry and allowing future expansion.

> Agreed.

---

### 5. Shared State Management

**Status**: ⚠️ Architecture Question

Both editor and REPL need to interact with the same ChucK instance.

**Questions**:
- Can user switch between editor and REPL in the same session?

> No, it's too complicated

- Should there be a top-level application class managing the ChucK instance?

> If it makes sense

- How is ChucK instance lifecycle managed (init, cleanup)?

> There should cleanup if the application is closed or ctrl-q is called.

- What happens if both modes try to start audio?

> 

**Recommended Architecture**:

```python
# tui/common.py
class ChuckApplication:
    """Base class managing ChucK instance and shared state."""

    def __init__(self):
        from .. import ChucK
        self.chuck = ChucK()
        self.session = ChuckSession(self.chuck)

        # Shared UI state
        self.show_help = False
        self.show_shreds = False
        self.show_log = False

    def get_common_key_bindings(self):
        """Return key bindings common to all views."""
        # F1, F2, F3, Ctrl-Q, etc.
        pass

    def create_help_window(self):
        """Create common help window."""
        pass

    def create_shreds_table(self):
        """Create shreds table window."""
        pass

    def create_log_window(self):
        """Create log window."""
        pass
```

**Benefits**:
- Single ChucK instance shared across views
- Consistent UI behavior
- Reduced code duplication
- Easier to maintain

---

### 6. File Saving in `~/.pychuck/editor`

**Status**: ⚠️ Implementation Detail

**Concern**: Auto-saving every edit could create many files quickly.

**Questions**:
- Save on every keystroke, or periodic (e.g., every 30 seconds)?
- Save on explicit actions (Ctrl-S, spork, replace)?
- How many versions/backups to keep?
- File naming convention for untitled files?

**Recommended Strategy**:

```
~/.pychuck/editor/
  untitled-1698765432.ck            # Timestamped untitled files
  myfile.ck                          # Current version
  myfile.ck.backup1                  # Previous version
  myfile.ck.backup2                  # 2 versions back
  .autosave/                         # Periodic auto-saves
    myfile.ck.20251007-143022        # Timestamped auto-saves
```

**Auto-save Policy**:
- **Periodic**: Every 30 seconds if modified
- **On Action**: Before spork, replace, close tab
- **Explicit**: Ctrl-S saves to main file
- **Backup Rotation**: Keep last 5 backups
- **Cleanup**: Delete auto-saves older than 7 days

---

### 7. Chuck Command Integration

**Status**: ⚠️ Needs Detail

**From REFACTOR.md**: "repl should be able to access the chuck executable's commands"

**Questions**:
- Implement these commands in Python or shell out to `chuck` executable?
- Which commands are highest priority?
  - `add` / `+` (spork file)
  - `remove` / `-` (remove shred)
  - `replace` / `=` (replace shred)
  - `status` (show VM status)
  - `time` (show current time)
- How to handle on-the-fly (OTF) commands when audio isn't running?

**Recommendation**: **Implement in Python** using existing bindings.

```python
# tui/commands.py additions
class CommandExecutor:
    def handle_add_file(self, path):
        """Add (spork) a ChucK file as new shred."""
        success, shred_ids = self.session.chuck.compile_file(path)
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, path)
        return success, shred_ids

    def handle_replace_shred(self, shred_id, path):
        """Replace existing shred with new code from file."""
        code = Path(path).read_text()
        new_id = self.session.chuck.replace_shred(shred_id, code)
        self.session.remove_shred(shred_id)
        self.session.add_shred(new_id, path)
        return new_id

    def handle_status(self):
        """Show VM status."""
        all_ids = self.session.chuck.get_all_shred_ids()
        ready_ids = self.session.chuck.get_ready_shred_ids()
        blocked_ids = self.session.chuck.get_blocked_shred_ids()

        return {
            'total': len(all_ids),
            'ready': len(ready_ids),
            'blocked': len(blocked_ids),
            'time': self.session.chuck.now()
        }
```

**Priority Commands**:
1. ✅ `+` / `add` - Already have via `compile_file`
2. ✅ `-` / `remove` - Already have via `remove_shred`
3. ✅ `=` / `replace` - Already have via `replace_shred`
4. ⚠️ `status` - Need to implement
5. ⚠️ `time` - Already have via `now()`, just expose in REPL

---

## Missing Specifications

The following areas need specification before implementation:

1. **Error Handling in Editor**: How to display compilation errors?
   - Inline error markers?
   - Error pane at bottom?
   - Status bar only?

2. **File Watching**: Should editor watch for external file changes?
   - Prompt to reload if file changed externally?
   - Auto-reload?
   - Ignore?

3. **Syntax Validation**: Real-time or on spork?
   - Real-time could be expensive
   - On spork is simpler but less immediate feedback

4. **Configuration**: User preferences?
   - `~/.pychuck/config.toml` for settings?
   - Keybinding customization?
   - Color scheme selection?

5. **Help System**: Context-sensitive help?
   - Different help text for editor vs REPL?
   - Help for specific ChucK UGens/functions?

6. **Multiple ChucK Instances**: Can user run multiple editors/REPLs?
   - Share audio context?
   - Independent VMs?

---

## Implementation Plan

### Phase 1: Restructure & Extract Common Code (2-3 days)

**Goal**: Reorganize code without breaking existing functionality.

**Tasks**:

1. **Create new directory structure**:
   ```bash
   mkdir -p src/pychuck/cli
   mkdir -p src/pychuck/tui
   ```

2. **Move files**:
   - `cli/` → `tui/` (rename directory)
   - Keep existing files: `chuck_lexer.py`, `commands.py`, `parser.py`, `paths.py`, `session.py`, `repl.py`
   - Delete: `cli/tui.py` (merge into repl.py)

3. **Create new files**:
   - `cli/__init__.py` - Package marker
   - `cli/main.py` - CLI argument parsing
   - `cli/executor.py` - File execution logic
   - `tui/common.py` - Shared base class

4. **Update imports**:
   - Change all `from .cli.` → `from .tui.`
   - Update `__main__.py` to import from `cli.main`

**Deliverables**:
- ✅ New directory structure in place
- ✅ All imports updated
- ✅ Existing tests pass
- ✅ No functionality changes

**Code Sample - `tui/common.py`**:

```python
"""Shared TUI functionality for both editor and REPL modes."""

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.filters import Condition
from prompt_toolkit.widgets import TextArea

from .session import ChuckSession

class ChuckApplication:
    """Base application managing ChucK instance and shared state."""

    def __init__(self):
        from .. import ChucK
        self.chuck = ChucK()
        self.session = ChuckSession(self.chuck)

        # Shared UI state
        self.show_help = False
        self.show_shreds = False
        self.show_log = False

    def get_common_key_bindings(self):
        """Return key bindings common to all views."""
        kb = KeyBindings()

        @kb.add('c-q')
        def exit_app(event):
            """Ctrl-Q: Exit application"""
            event.app.exit()

        @kb.add('f1')
        def toggle_help(event):
            """F1: Toggle help window"""
            self.show_help = not self.show_help

        @kb.add('f2')
        def toggle_shreds(event):
            """F2: Toggle shreds table"""
            self.show_shreds = not self.show_shreds

        @kb.add('f3')
        def toggle_log(event):
            """F3: Toggle log window"""
            self.show_log = not self.show_log

        return kb

    def create_help_window(self, help_text):
        """Create common help window."""
        return ConditionalContainer(
            Window(
                content=FormattedTextControl(text=help_text),
                height=D(min=3, max=20),
                wrap_lines=True
            ),
            filter=Condition(lambda: self.show_help)
        )

    def create_shreds_table(self):
        """Create shreds table window."""
        def get_shreds_text():
            if not self.session.shreds:
                return "No active shreds"

            lines = ["ID | Name | Time"]
            lines.append("-" * 40)
            for sid, info in sorted(self.session.shreds.items()):
                lines.append(f"{sid:3d} | {info['name'][:20]:20s} | {info['time']:.2f}s")
            return "\n".join(lines)

        return ConditionalContainer(
            Window(
                content=FormattedTextControl(get_shreds_text),
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

        return ConditionalContainer(
            log_area,
            filter=Condition(lambda: self.show_log)
        )

    def create_status_bar(self, status_text_func):
        """Create bottom status bar."""
        return Window(
            content=FormattedTextControl(status_text_func),
            height=1,
            style='bg:#444444 fg:#ffffff'
        )
```

---

### Phase 2: Refactor CLI (1-2 days)

**Goal**: Implement new CLI API with subcommands.

**Tasks**:

1. Create `cli/main.py` with argparse subcommands
2. Create `cli/executor.py` for file execution
3. Update `__main__.py` to use new CLI
4. Test all CLI commands

**Deliverables**:
- ✅ `pychuck edit [files...]` command
- ✅ `pychuck repl [files...]` command
- ✅ `pychuck exec <file>` command with options
- ✅ `pychuck version` and `pychuck info` commands
- ✅ Backward compatibility maintained

**Code Sample - `cli/main.py`**:

```python
"""Main CLI entry point for pychuck."""

import sys
import argparse
from pathlib import Path

def create_parser():
    parser = argparse.ArgumentParser(
        prog='pychuck',
        description='Python bindings for ChucK audio programming language'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # edit subcommand
    edit_parser = subparsers.add_parser('edit', help='Launch interactive editor')
    edit_parser.add_argument('files', nargs='*', help='Files to open')
    edit_parser.add_argument('--start-audio', action='store_true')

    # repl subcommand
    repl_parser = subparsers.add_parser('repl', help='Launch interactive REPL')
    repl_parser.add_argument('files', nargs='*', help='Files to load')
    repl_parser.add_argument('--start-audio', action='store_true')
    repl_parser.add_argument('--no-smart-enter', action='store_true')

    # exec subcommand
    exec_parser = subparsers.add_parser('exec', help='Execute ChucK file(s)')
    exec_parser.add_argument('files', nargs='+', help='ChucK files')
    exec_parser.add_argument('--srate', type=int, default=44100)
    exec_parser.add_argument('--channels', type=int, default=2)
    exec_parser.add_argument('--bufsize', type=int, default=512)
    exec_parser.add_argument('--silent', action='store_true')
    exec_parser.add_argument('--loop', action='store_true')

    # version/info subcommands
    version_parser = subparsers.add_parser('version')
    info_parser = subparsers.add_parser('info')

    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command == 'edit':
        from ..tui.editor import main as editor_main
        editor_main(files=args.files, start_audio=args.start_audio)

    elif args.command == 'repl':
        from ..tui.repl import main as repl_main
        repl_main(files=args.files,
                 start_audio=args.start_audio,
                 smart_enter=not args.no_smart_enter)

    elif args.command == 'exec':
        from .executor import execute_files
        execute_files(args.files,
                     sample_rate=args.srate,
                     channels=args.channels,
                     buffer_size=args.bufsize,
                     silent=args.silent,
                     loop=args.loop)
    # ... version, info, etc.
```

---

### Phase 3: Refactor REPL (1-2 days)

**Goal**: Simplify REPL using common components, add file loading.

**Tasks**:

1. Update `tui/repl.py` to use `ChuckApplication` base
2. Add file loading support (`files` parameter)
3. Change log toggle from `Ctrl-L` to `F3`
4. Add `load` command for loading files during session
5. Test all existing features still work

**Deliverables**:
- ✅ REPL uses `ChuckApplication` base
- ✅ Can load files on startup: `pychuck repl file1.ck file2.ck`
- ✅ `load <file>` command works during session
- ✅ All existing features preserved
- ✅ Tests updated and passing

**Key Changes to `tui/repl.py`**:

```python
from .common import ChuckApplication

class ChuckREPL:
    def __init__(self, smart_enter=True, files=None):
        self.app = ChuckApplication()  # Use common base
        self.smart_enter = smart_enter
        self.files_to_load = files or []
        # ... rest of initialization ...

    def initialize(self):
        """Initialize REPL and load any files."""
        self.app.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.app.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.app.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.app.chuck.init()

        # Load files if provided
        for file_path in self.files_to_load:
            success, ids = self.app.chuck.compile_file(file_path)
            if success:
                for sid in ids:
                    self.app.session.add_shred(sid, file_path)
                print(f"Loaded {file_path}: shreds {ids}")
            else:
                print(f"Failed to load {file_path}")

def main(files=None, start_audio=False, smart_enter=True):
    """Main entry point for REPL."""
    repl = ChuckREPL(smart_enter=smart_enter, files=files)
    repl.initialize()

    if start_audio:
        repl.start_audio()

    repl.run()
```

---

### Phase 4: Implement Editor (3-4 days)

**Goal**: Create new editor mode with file editing, saving, and sporking.

**Tasks**:

1. Create `tui/editor.py` with multi-tab support
2. Implement `EditorTab` class for individual files
3. Implement syntax highlighting with ChuckLexer
4. Add keybindings (F5=spork, F6=replace, Ctrl-S=save, etc.)
5. Implement auto-save to `~/.pychuck/editor/`
6. Add file loading from CLI
7. Integrate with `ChuckApplication` base
8. Test thoroughly

**Deliverables**:
- ✅ Multi-tab editor working
- ✅ Spork (F5) and Replace (F6) functional
- ✅ File save/load working
- ✅ Auto-save implemented
- ✅ Syntax highlighting with ChuckLexer
- ✅ Shared F1/F2/F3 windows working
- ✅ Can launch with: `pychuck edit file1.ck file2.ck`

**Architecture**:

```python
# tui/editor.py

class EditorTab:
    """Represents a single file being edited."""

    def __init__(self, file_path=None):
        self.file_path = Path(file_path) if file_path else None
        self.modified = False
        self.shred_id = None  # Track if code is sporked
        self.text_area = TextArea(
            text=self.load_content(),
            multiline=True,
            scrollbar=True,
            lexer=PygmentsLexer(ChuckLexer)
        )

    @property
    def name(self):
        """Display name with indicators."""
        name = self.file_path.name if self.file_path else "untitled"
        if self.modified:
            name += "*"
        if self.shred_id is not None:
            name += f" [{self.shred_id}]"
        return name

class ChuckEditor:
    """Multi-tab ChucK editor with live coding features."""

    def __init__(self, start_audio=False):
        self.app_state = ChuckApplication()
        self.tabs = []
        self.current_tab_index = 0

    def create_key_bindings(self):
        kb = self.app_state.get_common_key_bindings()

        @kb.add('f5')
        def spork_code(event):
            """Spork current buffer as new shred"""
            # ... implementation ...

        @kb.add('f6')
        def replace_shred(event):
            """Replace existing shred"""
            # ... implementation ...

        @kb.add('c-s')
        def save_file(event):
            """Save current file"""
            # ... implementation ...

        return kb
```

---

### Phase 5: Testing & Documentation (1-2 days)

**Goal**: Ensure everything works and is documented.

**Tasks**:

1. **Manual testing**:
   - Test all CLI commands
   - Test editor features (tabs, spork, replace, save)
   - Test REPL features with file loading
   - Test on macOS (primary platform)

2. **Automated testing**:
   - Add tests for CLI argument parsing
   - Add tests for file loading in REPL
   - Add tests for editor file operations
   - Ensure existing tests still pass

3. **Documentation**:
   - Update README.md with new CLI commands
   - Update CLAUDE.md with new structure
   - Add docstrings to new functions
   - Create usage examples

4. **Polish**:
   - Fix any bugs found during testing
   - Improve error messages
   - Add user-friendly help text

**Deliverables**:
- ✅ All tests passing
- ✅ README.md updated
- ✅ CLAUDE.md updated
- ✅ No regressions in existing functionality

**Test Commands**:
```bash
# Test CLI
pychuck edit
pychuck edit examples/basic/blit2.ck
pychuck repl
pychuck repl --start-audio
pychuck repl examples/basic/blit2.ck
pychuck exec examples/basic/blit2.ck
pychuck exec examples/basic/blit2.ck --silent
pychuck version
pychuck info

# Test REPL commands
+ examples/basic/blit2.ck
- 1
status
help

# Test editor keybindings
# F5 to spork
# F6 to replace
# Ctrl-S to save
# Ctrl-T for new tab
# F1/F2/F3 for help/shreds/log
```

---

## Timeline Summary

| Phase | Duration | Critical Path? |
|-------|----------|----------------|
| Phase 1: Restructure | 2-3 days | Yes |
| Phase 2: CLI | 1-2 days | Yes |
| Phase 3: REPL | 1-2 days | Yes |
| Phase 4: Editor | 3-4 days | Yes |
| Phase 5: Testing/Docs | 1-2 days | Yes |
| **Total** | **8-13 days** | |

**Critical Path**: All phases are sequential and on critical path.

**Buffer**: 5 days of buffer built into estimates (8-13 day range).

---

## Risk Assessment

### Low Risk Items ✅

- Phase 1 (Restructure): No functionality changes, only moving files
- Phase 2 (CLI): Additive changes, existing code untouched
- Phase 3 (REPL): Refactoring with tests to catch regressions

### Medium Risk Items ⚠️

- Phase 4 (Editor): New code, complexity in tab management and state tracking
- Integration between editor and ChucK instance (shred tracking)

### Mitigation Strategies

1. **Incremental Development**: Each phase is independently testable
2. **Preserve Existing Features**: Phase 1-3 don't break current functionality
3. **Test Coverage**: Add tests at each phase
4. **User Feedback**: Test with real usage patterns during Phase 5

---

## Open Questions for Stakeholder

Before starting implementation, please clarify:

1. **Editor Tabs**: Confirm multi-tab approach is correct
2. **Auto-save Frequency**: Every 30 seconds acceptable? Alternative preference?
3. **Error Display**: How should compilation errors be shown in editor?
4. **Configuration File**: Should we add `~/.pychuck/config.toml` for user preferences?
5. **CLI Style**: Confirm preference for Option A (explicit subcommands) over Option B (Chuck-style)
6. **File Watching**: Should editor detect external file changes?
7. **REPL Improvements**: Any specific features beyond file loading?

---

## Conclusion

The refactoring plan is **solid and ready for implementation** pending clarification on the above questions. The phased approach minimizes risk while delivering significant architectural improvements.

**Key Benefits**:
- ✅ Clear separation between editor and REPL modes
- ✅ Reduced code duplication via `ChuckApplication` base
- ✅ Improved CLI with subcommand structure
- ✅ File loading support in both modes
- ✅ Multi-tab editor for live coding workflows
- ✅ Consistent UI (F1/F2/F3 shortcuts across modes)

**Estimated Effort**: 8-13 days (1.5-2.5 weeks)

**Next Steps**:
1. Review and answer open questions
2. Approve final directory structure
3. Begin Phase 1 implementation

Ready to proceed? 🚀
