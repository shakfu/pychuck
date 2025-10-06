# ChucK REPL / TUI

Interactive REPL for pychuck with optional rich terminal interface.

## Installation

```bash
# Base installation (vanilla REPL only)
pip install -e .

# With prompt-toolkit (better vanilla REPL)
pip install -e .[repl]

# With textual (rich TUI)
pip install -e .[tui]

# Everything
pip install -e .[all]
```

## Usage

```bash
# Launch TUI (auto-detects textual, falls back to vanilla)
PYTHONPATH=src python3 -m pychuck tui

# Force rich TUI (fails if textual not installed)
PYTHONPATH=src python3 -m pychuck tui --rich

# Show version
PYTHONPATH=src python3 -m pychuck version

# Show ChucK info
PYTHONPATH=src python3 -m pychuck info
```

## DSL Commands

### Shred Management
```
+ sine.ck                    # Spork file
+ "SinOsc s => dac;"         # Spork code
- 42                         # Remove shred ID 42
- all                        # Remove all shreds
~ 42 "TriOsc t => dac;"      # Replace shred 42
```

### Status/Introspection
```
?                            # Show all shreds
? 42                         # Show shred info
?g                           # Show globals
?a                           # Show audio info
.                            # Show current time
```

### Global Variables
```
gain::0.5                    # Set global float
freq::440                    # Set global int/float
msg::"hello"                 # Set global string
notes::[60,64,67]            # Set global array
gain?                        # Get global (async)
```

### Events
```
kick!                        # Signal event
kick!!                       # Broadcast event
```

### Audio Control
```
>                            # Start audio
||                           # Stop audio
X                            # Shutdown audio
```

### VM Control
```
clear                        # Clear VM
reset                        # Reset shred ID counter
```

### Other
```
: sine.ck                    # Compile without running
! "<<< now >>>"              # Execute code immediately
$ ls examples/               # Run shell command
help                         # Show help
quit                         # Exit
```

## Vanilla REPL Features

The vanilla REPL has three modes:
- **prompt-toolkit mode** (best): Full history, auto-suggestions, tab completion
- **readline mode** (good): Arrow-up/down history navigation, saved history file
- **basic mode** (fallback): Simple input without history

History is automatically saved to `~/.chuck_repl_history` and persists across sessions.

## Rich TUI Features

When textual is installed and `--rich` is used:

- **4-panel grid layout**:
  - Console (left): Command input/output with syntax highlighting
  - Shreds (top right): Live table of running shreds with status
  - Globals (middle right): List of global variables
  - Audio (bottom right): Audio system status and info

- **Keybindings**:
  - `Ctrl+C`: Quit
  - `Ctrl+L`: Clear console
  - `Ctrl+S`: Toggle audio on/off
  - `Ctrl+R`: Remove all shreds
  - `Escape`: Focus input

- **Live updates**: UI panels refresh automatically after operations

## Examples

### Basic Usage
```bash
$ PYTHONPATH=src python3 -m pychuck tui
ChucK REPL v0.1.0 (vanilla mode)
Type 'help' for commands, 'quit' to exit

chuck> >
audio started

chuck> + "SinOsc s => dac; 440 => s.freq; 1::second => now;"
sporked code -> shred 1

chuck> ?
ID       Name
--------------------------------------------------
1        inline:SinOsc s => dac; 44...

chuck> - 1
removed shred 1

chuck> quit
Shutting down...
```

### With File
```bash
chuck> + examples/test/sine.ck
sporked examples/test/sine.ck -> shred 2

chuck> ?a
Sample rate: 44100 Hz
Channels out: 2
Channels in: 0
Buffer size: 512
```

### Global Variables
```bash
chuck> gain::0.3
set gain = 0.3

chuck> gain?
gain = 0.3

chuck> notes::[60,64,67,72]
set notes = [60, 64, 67, 72]

chuck> ?g
Type                 Name
----------------------------------------------------
float                gain
int[]                notes
```

## Architecture

```
src/pychuck/
├── __main__.py              # CLI entry point
├── cli/
│   ├── __init__.py
│   ├── tui.py               # Dispatcher (textual vs vanilla)
│   ├── tui_rich.py          # Textual TUI implementation
│   ├── repl.py              # Vanilla REPL
│   ├── parser.py            # DSL command parser
│   ├── session.py           # Session state management
│   ├── commands.py          # Command executor
│   └── widgets/             # Textual widgets
│       ├── shred_list.py
│       ├── globals_panel.py
│       └── audio_meter.py
```

## Design Decisions

1. **ChucK-friendly syntax**: Uses familiar ChucK operators (`+`, `-`, `~`) for live coding
2. **Graceful fallback**: Works without any dependencies, better with prompt-toolkit, best with textual
3. **Explicit `--rich` flag**: Users can force rich mode or let it auto-detect
4. **Shared core**: Parser, session, and executor work identically in both modes
5. **Live coding focus**: Optimized for interactive shred manipulation

## Future Enhancements

- Code editor pane for editing .ck files
- Waveform visualization
- File browser for examples
- Multiple console tabs
- Theme customization
- MIDI/OSC control integration
