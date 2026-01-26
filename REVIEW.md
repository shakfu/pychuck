# numchuck Code Review

A comprehensive review of the numchuck project covering code quality, architecture, packaging, documentation, and enhancement opportunities.

---

## Executive Summary

numchuck is a well-architected Python binding for ChucK with a clean layered design. The codebase demonstrates solid engineering practices: proper separation of concerns, comprehensive error handling, good test coverage (~213 tests), and cross-platform support. The project is production-ready for its current scope but has opportunities for refinement and expansion.

**Strengths:**
- Clean C++/Python boundary with nanobind
- Pythonic high-level API wrapping low-level bindings
- Comprehensive TUI with prompt_toolkit
- Strong test coverage with pytest
- Cross-platform CI/CD with pre-built wheels

**Areas for Improvement:**
- API surface could be more intuitive in some areas
- TUI code has some duplication between REPL and Editor
- Documentation could benefit from more examples
- Some edge cases in error handling

---

## 1. Code Quality Analysis

### 1.1 C++ Binding Layer (`src/_numchuck.cpp`)

**Strengths:**
- Proper use of RAII patterns (e.g., `AudioContext`, `ChuckContextGuard`)
- Thread-safe callback management with mutexes
- Good GIL handling with `nb::gil_scoped_acquire`
- Exception-safe memory management with `std::unique_ptr` in `replace_shred`
- Input validation on buffer sizes and parameters

**Issues Identified:**

1. **Static callback storage scales linearly** (lines 125-128)
   ```cpp
   static std::unordered_map<int, nb::callable> g_callbacks;
   static int g_next_callback_id = 1;
   ```
   The callback ID counter never wraps, though in practice this won't overflow for reasonable use.

2. **Thread-local storage limitation** (line 29)
   ```cpp
   static thread_local ChucK* g_current_chuck = nullptr;
   ```
   Only one ChucK instance per thread can use chout/cherr callbacks during audio. Documented but could be confusing.

3. **Potential callback leak** - If `listen_for_global_event` is called but the event name doesn't exist, the callback is still stored after the error is thrown.

**Recommendations:**
- Add callback cleanup on ChucK instance destruction (partially done but could be more thorough)
- Consider using weak_ptr patterns for long-lived callbacks
- Document the single-instance-per-thread limitation more prominently

### 1.2 Python API Layer (`src/numchuck/api.py`)

**Strengths:**
- Clean Pythonic interface with properties instead of get/set methods
- Good docstrings with thread safety documentation
- Sensible defaults for all parameters
- Buffer reuse optimization with `reuse=True` parameter

**Issues Identified:**

1. **Sync getters require running frames** (lines 432-450)
   ```python
   def get_int(self, name: str, run_frames: int = 256) -> int:
       result: list[int] = []
       self._chuck.get_global_int(name, lambda v: result.append(v))
       self.run(run_frames)
   ```
   The need to run frames to get a value is counterintuitive. The API could be clearer about this callback-based nature.

2. **No context manager support** - The `Chuck` class doesn't implement `__enter__`/`__exit__` for proper resource cleanup.

3. **Missing `close()` visibility** - While `close()` exists, it should be more prominently documented as essential on Windows.

**Recommendations:**
```python
# Add context manager support
def __enter__(self):
    return self

def __exit__(self, *args):
    self.close()

# Usage:
with Chuck() as chuck:
    chuck.compile("SinOsc s => dac;")
    output = chuck.run(44100)
```

### 1.3 TUI Components (`src/numchuck/tui/`)

**Strengths:**
- Good use of prompt_toolkit for terminal UI
- ChucK syntax highlighting via Pygments lexer
- Smart Enter mode balances usability and code entry
- Project versioning for livecoding sessions

**Issues Identified:**

1. **Code duplication between REPL and Editor**
   - Both `repl.py` (684 lines) and `editor.py` (586 lines) contain similar setup code
   - Audio start/stop logic is duplicated
   - Log capture setup is duplicated

2. **Complex nested class in REPL** (lines 66-183)
   The `ChuckCompleter` class is defined inside `__init__`, making it harder to test and maintain.

3. **Mixed concerns in cleanup** (lines 652-683)
   Cleanup logic interleaves ChucK operations, audio operations, and reference breaking.

**Recommendations:**
- Extract `ChuckCompleter` to a standalone class in a separate file
- Create a shared audio management mixin or helper class
- Consider a `CleanupManager` pattern for orderly shutdown

### 1.4 CLI Layer (`src/numchuck/cli/`)

