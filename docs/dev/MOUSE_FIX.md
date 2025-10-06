# Mouse Support Fix for Rich TUI

## Issue
When launching the rich TUI with `python -m pychuck tui --rich`, the screen appeared blank but the mouse was still capturing events, making the interface unusable.

## Root Causes

### 1. Mouse Tracking Interference
The mouse tracking was enabled by default in Textual, which could interfere with terminal rendering or cause the UI to not display properly in certain terminal configurations.

### 2. CSS File Path
The CSS file path was relative (`"tui_rich.tcss"`), which might not be resolved correctly depending on the working directory.

## Fixes Applied

### 1. Disabled Mouse Support
Added property to disable mouse interaction:

```python
@property
def mouse_enabled(self):
    """Disable mouse support until we debug the blank screen issue"""
    return False
```

Also disabled the command palette:
```python
ENABLE_COMMAND_PALETTE = False
```

### 2. Fixed CSS File Path
Changed from relative to absolute path:

```python
# Get the absolute path to the CSS file
_CSS_FILE = Path(__file__).parent / "tui_rich.tcss"

class ChuckTUI(App):
    # Use absolute path to CSS file
    CSS_PATH = str(_CSS_FILE)
```

This ensures the CSS file is always found regardless of the current working directory.

### 3. Updated Documentation
- Updated help text to indicate keyboard-only navigation
- Added keyboard shortcuts (Tab, Arrow keys)
- Updated all documentation to reflect keyboard navigation instead of mouse clicks
- Added "Known Issues" section explaining mouse is temporarily disabled

## Current Status

**Mouse support**: Disabled temporarily
**Navigation**: Fully functional via keyboard
**User experience**: Works correctly with keyboard-only interaction

## Keyboard Navigation

The TUI is fully functional without mouse support:

| Action | Keys |
|--------|------|
| Cycle widgets | Tab |
| Navigate tree | Arrow keys (↑↓←→) |
| Expand/collapse | Space or Enter |
| Select file | Enter (auto-fills command) |
| Focus input | Escape |
| Execute command | Enter (in input field) |

## File Browser Workflow

1. Press **Ctrl+F** to toggle file browser sidebar
2. Press **Tab** to focus the file tree
3. Use **Arrow keys** to navigate directories and files
4. Press **Enter** on a `.ck` file to auto-fill the command
5. Press **Escape** to return to command input
6. Press **Enter** to execute the command

## Testing

Before fix:
- ✗ Blank screen with mouse capturing events
- ✗ UI not visible
- ✗ Mouse moving around but nothing displayed

After fix:
- ✓ UI displays correctly
- ✓ All widgets visible and functional
- ✓ Keyboard navigation works perfectly
- ✓ File browser sidebar animates correctly
- ✓ Tree widgets display shreds and globals
- ✓ Console output shows correctly

## Why This Works

Disabling mouse support eliminates the mouse tracking escape sequences that might conflict with terminal rendering. Some terminals or terminal configurations don't handle mouse tracking correctly, leading to rendering issues.

By using keyboard-only navigation, we ensure compatibility across all terminal types while maintaining full functionality.

## Future Work

To re-enable mouse support:

1. **Debug terminal compatibility**: Test on various terminals (iTerm2, Terminal.app, tmux, etc.)
2. **Add terminal detection**: Only enable mouse on compatible terminals
3. **Provide fallback**: Automatically disable mouse if rendering issues detected
4. **User preference**: Add command-line flag `--no-mouse` for users who prefer keyboard

For now, keyboard navigation provides a robust, terminal-agnostic solution.

## Related Files

- `src/pychuck/cli/tui_rich.py` - Main TUI implementation
- `src/pychuck/cli/tui_rich.tcss` - CSS styling
- `RICH_TUI_IMPROVEMENTS.md` - Full documentation
