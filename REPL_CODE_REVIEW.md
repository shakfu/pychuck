# Vanilla TUI Review & Recommendations

## Current State Assessment

**Strengths:**
- Clean separation: `parser.py` → `commands.py` → `session.py` architecture
- Comprehensive command coverage (shreds, globals, events, audio, VM control)
- Graceful fallback: prompt_toolkit → readline → basic input
- Tab completion for commands and `.ck` files
- History support with persistent file
- Proper cleanup on exit

**Issues:**

## Critical Issues

1. **No syntax highlighting** (parser.py:14-48)
   - ChucK code should be highlighted in command parsing/display
   - No visual feedback distinguishing code vs commands

2. **Poor error visibility** (commands.py throughout)
   - Generic "failed" messages with no ChucK compiler errors
   - No stack traces for ChucK runtime errors
   - Silent failures in global getters (lines 116-125)

3. **No multiline code support** (repl.py:44)
   - `multiline=False` prevents writing longer ChucK snippets
   - Need editor mode or multiline continuation

4. **Incomplete status feedback** (session.py)
   - No VM time tracking
   - No CPU/performance metrics
   - Audio status not tracked properly

## High Priority Improvements

### 1. **Enhanced Error Reporting**
```python
# In commands.py, propagate ChucK errors:
def _cmd_spork_file(self, args):
    success, shred_ids = self.chuck.compile_file(args['path'])
    if success:
        for sid in shred_ids:
            self.session.add_shred(sid, args['path'])
            print(f"✓ sporked {args['path']} → shred {sid}")
    else:
        # Get compilation errors from ChucK
        print(f"✗ Failed to compile {args['path']}")
        # TODO: chuck.get_last_error() or similar
```

### 2. **Multiline Editor Mode**
```python
# Add to repl.py patterns:
(r'^edit$', self._open_editor),  # Launch $EDITOR for code
(r'^ml$', self._multiline),      # Enter multiline mode
```

### 3. **Syntax Highlighting**
```python
# In repl.py __init__, add Pygments lexer:
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.c_cpp import CLexer  # ChucK similar to C

self.prompt_session = PromptSession(
    lexer=PygmentsLexer(CLexer),  # Highlight input
    # ...
)
```

### 4. **Status Bar** (prompt_toolkit toolbar)
```python
# Show audio status, VM time, active shreds count:
def get_toolbar():
    status = "Audio: " + ("ON" if self.session.audio_running else "OFF")
    status += f" | Now: {self.chuck.now():.2f}"
    status += f" | Shreds: {len(self.session.shreds)}"
    return status

self.prompt_session = PromptSession(
    bottom_toolbar=get_toolbar,
    # ...
)
```

### 5. **Better Command Completions**
```python
# Context-aware completion:
# - After '+', suggest .ck files
# - After '-', suggest active shred IDs
# - After 'name?', suggest known globals

from prompt_toolkit.completion import Completer, Completion

class ChuckCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text
        if text.startswith('+'):
            # Suggest .ck files
            yield from path_completions('.ck')
        elif text.startswith('-'):
            # Suggest shred IDs
            for sid in self.session.shreds.keys():
                yield Completion(str(sid), start_position=-len(text[1:].strip()))
```

### 6. **Live VM Monitoring**
```python
# commands.py - add watch command:
def _cmd_watch(self, args):
    """Monitor VM state continuously"""
    import time
    try:
        while True:
            print(f"\rNow: {self.chuck.now():.2f} | Shreds: {len(self.chuck.get_all_shred_ids())}", end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
```

### 7. **Code Snippets/Macros**
```python
# Store reusable ChucK snippets:
# ~/.chuck_snippets/sine.ck
# ~/.chuck_snippets/drums.ck

# parser.py:
(r'^@(\w+)$', self._load_snippet),  # @sine → load snippet

def _load_snippet(self, m):
    name = m.group(1)
    path = Path.home() / '.chuck_snippets' / f'{name}.ck'
    return Command('spork_file', {'path': str(path)})
```