**Strengths:**
- Clean subcommand architecture with argparse
- Good separation between parsing and execution
- Backward compatibility with `tui` alias

**Minor Issues:**
- `cmd_repl` uses `getattr` for optional attributes that could use `None` defaults in the argument parser

---

## 2. Architecture Analysis

### 2.1 Layered Design (Excellent)

The project follows a clean layered architecture:

```
CLI/TUI Layer (user interaction)
      |
Python API (Chuck class)
      |
C++ Bindings (nanobind)
      |
ChucK Core (VM, compiler, UGens)
      |
RtAudio (platform audio)
```

Each layer has clear responsibilities and minimal leakage of abstractions.

### 2.2 Dependency Management (Good)

- Core dependencies (numpy, prompt-toolkit, pygments) are appropriate
- nanobind is a good choice over pybind11 for size/performance
- ChucK as a git submodule enables version pinning

### 2.3 State Management (Adequate)

**Issue:** Session state is scattered across multiple objects:
- `REPLSession` / `ChuckSession` tracks shreds
- `ChuckApplication` holds UI state
- `Chuck` instance holds VM state

Consider consolidating into a cleaner state hierarchy.

### 2.4 Error Handling Strategy (Good)

The project uses a consistent pattern:
- C++ layer throws `std::runtime_error` and `std::invalid_argument`
- Python layer catches and re-raises with context
- API documents which operations are not thread-safe

**Gap:** Some TUI errors are caught and silently logged rather than surfaced to users.

---

## 3. Packaging Analysis

### 3.1 Build System (Excellent)

- scikit-build-core + CMake is the right choice for C++ extensions
- Stable ABI targeting (cp312) reduces wheel count
- cibuildwheel configuration is comprehensive

### 3.2 PyPI Package (Good)

```toml
[project]
name = "numchuck"
version = "0.1.8"
requires-python = ">=3.8"
```

**Observations:**
- Python 3.8 support is maintained but 3.8 is EOL (Oct 2024)
- Version is still alpha (0.1.x) which is appropriate

**Recommendations:**
- Consider dropping Python 3.8 in next minor version
- Add `py.typed` marker for type checker support
- Consider PEP 621 `[project.optional-dependencies]` for dev tools

### 3.3 Platform Support (Comprehensive)

Pre-built wheels for:
- macOS (arm64, x86_64)
- Linux (x86_64, aarch64)
- Windows (x86_64)

CI skips musllinux and 32-bit builds appropriately.

### 3.4 Missing Elements

1. **No `py.typed` marker** - Type checkers won't recognize the package as typed
2. **No `__all__` in submodules** - Public API isn't explicitly declared in TUI/CLI modules
3. **No license classifier update** - LICENSE says GPLv2 but classifier says same (correct)

---

## 4. Documentation Analysis

### 4.1 README.md (Comprehensive)

**Strengths:**
- Complete API reference for both high-level and low-level APIs
- Good examples covering common use cases
- Clear installation instructions

**Gaps:**
- No "Quickstart" section at the top for impatient users
- Examples are code-heavy without explanatory prose
- No troubleshooting section

### 4.2 Inline Documentation (Good)

- Most public methods have docstrings
- Thread safety is documented in module docstrings
- Type hints are present but incomplete in some TUI code

### 4.3 Architecture Docs (Present)

`docs/architecture.md` exists but wasn't reviewed. Other docs cover specific fixes.

### 4.4 Missing Documentation

1. **Contributing guide** - No CONTRIBUTING.md
2. **API changelog** - CHANGELOG.md exists but could be more detailed
3. **Error reference** - No documentation of error types and recovery
4. **Performance guide** - No guidance on buffer sizes, real-time constraints

---

## 5. Test Suite Analysis

### 5.1 Coverage (Good)

15 test files with ~213 tests covering:
- Core API functionality
- Global variables and events
- Shred management
- CLI commands
- TUI components
- Error handling
- Integration scenarios

### 5.2 Test Quality (Good)

Tests follow pytest conventions and use appropriate fixtures. Recent improvements fixed flaky test patterns.

### 5.3 Gaps

1. **No performance/stress tests** - No tests for memory leaks or sustained operation
2. **Limited TUI integration tests** - UI testing is inherently difficult but could use more
3. **No property-based tests** - Could benefit from hypothesis for edge cases

---

## 6. Refactoring Opportunities

### 6.1 High Priority (COMPLETED 2026-01-26)

1. **[DONE] Extract shared TUI logic** - Enhanced `ChuckApplication` in `common.py`
   - Added `setup()`, `start_audio_playback()`, `stop_audio_playback()`
   - Unified output capture with `setup_output_capture()` and `set_log_callback()`
   - Refactored both Editor and REPL to use shared base class

