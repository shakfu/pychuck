# Rich TUI Improvements

The pychuck textual-based TUI has been significantly improved based on patterns from the official Textual examples library.

## What Changed

### Before
- Inline CSS styling
- Static shred display with Label
- No file browser
- Basic layout
- Manual UI updates
- Debug output in console

### After
- **External CSS file** (`tui_rich.tcss`) - cleaner separation of concerns
- **Animated file browser sidebar** - toggleable with Ctrl+F
- **Tree widgets** for shreds and globals - hierarchical display with expandable nodes
- **DirectoryTree widget** - browse `.ck` files in filesystem
- **Better reactive updates** - automatic subtitle updates when shreds/audio changes
- **Click-to-load files** - click `.ck` files in sidebar to auto-fill command
- **Improved cleanup** - proper memory management on exit
- **Better threading** - uses `call_from_thread` for ChucK callbacks

## New Features

### File Browser Sidebar
- **Toggle**: Press `Ctrl+F` to slide in/out
- **Navigation**: Use arrow keys to browse directories and `.ck` files
- **Select to load**: Press Enter on any `.ck` file to auto-fill `+ <file>` in command input
- **Animated**: Smooth slide-in animation using CSS transitions
- **Note**: Mouse support is currently disabled (keyboard navigation only)

### Tree Widgets
- **Shred Tree**: Shows running shreds with expandable details (name, start time)
- **Globals Tree**: Lists all global variables
- **Auto-update**: Trees refresh after relevant commands

### Dynamic Subtitle
- Shows real-time shred count
- Shows audio status (ON/OFF)
- Updates automatically via reactive properties

## Key Bindings

| Key | Action | Description |
|-----|--------|-------------|
| **Ctrl+F** | Toggle Files | Show/hide file browser sidebar (keyboard nav) |
| **Ctrl+C** | Quit | Exit application |
| **Ctrl+L** | Clear | Clear console output |
| **Ctrl+S** | Toggle Audio | Start/stop audio system |
| **Ctrl+R** | Clear VM | Remove all shreds |
| **Ctrl+U** | Refresh | Manually refresh UI (hidden) |
| **Escape** | Focus Input | Focus command input field |
| **Tab** | Cycle Widgets | Move focus between widgets |
| **Arrow Keys** | Navigate | Browse file tree and other widgets |

## Layout

```
┌─────────────────────────────────────────────────────────────┐
│ ChucK REPL                     Shreds: 2 | Audio: ON      │
├────────────┬───────────────────────────────┬────────────────┤
│ Files      │ Console Output                │ Running Shreds │
│ (.ck)      │                               │ ├─ Shred 1    │
│            │ chuck> + foo.ck               │ │  └─ Name...  │
│ (sidebar)  │ [chout] success              │ ├─ Shred 2    │
│            │ chuck> ?                      │                │
│            │ Shred 1: foo.ck              │ Global Vars    │
│            │ Shred 2: bar.ck              │ ├─ tempo      │
│            │                               │ ├─ volume     │
│            │                               │                │
├────────────┴───────────────────────────────┴────────────────┤
│ chuck> _                                                     │
├──────────────────────────────────────────────────────────────┤
│ ^C Quit ^L Clear ^S Audio ^R Clear VM ^F Files              │
└──────────────────────────────────────────────────────────────┘
```

## Technical Improvements

### 1. External CSS (tui_rich.tcss)
Following the pattern from `code_browser.py` and `dictionary.py`:
```python
class ChuckTUI(App):
    CSS_PATH = "tui_rich.tcss"  # Load external stylesheet
```

Benefits:
- Cleaner Python code
- Easier styling updates
- Better organization
- Standard Textual pattern

### 2. Animated Sidebar (sidebar.py pattern)
```css
#file-sidebar {
    offset-x: -100%;        /* Hidden by default */
    transition: offset 200ms;  /* Smooth animation */
}

#file-sidebar.-visible {
    offset-x: 0;            /* Visible when class applied */
}
```

Controlled via reactive variable:
```python
show_files = var(False)

def watch_show_files(self, show_files: bool) -> None:
    sidebar.set_class(show_files, "-visible")
```

### 3. Tree Widgets (json_tree.py pattern)
Better than static labels for hierarchical data:
```python
shred_tree = Tree("Shreds", id="shred-tree")
shred_tree.show_root = False  # Hide root node

for shred_id in all_shreds:
    node = shred_tree.root.add(f"Shred {shred_id}")
    node.add_leaf(f"Name: {info['name']}")
    node.add_leaf(f"Start: {info['start']}")
```

### 4. DirectoryTree Widget (code_browser.py pattern)
Built-in file browser:
```python
yield DirectoryTree(path, id="file-tree")
```

With click handler:
```python
async def on_directory_tree_file_selected(self, event):
    if file_path.endswith('.ck'):
        cmd_input.value = f"+ {file_path}"
```

