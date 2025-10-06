# Vanilla REPL Features

The pychuck vanilla REPL is the default interactive interface, optimized for daily use with full tab completion and command history.

## Launch

```bash
python -m pychuck tui
```

## Features

### Tab Completion

**Commands**: All ChucK REPL commands complete on Tab:
- `+`, `-`, `~`, `?`, `?g`, `?a`
- `clear`, `reset`, `>`, `||`, `X`, `.`
- `all`, `$`, `:`, `!`, `help`, `quit`, `exit`

**File Paths**: Smart completion for `.ck` files:
- Filters to show only `.ck` files and directories
- Supports `~` home directory expansion
- Works with relative and absolute paths
- Shows directories with trailing `/`

**Case-Insensitive**: Commands match regardless of case (e.g., `EX` → `exit`)

### Command History

- **Persistent**: History saved to `.chuck_repl_history` across sessions
- **Navigation**: Up/Down arrows to browse history
- **Auto-suggest**: Shows suggestions from history as you type (prompt_toolkit mode)
- **Smart**: Avoids duplicate consecutive entries

### Implementation

**Two-tier fallback system**:

1. **prompt_toolkit** (preferred if installed):
   - Rich completion with dropdown menu
   - Auto-suggest from history
   - Better key bindings
   - Color support

2. **readline** (built-in fallback):
   - Basic tab completion
   - Works on all platforms
   - macOS libedit compatibility
   - Minimal dependencies

The REPL automatically detects and uses the best available backend.

## ChucK REPL Commands

### Shred Management
```
+ <file.ck>           Spork file
+ "<code>"            Spork code string
- <id>                Remove shred by ID
- all                 Remove all shreds
~ <id> "<code>"       Replace running shred with new code
```

### Status Queries
```
?                     List all running shreds
? <id>                Show detailed info for shred ID
?g                    List global variables
?a                    Show audio system info
.                     Display current VM time
```

### Global Variables
```
name::value           Set global variable (int, float, string)
name?                 Get global variable value (async)
```

### Event Signaling
```
event!                Signal event (wake one listener)
event!!               Broadcast event (wake all listeners)
```

### Audio Control
```
>                     Start real-time audio
||                    Stop audio (pause)
X                     Shutdown audio system
```

### VM Control
```
clear                 Clear VM (remove all shreds)
reset                 Reset shred ID counter
```

### Utilities
```
: <file>              Compile file without running
! "<code>"            Execute code immediately
$ <cmd>               Run shell command
help                  Show help
quit / exit           Exit REPL
```

## Usage Tips

### Tab Completion Examples

```bash
chuck> ex<TAB>              # Completes to: exit
chuck> + examples/<TAB>     # Shows subdirectories in examples/
chuck> + examples/basic/<TAB>  # Shows .ck files in examples/basic/
chuck> ?<TAB>               # Shows: ?, ?a, ?g
```

### History Navigation

```bash
chuck> + examples/basic/foo.ck
chuck> <UP>                 # Recalls previous command
chuck> <DOWN>               # Moves forward in history
```

### Quick Commands

```bash
# Spork a file
chuck> + mycode.ck

# Check what's running
chuck> ?

# Remove everything
chuck> - all

# Start audio
chuck> >

# Stop audio
chuck> X
```

## Keyboard Shortcuts

- **Tab**: Complete command or path
- **Up/Down**: Navigate command history
- **Ctrl+C**: Interrupt current line (continue REPL)
- **Ctrl+D**: Exit REPL
- **Ctrl+L**: Clear screen (if supported by terminal)

## Configuration

The REPL respects standard readline configuration (`~/.inputrc`) when using readline mode.

Example `~/.inputrc`:
```
# Case-insensitive completion
set completion-ignore-case on

# Show all completions immediately
set show-all-if-ambiguous on

# Use visible bell instead of audible
set bell-style visible
```

## Environment

The REPL initializes ChucK with these defaults:
- Sample rate: 44100 Hz
- Output channels: 2 (stereo)
- Input channels: 0

These can be changed using ChucK REPL commands after startup.

## Output Capture

ChucK output is captured and displayed with prefixes:
- `[chout]` - ChucK stdout messages
- `[cherr]` - ChucK stderr/error messages

## Memory Management

The vanilla REPL properly cleans up resources on exit:
- Stops audio gracefully
- Removes all running shreds
- Breaks circular references to prevent nanobind leaks
- Saves command history

This ensures clean shutdown with no memory leaks.

## Comparison with Rich TUI

| Feature | Vanilla REPL | Rich TUI |
|---------|-------------|----------|
| Tab completion | ✓ | ✓ |
| Command history | ✓ (persistent) | ✓ |
| Dependencies | readline/prompt_toolkit | textual |
| Syntax highlighting | ✗ | ✓ |
| Mouse support | ✗ | ✓ |
| Split panes | ✗ | ✓ |
| Startup time | Instant | ~1s |
| Resource usage | Minimal | Moderate |
| Works over SSH | ✓ | ✓ |
| Pipeable | ✓ | ✗ |

**Use vanilla REPL for**: Daily development, quick tests, scripting, low-latency response

**Use rich TUI for**: Visual coding sessions, learning ChucK, when syntax highlighting helps

## Troubleshooting

**Tab completion not working:**
- Check if prompt_toolkit is installed: `pip install prompt_toolkit`
- On macOS, built-in readline uses libedit (works but basic)
- Try `pip install gnureadline` for better GNU readline

**History not saving:**
- Check permissions on `.chuck_repl_history` file
- Ensure clean exit (don't kill process)

**Colors not showing:**
- Some terminals have limited color support
- Try setting `TERM=xterm-256color`

**Completion shows wrong files:**
- Completion filters to `.ck` files only by design
- Use full paths for non-.ck files

## See Also

- [COMPLETION_TEST.md](COMPLETION_TEST.md) - Tab completion testing guide
- `python -m pychuck tui --help` - Command-line help
- Type `help` in REPL - Command reference
