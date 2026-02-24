# Model/View Separation

**Status: Implemented**

This document describes the service layer architecture that separates business logic from UI concerns.

## Architecture Overview

```text
CLI Layer (cli/)              TUI Layer (tui/)
    |                              |
    +-------------+----------------+
                  |
         Service Layer (services/)
         |- audio.py     - AudioService
         |- shreds.py    - ShredService
         |- globals.py   - GlobalsService
         |- files.py     - FileService
                  |
         Domain Layer
         |- session.py   - ChuckSession (state tracking)
         |- project.py   - Project (file versioning)
         |- api.py       - Chuck wrapper (core API)
```

## Service Layer (`src/numchuck/services/`)

### AudioService (`audio.py`)

Manages audio lifecycle for ChucK instances.

```python
from numchuck.services import AudioService

audio = AudioService(chuck)
audio.start()      # Start real-time audio
audio.stop()       # Stop and shutdown audio
audio.restart()    # Stop then start
audio.is_running   # Check state

# Optional callbacks
audio.set_callbacks(on_start=..., on_stop=...)
```

**Features:**

- Consistent start/stop/shutdown with error handling
- State tracking via `is_running` property
- Configurable shutdown timeout
- Optional callbacks for state changes
- Used by both CLI (`executor.py`, `watcher.py`) and TUI (`common.py`)

### ShredService (`shreds.py`)

Manages shred compilation, replacement, and removal.

```python
from numchuck.services import ShredService

shreds = ShredService(chuck, session)

# Spork operations
result = shreds.spork_code("SinOsc s => dac;")
result = shreds.spork_file("sound.ck")

# Returns ShredResult with:
result.success      # bool
result.shred_ids    # list[int]
result.shred_id     # first ID or None
result.error        # error message or None

# Shred management
shreds.replace_shred(old_id, new_code)
shreds.replace_shred_file(old_id, "new.ck")
shreds.remove_shred(shred_id)
shreds.remove_all()

# VM operations
shreds.clear_vm()
shreds.reset_shred_id()
shreds.compile_file(path)  # Syntax check only
shreds.exec_code(code)     # Immediate execution

# Query
shreds.list_shreds()           # list[int]
shreds.get_shred_info(id)      # ShredInfo
```

**Features:**

- Structured `ShredResult` return type (not formatted strings)
- Automatic session tracking when session provided
- Project integration for versioning
- Used by `CommandExecutor` for all shred commands

### GlobalsService (`globals.py`)

Manages global variables and events.

```python
from numchuck.services import GlobalsService

globals = GlobalsService(chuck)

# Set globals (auto-detects type)
globals.set_global("freq", 440)         # int
globals.set_global("amp", 0.5)          # float
globals.set_global("name", "sine")      # string
globals.set_global("notes", [60, 64])   # int array

# Get globals
globals.get_global_int("freq")          # int | None
globals.get_global_float("amp")         # float | None
globals.get_global_string("name")       # str | None
globals.get_global("freq")              # ("int", 440) or None

# List all globals
for info in globals.list_globals():
    print(f"{info.type}: {info.name}")

# Events
globals.signal_event("trigger")
globals.broadcast_event("reset")
```

**Features:**

- Type-aware setters with automatic detection
- Structured `GlobalInfo` return type for listing
- Clean event signaling/broadcasting
- Used by `CommandExecutor` for all global/event commands

### FileService (`files.py`)

Manages snippets and project files.

```python
from numchuck.services import FileService

files = FileService(session)

# Snippets
snippet = files.load_snippet("sine")
if snippet:
    print(f"Path: {snippet.path}")
    print(f"Source: {snippet.source}")  # "local" or "global"
    print(f"Content: {snippet.content}")

for snippet in files.list_snippets():
    print(f"@{snippet.name} ({snippet.source})")

# Directories
snippets_dir = files.get_snippets_dir()
files.ensure_directories()

# Project integration
files.save_to_project(name, content, shred_id)
files.save_replacement_to_project(shred_id, content)

# File reading
content = files.read_file("sound.ck")
```

**Features:**

- Structured `SnippetInfo` return type
- Local/global snippet resolution
- Project versioning integration
- Directory management

## TUI Widgets (`src/numchuck/tui/widgets.py`)

Reusable UI component factories:

```python
from numchuck.tui.widgets import (
    create_help_window,
    create_shreds_table,
    create_log_window,
    create_status_bar,
    create_message_area,
)

# Help window with show/hide condition
help_window = create_help_window(
    show_condition=lambda: app.show_help,
    help_text="Press F1 for help...",
)

# Shreds table with dynamic content
shreds_table = create_shreds_table(
    show_condition=lambda: app.show_shreds,
    get_table_text=lambda: generate_shreds_table(session.shreds, chuck),
)

# Log window (returns container and textarea)
log_container, log_area = create_log_window(
    show_condition=lambda: app.show_log,
)

# Status bar
status_bar = create_status_bar(
    status_text_func=lambda: f"Shreds: {len(session.shreds)}",
)
```

## Data Flow

### Sporking a File (After Refactoring)

```text
User input
    |
CommandParser.parse() -> Command
    |
CommandExecutor._cmd_spork_file()
    |
ShredService.spork_file()
    +-- Read file content
    +-- Chuck.compile_file()
    +-- Session.add_shred()
    +-- Project.save_on_spork() (if project)
    +-- Return ShredResult
    |
UI: Display result or error
```

### Audio Control (After Refactoring)

```text
CLI executor.py / TUI commands.py
    |
AudioService.start() / .stop()
    +-- _numchuck.start_audio() / stop_audio()
    +-- State tracking
    +-- Callbacks (optional)
    +-- Return success/failure
```

## Component Summary

| Component | Role | Dependencies |
|-----------|------|--------------|
| `AudioService` | Audio lifecycle | `_numchuck` bindings |
| `ShredService` | Shred operations | `Chuck`, `ChuckSession` |
| `GlobalsService` | Global vars/events | `Chuck` |
| `FileService` | Snippets/projects | `ChuckSession`, `paths` |
| `CommandExecutor` | Command dispatch | All services |
| `ChuckApplication` | TUI base class | `AudioService`, services, `widgets` |
| `widgets` | UI component factories | `prompt_toolkit` |

## Test Coverage

Tests in `tests/test_services.py` cover:

- AudioService: start/stop/restart, callbacks, state tracking
- ShredService: spork/replace/remove, session integration
- GlobalsService: set/get operations, events, listing
- FileService: snippet loading, directory management

Tests in `tests/test_widgets.py` cover:

- `create_help_window`: container creation, visibility conditions, custom heights
- `create_shreds_table`: container creation, visibility conditions, custom heights
- `create_log_window`: container and textarea creation, provided vs new textarea
- `create_status_bar`: window creation, default/custom styles, height
- `create_message_area`: textarea creation, read-only settings, focusability

## Design Principles

1. **Services are stateless** - Dependencies passed via constructor
2. **Structured results** - Services return dataclasses, not formatted strings
3. **Single responsibility** - Each service has one concern
4. **CLI uses same services as TUI** - Shared business logic
5. **No UI in services** - Pure business logic only