2. **[DONE] Add context manager to Chuck class** (`src/numchuck/api.py`)
   ```python
   with Chuck() as ck:
       ck.compile("SinOsc s => dac;")
   # Automatically calls close()
   ```

3. **[DONE] Consolidate session types** - Already unified
   - `REPLSession` is an alias for `ChuckSession`

4. **[DONE] Extract ChuckCompleter to standalone class** (`src/numchuck/tui/completer.py`)
   - Moved from nested class inside `__init__` to standalone module
   - Added 12 tests in `test_completer.py`

### 6.2 Medium Priority (COMPLETED 2026-01-26)

5. **[DONE] Create audio management helper** (`src/numchuck/tui/common.py`)
   ```python
   class AudioManager:
       def __init__(self, chuck: ChucK, logger: TUILogger | None = None): ...
       @property
       def is_running(self) -> bool: ...
       def start(self) -> bool: ...
       def stop(self) -> bool: ...
       def restart(self) -> bool: ...
   ```
   - RAII-style lifecycle management
   - Logger integration for consistent error reporting
   - ChuckApplication now uses AudioManager internally

6. **[DONE] Standardize error handling in TUI**
   - Command methods return error strings instead of raising
   - Logger integration for warnings
   - Specific exception types instead of broad catches

### 6.3 Lower Priority (COMPLETED 2026-01-26)

7. **[DONE] Type hints completion** - All TUI modules now have complete type annotations
   - `common.py`, `commands.py`, `session.py`, `repl.py`, `completer.py`, `editor.py`

8. **[DONE] Logging standardization** - New centralized logging module
   - `src/numchuck/tui/logging.py` with TUILogger class
   - LogLevel enum (DEBUG, INFO, WARNING, ERROR)
   - Global logger functions: `get_logger()`, `set_logger()`, `debug()`, `info()`, `warning()`, `error()`
   - 15 tests in `test_logging.py`

9. **[DONE] Configuration file support** - Allow `~/.numchuck/config.toml` for preferences

---

## 7. Feature Enhancement Opportunities

### 7.1 API Enhancements

1. **[DONE] Async/await support** (`src/numchuck/api.py`)
   ```python
   value = await chuck.get_int_awaitable("counter")
   ```

2. **[DONE] Typed global variables** (`src/numchuck/api.py`)
   ```python
   tempo = chuck.global_int("tempo")
   tempo.value = 120
   ```

3. **[DONE] Shred handles** (`src/numchuck/api.py`)
   ```python
   shred = chuck.spork("SinOsc s => dac;")
   shred.replace("TriOsc t => dac;")
   shred.remove()
   ```

4. **Audio stream iteration** - NOT IMPLEMENTED
   ```python
   for frame in chuck.stream(512):
       process(frame)
   ```

### 7.2 TUI Enhancements

1. **[DONE] Configurable key bindings** (`src/numchuck/config.py`, `src/numchuck/tui/common.py`)
   - `KeybindingsConfig` dataclass with all key bindings
   - Customizable via `~/.numchuck/config.toml`

2. **[DONE] Theme support** (`src/numchuck/tui/themes.py`)
   - Built-in themes: dark, light, solarized
   - `ThemeConfig` and `ThemeColors` in config

3. **[DONE] Session recording/playback** (`src/numchuck/recorder.py`)
   - `SessionRecorder`, `SessionPlayer` classes
   - REPL commands: `record start/stop/save`, `playback`

4. **[DONE] Snippet library** (`src/numchuck/snippets/`)
   - 5 built-in snippets: sine, fm, drum, noise, delay
   - REPL command: `@snippet_name`
   - CLI: `numchuck snippets list/show/copy`

5. **Autocomplete for UGen parameters** - NOT IMPLEMENTED
   - Tab completion for `.freq`, `.gain`, etc.

6. **[DONE] Visual waveform display** (`src/numchuck/tui/waveform.py`)
   - `samples_to_waveform()`, `WaveformBuffer`
   - ASCII/Unicode waveform visualization
   - REPL commands: `wave on/off`

### 7.3 Tooling Enhancements

1. **LSP server** - NOT IMPLEMENTED
   - Language Server Protocol for IDE integration

2. **[DONE] Watch mode** (`src/numchuck/watcher.py`)
   - `FileWatcher` class for auto-reload on file changes
   - CLI: `numchuck watch file1.ck file2.ck`
   - REPL commands: `watch`, `unwatch`, `watching`

