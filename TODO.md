# TODO

- [ ] enable advanced chugins {faust, warpbug, fluidsynth}

- [x] complete api wrapping, missing a bunch of params, methods, and callbacks

---

## From Code Review

Remaining tasks from recent code review.

### C++ Binding Layer

- [x] **Memory leak potential in `replace_shred`** (`src/_numchuck.cpp`)
  - Fixed: Now uses `std::unique_ptr` for exception safety during message construction

### Python API

- [x] **Improve error propagation for sync getters** (`src/numchuck/api.py`)
  - Fixed: Error messages now explain that callback wasn't invoked and suggest increasing `run_frames`

### TUI Components

- [x] **Inconsistent error handling in cleanup** (`src/numchuck/tui/repl.py`)
  - Fixed: Now catches `RuntimeError` for ChucK ops, `(RuntimeError, OSError)` for audio ops

- [x] **Potential race condition in editor tab switching** (`src/numchuck/tui/editor.py`)
  - Resolved: Added documentation explaining prompt_toolkit is single-threaded (no actual race)

### Test Suite

- [x] **Expand test_api.py coverage**
  - Added 11 new tests: event callbacks (5), advance method (2), buffer reuse modes (4)
  - Total test count: 213 (up from 202)

- [x] **Fix flaky test pattern**
  - Fixed `try/except pass` patterns in test_global_events.py, test_realtime_audio.py, test_error_handling.py
  - Tests now have explicit assertions documenting expected behavior

### Build / CI

- [x] **Investigate skipped platform tests** (`wheels.yml`)
  - Restored testing on macosx_arm64 and Windows
  - manylinux_aarch64 skipped (cross-compiled, no native runner)
  - wavfile tests skipped in CI (WvOut timing issues)
  - chugin tests skipped in CI (not bundled in wheel)

- [x] **Fix Windows access violation**
  - Fixed: Crash during ChucK VM destruction/cleanup
  - Upstream fix in `thirdparty/chuck/core/chuck.cpp`:
    - Added 50ms delay after VM stop on Windows (`__PLATFORM_WINDOWS__`)
    - Allows WASAPI/DirectSound audio threads to fully terminate
  - Made `ChucK::shutdown()` public in `chuck.h` for explicit cleanup
  - Python API: `Chuck.close()` method for explicit shutdown
  - Windows tests re-enabled in CI

---

## Refactoring (2026-01-26)

High priority items from comprehensive code review.

### API Improvements

- [x] **Add context manager to Chuck class** (`src/numchuck/api.py`)
  - Added `__enter__` and `__exit__` methods for `with Chuck() as ck:` pattern
  - Ensures proper cleanup even on exceptions
  - Added 4 tests in test_api.py

### TUI Refactoring

- [x] **Extract shared TUI logic into base class** (`src/numchuck/tui/common.py`)
  - Enhanced `ChuckApplication` with audio lifecycle management
  - Added `setup()`, `start_audio_playback()`, `stop_audio_playback()`
  - Unified output capture with `setup_output_capture()` and `set_log_callback()`
  - Refactored `ChuckEditor` and `ChuckREPL` to use shared base class
  - Reduced code duplication for audio and cleanup logic

- [x] **Extract ChuckCompleter to standalone class** (`src/numchuck/tui/completer.py`)
  - Moved from nested class inside `ChuckREPL.__init__` to standalone module
  - Enables independent testing of completion logic
  - Added 12 tests in test_completer.py

### Test Suite

- [x] **Context manager tests** - 4 new tests for `with Chuck()` support
- [x] **Completer tests** - 12 new tests for ChuckCompleter class
- Total test count: 228 (up from 216)

### Packaging

- [x] **Add py.typed marker** (`src/numchuck/py.typed`)
  - Enables type checker support (PEP 561)
  - Added "Typing :: Typed" classifier to pyproject.toml

- [x] **Drop Python 3.8 support**
  - Python 3.8 reached EOL October 2024
  - Updated `requires-python = ">=3.9"` in pyproject.toml
  - Removed 3.8 classifier, added 3.13 classifier

---

## Medium-Term Enhancements (2026-01-26)

### API Enhancements

- [x] **Async/await API variants** (`src/numchuck/api.py`)
  - Added `get_int_awaitable()`, `get_float_awaitable()`, `get_string_awaitable()`
  - Uses asyncio with executor for non-blocking VM execution
  - Added 4 async tests

- [x] **Typed global variable proxies** (`src/numchuck/api.py`)
  - Added `GlobalInt`, `GlobalFloat`, `GlobalString` classes
  - Property-based access: `tempo.value = 120` instead of `chuck.set_int("tempo", 120)`
  - Factory methods: `chuck.global_int("tempo")`, etc.
  - Added 5 proxy tests

- [x] **Shred handle objects** (`src/numchuck/api.py`)
  - Added `Shred` class wrapping shred IDs
  - Methods: `shred.remove()`, `shred.replace()`, `shred.info`
  - Properties: `shred.id`, `shred.is_running`
  - Factory methods: `chuck.spork()`, `chuck.spork_file()`
  - Added 9 shred tests

- [x] **Configuration file support** (`src/numchuck/config.py`)
  - Support for `~/.numchuck/config.toml`
  - Dataclasses: `Config`, `AudioConfig`, `REPLConfig`, `EditorConfig`, `PathsConfig`, `ChuckConfig`
  - Functions: `load_config()`, `save_config()`, `get_config()`
  - Added 7 config tests

### Test Suite

- Total test count: 253 (up from 228)
