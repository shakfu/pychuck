# Tab Completion Test Guide

The vanilla REPL now has full tab completion support for both commands and file paths.

## How to Test

1. **Start the vanilla REPL:**
   ```bash
   python -m pychuck tui
   ```

2. **Test command completion:**
   - Type `ex` and press Tab → should complete to `exit`
   - Type `he` and press Tab → should complete to `help`
   - Type `?` and press Tab → should show `?`, `?a`, `?g`
   - Type empty string and press Tab → should show all commands

3. **Test path completion:**
   - Type `examples/` and press Tab → should show directories in examples/
   - Type `examples/basic/` and press Tab → should show .ck files in that directory
   - Type `~/` and press Tab → should expand home directory and show contents

## Implementation Details

The REPL uses two completion backends:

### Primary: prompt_toolkit (preferred)
If `prompt_toolkit` is installed, it provides:
- Command completion with all ChucK REPL commands
- Path completion filtered for `.ck` files and directories
- Case-insensitive matching
- Auto-suggest from history
- Complete on Tab only (not while typing)

### Fallback: readline
If `prompt_toolkit` is not available, falls back to `readline`:
- Same command and path completion functionality
- Detects macOS libedit vs GNU readline and configures appropriately
- History saved to `~/.chuck_repl_history`

## Commands That Complete

- `+`, `-`, `~` (shred management)
- `?`, `?g`, `?a` (status queries)
- `clear`, `reset` (VM control)
- `>`, `||`, `X` (audio control)
- `.` (current time)
- `all`, `$`, `:`, `!` (special commands)
- `help`, `quit`, `exit` (utility)

## File Completion

- Filters for `.ck` files only
- Shows directories (with trailing `/`)
- Supports `~` expansion for home directory
- Works with relative and absolute paths