### 5. Reactive Subtitle Updates
Clean pattern for status bar:
```python
shred_count = reactive(0)
audio_running = reactive(False)

def watch_shred_count(self, count: int) -> None:
    self.sub_title = f"Shreds: {count} | Audio: {'ON' if self.audio_running else 'OFF'}"
```

### 6. Thread-Safe ChucK Callbacks
```python
self.chuck.set_chout_callback(lambda msg: self.call_from_thread(
    lambda: log.write(f"[cyan][chout][/cyan] {msg}", end='')
))
```

The `call_from_thread` ensures thread-safe UI updates from ChucK callbacks.

### 7. Proper Memory Cleanup
```python
def action_quit(self) -> None:
    # Break circular references
    if hasattr(self, 'session') and self.session:
        self.session.chuck = None
    if hasattr(self, 'executor') and self.executor:
        self.executor.chuck = None
        self.executor.session = None
    # ... cleanup
```

## CSS Classes and Styling

The external CSS file defines:
- **Layout**: Grid-based with sidebar layer
- **Colors**: Uses Textual's theme variables (`$primary`, `$accent`, `$surface`)
- **Transitions**: Smooth animations for sidebar
- **Responsive**: Adapts to terminal size
- **Semantic classes**: `.panel-title`, `.chuck-*` for different message types

## Comparison: Old vs New

| Feature | Old TUI | Improved TUI |
|---------|---------|--------------|
| CSS | Inline | External file |
| File browser | None | Animated sidebar |
| Shred display | Static label | Tree widget |
| Globals display | None | Tree widget |
| File selection | Manual typing | Keyboard nav + Enter |
| Subtitle | Static | Reactive updates |
| Layout control | Python | CSS |
| Threading | Basic | Thread-safe callbacks |
| Memory cleanup | Basic | Comprehensive |
| Mouse support | Basic | Disabled (temp) |

## Usage Examples

### Basic Session
```bash
python -m pychuck tui --rich

# In TUI:
# 1. Press Ctrl+F to open file browser
# 2. Click on a .ck file to load it
# 3. Press Enter to spork it
# 4. Watch shred tree populate
# 5. Press Ctrl+S to start audio
# 6. Check subtitle for status
```

### Workflow
1. **Browse files**: `Ctrl+F` to toggle sidebar
2. **Navigate**: Use arrow keys to browse file tree
3. **Load file**: Press Enter on `.ck` file to auto-fill command
4. **Execute**: Press Enter in command input
5. **Monitor**: Watch shred tree and console
6. **Control audio**: `Ctrl+S` to toggle
7. **Clean up**: `Ctrl+R` to remove all shreds

## Development Notes

### Adding New Widgets
Follow the pattern:
1. Add to `compose()` method
2. Style in `.tcss` file
3. Use reactive variables for state
4. Implement watcher methods

### Styling Guidelines
- Use Textual theme variables for colors
- Keep layout in CSS, not Python
- Use semantic class names
- Add transitions for animations

### State Management
- Use `reactive()` for properties that affect UI
- Use `var()` for state without computed properties
- Implement `watch_*` methods for side effects
- Call `refresh_ui_sync()` after state changes

## Future Enhancements

Possible improvements:
- **Code editor**: Inline `.ck` editor with syntax highlighting
- **Audio visualizer**: Real-time audio waveform display
- **Shred inspector**: Detailed view of shred state
- **History browser**: Navigate command history
- **Snippet library**: Quick access to code snippets
- **Documentation viewer**: Built-in ChucK docs
- **Variable editor**: GUI for setting globals
- **Log filtering**: Filter console output by type
- **Themes**: Custom color schemes

## Known Issues

### Mouse Support Disabled
Mouse support is currently disabled (`mouse_enabled = False`) due to a blank screen issue when mouse tracking is enabled. The TUI is fully functional with keyboard navigation:
- Use **Tab** to cycle through widgets
- Use **Arrow keys** to navigate trees and lists
- Use **Enter** to select items
- Use **Escape** to return focus to input

This will be re-enabled once the blank screen issue is debugged.

## Testing

The improved TUI:
- ✓ Compiles without syntax errors
- ✓ Doesn't break existing tests
- ✓ Properly cleans up on exit (no nanobind leaks)
- ✓ Follows Textual best practices
- ✓ Mouse support disabled (keyboard navigation only)
- ⚠ Requires `textual` package: `pip install textual`

## Resources

Based on these Textual examples:
- `code_browser.py` - External CSS, DirectoryTree, toggle sidebar
- `sidebar.py` - Animated sidebar with layers and offsets
- `json_tree.py` - Tree widget for hierarchical data
- `dictionary.py` - Reactive updates and getters

Textual documentation:
- https://textual.textualize.io/
- https://textual.textualize.io/widgets/
- https://textual.textualize.io/guide/CSS/
