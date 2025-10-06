# Debugging Black Screen in Rich TUI

## Problem
When running `python -m pychuck tui --rich`, the screen appears black/blank even though textual is installed.

## Diagnostic Steps

### 1. Verify Textual Installation

```bash
python3 -c "import textual; print('Textual version:', textual.__version__)"
```

If this fails with `ModuleNotFoundError`, install textual:
```bash
pip install textual
# or
pip install pychuck[tui]
```

### 2. Test Minimal Textual App

Run the minimal test app to verify textual works:

```bash
python3 test_textual_minimal.py
```

If this shows a blank screen too, the issue is with textual or your terminal, not pychuck.

### 3. Test Simple TUI

We've created a simplified TUI with minimal widgets and inline CSS:

```bash
python -m pychuck tui --simple
```

This uses:
- No external CSS file
- Simple layout (Header, RichLog, Input, Footer)
- Mouse disabled
- Minimal complexity

If this works but `--rich` doesn't, the issue is with the complex CSS or widget arrangement.

## Common Causes

### 1. Terminal Compatibility
Some terminals don't handle certain textual features well:
- Try a different terminal (iTerm2, Terminal.app, Alacritty, kitty)
- Check if running in tmux/screen (can cause issues)
- Try without any terminal multiplexer

### 2. CSS Issues
The external CSS file might have syntax errors or incompatible styles:
- Check if `tui_rich.tcss` loads correctly
- Look for CSS syntax errors
- Test with inline CSS (use `--simple`)

### 3. Layer Problems
The CSS uses layers which might not render correctly:
```css
Screen {
    layers: sidebar base;
}
```

### 4. Grid Layout Issues
Complex grid layouts can fail to render:
```css
#main-container {
    layout: grid;
    grid-size: 2 2;
    grid-columns: 3fr 1fr;
    grid-rows: 1fr auto;
}
```

### 5. Widget Initialization
Widgets might fail to initialize properly, especially:
- DirectoryTree (file browser)
- Tree widgets (shreds/globals)
- ScrollableContainer

## Debugging Commands

```bash
# 1. Check textual version
python3 -c "import textual; print(textual.__version__)"

# 2. Try minimal textual app
python3 test_textual_minimal.py

# 3. Try simplified pychuck TUI
python -m pychuck tui --simple

# 4. Try full rich TUI
python -m pychuck tui --rich

# 5. Enable textual devtools (if installed)
textual run --dev python -m pychuck tui --rich

# 6. Check for errors in textual console
textual console
# Then in another terminal:
python -m pychuck tui --rich
```

## Textual Devtools

Install textual devtools for better debugging:

```bash
pip install textual-dev
```

Then run with dev mode:

```bash
textual run --dev src/pychuck/cli/tui_simple.py
```

This opens a separate console showing:
- Widget tree
- Layout information
- CSS application
- Log messages
- Errors

## Manual Testing Checklist

- [ ] Textual is installed (`import textual` works)
- [ ] Minimal textual app works (`test_textual_minimal.py`)
- [ ] Simplified TUI works (`--simple` flag)
- [ ] Terminal is compatible (not in tmux/screen)
- [ ] Terminal supports 256 colors
- [ ] No errors in textual console
- [ ] CSS file exists and is readable
- [ ] Mouse is disabled (`mouse_enabled = False`)

## Workarounds

### Use Simplified TUI
If the rich TUI doesn't work, use the simplified version:

```bash
python -m pychuck tui --simple
```

Features:
- Same ChucK functionality
- Simpler UI (no file browser, no trees)
- More reliable rendering
- Inline CSS (no external file)

### Use Vanilla REPL
The vanilla REPL always works:

```bash
python -m pychuck tui
```

Features:
- Tab completion
- Command history
- No graphical UI needed
- Most reliable option

## Reporting Issues

If you still see a black screen, please report with:

1. **Textual version**: `python3 -c "import textual; print(textual.__version__)"`
2. **Terminal**: Which terminal app (iTerm2, Terminal.app, etc.)
3. **OS**: macOS version, Linux distro, etc.
4. **Works?**: Does `test_textual_minimal.py` work?
5. **Works?**: Does `--simple` flag work?
6. **Errors**: Any errors in textual console?
7. **TERM**: Value of `$TERM` environment variable

## Next Steps

1. **Try simple TUI first**: `python -m pychuck tui --simple`
2. **If that works**: The issue is with the complex CSS/layout
3. **If that fails**: The issue is with textual/terminal compatibility
4. **If nothing works**: Use vanilla REPL (`python -m pychuck tui`)

## Technical Details

### Simple TUI
- File: `src/pychuck/cli/tui_simple.py`
- CSS: Inline, minimal
- Widgets: Header, RichLog, Input, Footer
- Layout: Simple docking
- Mouse: Disabled

### Rich TUI
- File: `src/pychuck/cli/tui_rich.py`
- CSS: External file (`tui_rich.tcss`)
- Widgets: Header, Footer, RichLog, Input, DirectoryTree, Tree (x2), Labels
- Layout: Grid with layers
- Mouse: Disabled

### Differences
Rich TUI adds:
- External CSS file
- Grid layout
- Layers (sidebar, base)
- DirectoryTree widget
- Tree widgets
- ScrollableContainer
- More complex widget hierarchy

Any of these could cause rendering issues on certain terminals.