### 8. **History Search Enhancement**
Already has `enable_history_search=True`, but add:
```python
# Ctrl+R reverse search is enabled
# Add Ctrl+S forward search:
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

@kb.add('c-s')
def _(event):
    event.app.current_buffer.start_history_search(
        direction=history.SEARCH_FORWARD
    )

self.prompt_session = PromptSession(
    key_bindings=kb,
    # ...
)
```

## Medium Priority

### 9. **Session Save/Restore**
```python
# Save current state:
# - Active shreds + their source
# - Global variables
# - Audio settings

def _cmd_save_session(self, args):
    import json
    state = {
        'shreds': [(sid, self.session.get_shred_name(sid))
                   for sid in self.chuck.get_all_shred_ids()],
        'globals': self.chuck.get_all_globals(),
        'audio_running': self.session.audio_running,
    }
    with open(args['path'], 'w') as f:
        json.dump(state, f)
```

### 10. **Performance Metrics**
```python
# Show CPU load, memory usage, audio buffer health:
def _cmd_perf(self, args):
    # Requires C++ binding extensions:
    print(f"CPU: {self.chuck.cpu_load():.1f}%")
    print(f"Mem: {self.chuck.memory_usage() / 1024**2:.1f} MB")
    print(f"Audio buffer health: {self.chuck.audio_buffer_health()}")
```

### 11. **Shred Visualization**
```python
# ASCII timeline of shred lifetimes:
#
#  Shred 1: =============================>
#  Shred 2:         ======>
#  Shred 3:                  ============>
#           ^                ^
#          10s              20s
```

### 12. **Better File Handling**
```python
# Watch .ck files for changes and auto-reload:
# Use watchdog library

# Also: relative path resolution
# + examples/sine.ck  → resolve relative to cwd or ~/.chuck/
```

## Low Priority

### 13. **Color Themes**
```python
# Customizable syntax highlighting themes
# ~/.chuck_repl.conf:
# [theme]
# style = monokai | solarized | github
```

### 14. **Logging**
```python
# Save all chout/cherr to file:
# ~/.chuck_repl.log with timestamps
```

### 15. **Aliases**
```python
# User-defined shortcuts:
# ~/.chuck_aliases:
# s = > (start audio)
# k = || (kill audio)
```

## Recommended Implementation Order

**Phase 1 (Immediate):**
1. Fix error reporting (show ChucK compiler errors)
2. Add syntax highlighting
3. Add bottom toolbar with status
4. Multiline editor mode

**Phase 2 (Short-term):**
5. Better completions (context-aware)
6. Watch command for monitoring
7. Session save/restore
8. Code snippets

**Phase 3 (Long-term):**
9. Performance metrics (requires C++ bindings)
10. Shred visualization
11. File watching/auto-reload
12. Color themes

## Example Enhanced REPL Session
```
ChucK REPL v0.2.0 (prompt-toolkit mode)
──────────────────────────────────────────────────────
Audio: OFF | Now: 0.00 | Shreds: 0 | CPU: 0%
──────────────────────────────────────────────────────
chuck> >                         # Start audio
✓ Audio started

chuck> + "SinOsc s => dac;       # Tab highlights syntax
440 => s.freq;
second => now;"
✓ Sporked code → shred 1

chuck> ?                         # List shreds
ID       Name                     Started     Duration
─────────────────────────────────────────────────────
1        inline:SinOsc s => dac   0.00s       1.00s

chuck> edit                      # Opens $EDITOR with template
✓ Sporked /tmp/chuck_XXXXX.ck → shred 2

chuck> @drums                    # Load snippet
✓ Sporked ~/.chuck_snippets/drums.ck → shred 3
```

## Conclusion

The vanilla TUI is well-architected and functional. Main gaps are **error visibility**, **multiline editing**, and **status feedback**. Adding these would make it production-ready.