3. **[DONE] MIDI learn** (`src/numchuck/midi.py`)
   - `MIDIMapping`, `MIDIMappings` classes
   - `generate_midi_listener_code()` for ChucK integration
   - REPL commands: `midi learn/list/start/stop`

4. **[DONE] OSC integration** (`src/numchuck/osc.py`)
   - `OSCServer`, `OSCClient`, `OSCController` classes
   - `generate_osc_listener_code()` using ChucK's native liblo
   - REPL commands: `osc start/stop/status`

5. **[DONE] Export functionality** (`src/numchuck/render.py`)
   - `render()`, `render_file()`, `to_wav()` functions
   - CLI: `numchuck export output.wav --files file.ck --duration 10`

### 7.4 Documentation Enhancements

1. **Interactive tutorial** - NOT IMPLEMENTED
   - Step-by-step livecoding introduction

2. **Cookbook** - NOT IMPLEMENTED
   - Common patterns and recipes

3. **Video documentation** - NOT IMPLEMENTED
   - Screen recordings of livecoding sessions

---

## 8. Security Considerations

1. **Shell command execution** - The `$ <cmd>` REPL command executes shell commands. This is intentional but should be documented as a security consideration.

2. **File path handling** - PathCompleter allows navigation anywhere. In shared environments, consider sandboxing.

3. **No input sanitization for ChucK code** - ChucK code is passed directly to the VM. While ChucK itself is sandboxed, any file I/O operations use the process's permissions.

---

## 9. Performance Observations

1. **Buffer allocation** - The `reuse=True` parameter addresses the main allocation concern

2. **Callback overhead** - Python callbacks from C++ have GIL acquisition overhead

3. **TUI refresh** - Full redraw on every invalidate(); could optimize for partial updates

4. **Log buffer** - Unlimited growth until 1000 lines; could use deque for O(1) operations

---

## 10. Conclusion

numchuck is a well-designed project that successfully bridges ChucK and Python. The codebase is clean, well-tested, and production-ready for audio programming and livecoding applications.

**Phase 1 - Core Refactoring (COMPLETED 2026-01-26):**
1. [x] Added context manager support to `Chuck` class
2. [x] Consolidated TUI shared code into `ChuckApplication`
3. [x] Extracted `ChuckCompleter` to standalone testable class
4. [x] Added `py.typed` marker for type checker support (PEP 561)
5. [x] Dropped Python 3.8 support (EOL Oct 2024), now requires Python 3.9+

**Phase 2 - API Enhancements (COMPLETED 2026-01-26):**
1. [x] Async/await API variants (`get_int_awaitable()`, etc.)
2. [x] Typed global variable proxies (`GlobalInt`, `GlobalFloat`, `GlobalString`)
3. [x] Shred handle objects (`Shred` class with `spork()`, `replace()`, `remove()`)
4. [x] Configuration file support (`~/.numchuck/config.toml`)

**Phase 3 - TUI Quality (COMPLETED 2026-01-26):**
1. [x] AudioManager helper class for audio lifecycle management
2. [x] Standardized error handling with logger integration
3. [x] Complete type hints for all TUI modules
4. [x] Centralized logging module (`TUILogger`)

**Phase 4 - Feature Enhancements (COMPLETED 2026-01-26):**
1. [x] Offline rendering API (`numchuck.render`)
2. [x] Built-in snippet library (`numchuck.snippets`)
3. [x] File watch mode (`numchuck.watcher`)
4. [x] Theme support (`numchuck.tui.themes`)
5. [x] Configurable key bindings (`numchuck.config`)
6. [x] Waveform display (`numchuck.tui.waveform`)
7. [x] Session recording/playback (`numchuck.recorder`)
8. [x] MIDI learn support (`numchuck.midi`)
9. [x] OSC integration (`numchuck.osc`)

**Phase 5 - API Reorganization (COMPLETED 2026-01-26):**
1. [x] Created `numchuck.lang` subpackage (constants, lexer)
2. [x] Moved general-purpose modules to top level
3. [x] Streamlined top-level exports (core API only)
4. [x] Specialized modules require explicit imports

**Test Coverage:** 588 tests (up from 213 at review start)

**Remaining opportunities:**
1. Audio stream iteration API (`for frame in chuck.stream(512)`)
2. UGen parameter autocomplete (`.freq`, `.gain`, etc.)
3. LSP server for IDE integration
4. Documentation: interactive tutorial, cookbook, video docs

---

*Review conducted: 2026-01-26*
*Reviewer: Claude Code*
*All phases completed: 2026-01-26*
