# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Commons Changelog](https://common-changelog.org). This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Types of Changes

- Added: for new features.
- Changed: for changes in existing functionality.
- Deprecated: for soon-to-be removed features.
- Removed: for now removed features.
- Fixed: for any bug fixes.
- Security: in case of vulnerabilities.

---

## [Unreleased]

### Added

- **Wheel RECORD Validation** (`scripts/check_wheel_record.py`, `scripts/repair_wheel.py`):
  - New standalone script validates wheel RECORD files against actual ZIP contents -- checks for smuggled files, dangling entries, hash mismatches, and size mismatches
  - Addresses [wheel archive confusion attacks](https://blog.pypi.org/posts/2025-08-07-wheel-archive-confusion-attacks/)
  - Integrated into `repair_wheel.py` as a post-repair validation step for both chugin and non-chugin wheels
  - Added RECORD validation steps to CI wheels workflow (per-platform and combined artifact stages)
  - `make check` now runs RECORD validation alongside `twine check`

- **CLAP, PdPatch, and VST3 Chugins** (`thirdparty/chugins/{CLAP,PdPatch,VST3}/`):
  - Added three new chugins from [my-chugins](https://github.com/shakfu/my-chugins): CLAP (host CLAP plugins), PdPatch (embed Pure Data patches), and VST3 (host VST3 plugins)
  - All three are enabled by default via `option(CM_CLAP/CM_PDPATCH/CM_VST3 ... ON)` and bundled in release wheels
  - External dependencies (clap SDK 1.2.6, libpd, VST3 SDK v3.8.0) fetched automatically via CMake `FetchContent`
  - Can be individually disabled with `-DCM_CLAP=OFF`, `-DCM_PDPATCH=OFF`, or `-DCM_VST3=OFF`
  - macOS and Linux only -- all three depend on POSIX APIs (`dlfcn.h`, `dirent.h`, pthreads) not available on Windows
  - Fixed VST3 SDK option names (`SMTG_ENABLE_VST3_PLUGIN_EXAMPLES`/`SMTG_ENABLE_VST3_HOSTING_EXAMPLES`) to correctly disable SDK samples that require `gtk+-3.0` on Linux

### Fixed

- **Wheels workflow collect job** (`.github/workflows/wheels.yml`):
  - Reordered `collect` job steps to run `checkout` before artifact downloads -- `actions/checkout@v4` cleans the working directory by default, which was wiping the downloaded `dist/` directory

## [0.1.10]

### Added

- **Bundled Chugins in Wheels** (`scripts/cmake/fn_add_chugin.cmake`, `pyproject.toml`, `src/numchuck/api.py`):
  - Pre-built chugins (~37 `.chug` files) are now included in distributed wheels
  - `NUMCHUCK_INSTALL_CHUGINS` CMake option gates installation (ON for wheel builds, OFF for local dev)
  - `cmake.args = ["-DNUMCHUCK_INSTALL_CHUGINS=ON"]` in `pyproject.toml` enables bundling during `pip install` / `uv build`
  - Bundled chugins directory (`<package>/chugins/`) automatically added to ChucK search path in `Chuck.__init__`
  - Users no longer need to build from source to use chugins

- **`numchuck info` lists bundled chugins** (`src/numchuck/cli/main.py`):
  - Shows count and names of all bundled `.chug` files from the installed package
  - Displays "none" for editable/dev installs where chugins are in `examples/chugins/` instead

- **Cross-Platform Wheel Repair for Chugins** (`scripts/repair_wheel.py`):
  - Wheel repair tools (delocate, auditwheel, delvewheel) skip `.chug` files since they only scan platform-standard extensions
  - New repair script temporarily renames `.chug` to the native extension (`.dylib`/`.so`/`.dll`), runs the repair tool, then renames back
  - Ensures chugin shared library dependencies are properly bundled if any chugin gains external (non-system) dependencies
  - Uses only stdlib (`zipfile`, `hashlib`, `csv`) -- no dependency on the `wheel` CLI package
  - RECORD file correctly regenerated after rename operations
  - Platform-specific handling:
    - macOS: `.chug` -> `.dylib`, delocate-wheel with `--require-archs`
    - Linux: `.chug` -> `.so`, auditwheel repair
    - Windows: `.chug` -> `.dll`, delvewheel with `--analyze-existing --no-mangle`

- **README: Bundled chugins documentation** (`README.md`):
  - Categorized table of all 37 bundled chugins (38 on macOS with AudioUnit)
  - Updated "Using Chugins" section to show automatic discovery (no manual path setup)
  - Plugin Support overview links to the bundled chugins table

### Changed

- **CI: Chugin tests enabled in wheel builds** (`.github/workflows/wheels.yml`):
  - Removed `and not chugin` from `CIBW_TEST_COMMAND` filter
  - All three platforms (Linux, macOS, Windows) now use the custom repair script
  - Windows builds install delvewheel via `CIBW_BEFORE_BUILD_WINDOWS`

- **Chugin test helpers updated** (`tests/test_examples.py`):
  - New `_get_chugins_dir()` helper checks bundled package directory first, falls back to `examples/chugins/` for dev builds
  - All chugin tests (`test_chugin_loading`, `test_chugin_bitcrusher_strict`, `test_chugin_gverb_strict`, `test_chugin_convrev_example`) use the unified helper

### Fixed

- **TUI tests skipped on Windows** (`tests/conftest.py`):
  - Added `pytest_collection_modifyitems` hook to skip `@pytest.mark.tui` tests on Windows
  - prompt_toolkit raises `NoConsoleScreenBufferError` on Windows in non-console environments
  - 42 TUI tests now skip gracefully on Windows instead of failing

- **WAV file rendering tests** (`tests/test_wavfile.py`):
  - Fixed `test_render_sine_to_wav` run duration: `chuck.run(44100)` changed to `chuck.run(44100 * 4)` to match 4-second ChucK code duration
  - Added `del chuck` before temp directory cleanup in all tests to release file handles
  - Fixes `PermissionError` on Windows where files can't be deleted while open

- **Async awaitable race condition** (`src/numchuck/api.py`):
  - `get_int_awaitable`, `get_float_awaitable`, `get_string_awaitable` had a race between `run_in_executor` completion and `call_soon_threadsafe` callback delivery
  - Added `await asyncio.sleep(0)` after `run_in_executor` to yield to the event loop and process pending callbacks before checking `future.done()`
  - Fixes intermittent "callback not invoked" failures on slower platforms (macOS x86_64 under Rosetta)

## [0.1.9]

### Added

- **Chugin Directory Search** (`src/numchuck/api.py`, `src/numchuck/tui/common.py`):
  - Automatic discovery of chugins via `PARAM_IMPORT_PATH_SYSTEM` (auto-loads .chug files)
  - Default search paths:
    - `~/.numchuck/chugins` - Always included (global user chugins)
    - `./.numchuck/chugins` - Included if exists (project-local chugins)
  - `user_chugins` parameter accepts both directories and explicit `.chug` files

- **Import Path Properties** (`src/numchuck/api.py`):
  - `chuck.import_path_system` - System chugin/import search directories
  - `chuck.import_path_user` - User import search paths
  - `chuck.import_path_packages` - Package import search paths

- **ChucK Command Alignment** (`src/numchuck/tui/parser.py`, `src/numchuck/tui/commands.py`):
  - `abort.shred <id>` / `abort <id>` - ChucK-native shred abort commands
  - `exit` / `quit` - Exit the REPL
  - `= <id> file.ck` / `= <id> "code"` - ChucK-style replace shred shortcuts
  - `^` - ChucK-style status shortcut

- **Web IDE** (`src/_web.cpp`, `src/numchuck/web/`):
  - Browser-based ChucK IDE similar to WebChucK
  - Mongoose web server serving static files from package directory
  - REST API for ChucK control: compile, remove shred, audio start/stop
  - WebSocket for real-time console output and status updates
  - HTML/CSS/JS frontend in `src/numchuck/web/static/`
  - CLI command: `numchuck web [--port 8080] [files...]`
  - CMake option: `-DNUMCHUCK_ENABLE_WEB=ON` (enabled by default)
  - **Enhanced UI Features**:
    - Multi-file tabs with local storage persistence
    - Examples dropdown with built-in ChucK examples
    - Globals panel with auto-discovery and interactive sliders for int/float variables
    - Shred management: replace shred, preview code, elapsed time display
    - Theme toggle (dark/light mode) with system preference detection
    - Open file from disk (Ctrl+O) and download/save-as (Ctrl+Shift+S)
    - Keyboard shortcuts: Ctrl+Enter (spork), Ctrl+S (save), Ctrl+N (new tab), Ctrl+O (open), Ctrl+Shift+S (download)
  - **Real-time Audio Metering**:
    - RMS and peak level meters for left/right channels
    - Calculated in C++ audio callback for accuracy
    - Streamed via WebSocket every 100ms when audio running
    - Visual meter bars in browser UI
    - New `get_audio_meters()` function in Python API
  - **WebSocket Globals Sync**:
    - Push-based globals updates (every 500ms when changed)
    - Reduced polling to 10s fallback
    - Real-time slider sync in browser UI
  - **Bundled Static Assets** (offline support):
    - CodeMirror 5.65.16 editor bundled locally (`css/`, `js/`)
    - xterm.js 5.3.0 terminal emulator for REPL
    - No external CDN dependencies required
    - Works completely offline
  - **Interactive Web REPL**:
    - Full terminal emulator using xterm.js
    - Toggle between Editor and REPL views
    - Full command parity with TUI REPL (all ChucK commands supported)
    - Supports all REPL commands: +, -, =, status, globals, events, etc.
    - Command history with up/down arrows
    - Cut/copy/paste support (Ctrl+X/C/V or Cmd+X/C/V)
    - Right-click to select word
    - Ctrl+C to cancel (when no selection), Ctrl+L to clear
    - ChucK code can be entered directly
    - Clicking files in sidebar switches to Editor view
  - **New REST API Endpoints**:
    - `GET /api/globals` - List all global variables with types
    - `POST /api/shred/:id/replace` - Replace running shred with new code
    - `GET /api/shred/:id/code` - Get shred source code

- **Audio Metering API** (`src/_numchuck.cpp`, `src/numchuck/_numchuck.pyi`):
  - `get_audio_meters()` - Returns dict with `rms_left`, `rms_right`, `peak_left`, `peak_right`
  - Thread-safe atomic floats updated in real-time audio callback
  - `AudioMeters` TypedDict for type checking

- **Type Stubs for Web Module** (`src/numchuck/_web.pyi`):
  - Complete type annotations for `WebServer` class
  - Properties: `port`, `static_dir`, `is_running`, `client_count`
  - Methods: `set_api_handler`, `broadcast`, `start`, `stop`

- **Audio Stream Iteration API** (`src/numchuck/api.py`):
  - `chuck.stream(frames_per_chunk, max_chunks, reuse)` generator method
  - Iterator-based audio processing: `for audio in chuck.stream(512): process(audio)`
  - Supports infinite iteration with early break, or bounded with `max_chunks`
  - Zero-allocation mode with `reuse=True` (default)
  - 8 new tests for stream iteration

- **UGen Parameter Autocomplete** (`src/numchuck/tui/completer.py`):
  - Tab completion for UGen parameters after `.`: `.freq`, `.gain`, `.phase`, etc.
  - Context-aware: detects UGen type from variable declarations
  - `UGEN_PARAMS` mapping with parameters for 40+ UGens (oscillators, filters, envelopes, delays, reverbs, buffers, STK instruments)
  - 6 new tests for parameter completion

- **Offline Audio Rendering API** (`src/numchuck/render.py`):
  - `render(code, duration, sample_rate, channels, dtype)` - Render ChucK code to numpy array
  - `render_file(files, duration, sample_rate, channels, dtype)` - Render ChucK files to numpy array
  - `to_wav(output, code, files, duration, ...)` - Export ChucK code/files to WAV file
  - `RenderError` exception for rendering failures
  - Supports both `np.float32` and `np.int16` output dtypes
  - Chunked rendering to avoid memory issues for long durations

- **User Directory Template** (`_numchuck/`):
  - Template for `.numchuck` user configuration directory
  - Search order: `./.numchuck` (local) then `~/.numchuck` (global)
  - Local configuration takes precedence over global
  - Subdirectories with examples:
    - `snippets/` - Code snippets (sine, fm, drum, noise, delay)
    - `examples/` - Example ChucK files (hello, arpeggio, lfo)
    - `themes/` - Color themes (dark.toml, light.toml)
    - `keybindings/` - Key binding configurations (default.toml)
    - `chugins/` - User chugins with README
  - Copy to home: `cp -r _numchuck ~/.numchuck`

- **Snippet Support** with local/global precedence:
  - Snippets stored in `.numchuck/snippets/` directory
  - Local snippets (`./.numchuck/snippets/`) take precedence over global (`~/.numchuck/snippets/`)
  - CLI commands: `numchuck snippets list`, `snippets show <name>`, `snippets path`
  - REPL command: `@<name>` to load a snippet with tab completion

- **File Watch Mode** (`src/numchuck/watcher.py`):
  - `FileWatcher` class for auto-reloading ChucK files on modification
  - Debouncing to prevent rapid reloads during saves
  - Callbacks for reload and error events
  - CLI command: `numchuck watch file1.ck file2.ck`
  - REPL commands: `watch <file>`, `unwatch <file>`, `watching`

- **Theme Support** (`src/numchuck/tui/themes.py`):
  - Built-in themes: `dark`, `light`, `solarized`
  - `ThemeConfig` and `ThemeColors` dataclasses in config
  - `create_style(theme_config)` generates prompt_toolkit Style
  - Configurable via `~/.numchuck/config.toml`

- **Configurable Key Bindings** (`src/numchuck/config.py`):
  - `KeybindingsConfig` dataclass with all key bindings
  - `create_keybinding(kb, key, handler)` with safe validation
  - Customizable via `~/.numchuck/config.toml`

- **Waveform Display** (`src/numchuck/tui/waveform.py`):
  - `samples_to_waveform()` - Convert audio samples to Unicode/ASCII waveform
  - `WaveformBuffer` - Circular buffer for real-time waveform display
  - `format_waveform_bar()`, `format_stereo_meters()` - Level meter formatting
  - `calculate_rms()`, `calculate_peak()` - Audio level calculations
  - `db_to_linear()`, `linear_to_db()` - Decibel conversions
  - REPL commands: `wave`, `wave on`, `wave off` (toggle with F4)

- **Session Recording/Playback** (`src/numchuck/recording.py`):
  - `SessionRecorder` - Record REPL sessions with timestamps
  - `SessionPlayer` - Playback recorded sessions with speed control
  - `RecordedAction`, `RecordedSession` dataclasses
  - JSON-based session storage in `~/.numchuck/recordings/`
  - REPL commands: `record start`, `record stop`, `record save <name>`, `playback <name>`

- **MIDI Learn Support** (`src/numchuck/midi.py`):
  - `MIDIMapping` - Map MIDI CC to ChucK global variables with min/max scaling
  - `MIDIMappings` - Collection of MIDI mappings
  - `MIDILearnState` - State machine for MIDI learn mode
  - `generate_midi_listener_code()` - Generate ChucK code for MIDI control
  - `generate_midi_monitor_code()` - Generate MIDI monitor code
  - REPL commands: `midi learn <var>`, `midi list`, `midi start`, `midi stop`

- **OSC Integration** (`src/numchuck/osc.py`):
  - `OSCServer` - UDP server for receiving OSC messages
  - `OSCClient` - UDP client for sending OSC messages
  - `OSCController` - Map OSC addresses to REPL actions
  - `generate_osc_listener_code()` - Generate ChucK code using native liblo
  - `generate_osc_sender_code()` - Generate ChucK OSC sender code
  - OSC address patterns: `/numchuck/set/<var>`, `/numchuck/event/<name>`, `/numchuck/spork`
  - REPL commands: `osc start [port]`, `osc stop`, `osc status`

- **Context Manager Support** (`src/numchuck/api.py`):
  - `Chuck` class now supports `with` statement for automatic cleanup
  - `__enter__` and `__exit__` methods ensure `close()` is called on exit
  - Example: `with Chuck() as ck: ck.compile("SinOsc s => dac;")`
  - 4 new tests for context manager behavior

- **Async/Await API** (`src/numchuck/api.py`):
  - `get_int_awaitable(name, run_frames=256) -> int` - Async get global int
  - `get_float_awaitable(name, run_frames=256) -> float` - Async get global float
  - `get_string_awaitable(name, run_frames=256) -> str` - Async get global string
  - Uses asyncio with executor for non-blocking VM execution
  - 4 new async tests

- **Typed Global Variable Proxies** (`src/numchuck/api.py`):
  - `GlobalInt`, `GlobalFloat`, `GlobalString` classes for property-based access
  - Factory methods: `chuck.global_int("name")`, `chuck.global_float("name")`, `chuck.global_string("name")`
  - Property access: `tempo.value = 120` instead of `chuck.set_int("tempo", 120)`
  - Methods: `get()`, `set(value)`, `get_async()` (awaitable)
  - 5 new proxy tests

- **Shred Handle Objects** (`src/numchuck/api.py`):
  - `Shred` class wrapping shred IDs with methods for control
  - Factory methods: `chuck.spork(code, args="")`, `chuck.spork_file(path, args="")`
  - Methods: `remove()`, `replace(code, args="")`, `info` property
  - Properties: `id`, `is_running`
  - Equality comparison with int shred IDs
  - 9 new shred tests

- **Configuration File Support** (`src/numchuck/config.py`):
  - Support for `~/.numchuck/config.toml` user configuration
  - Dataclasses: `Config`, `AudioConfig`, `REPLConfig`, `EditorConfig`, `PathsConfig`, `ChuckConfig`
  - Functions: `load_config()`, `save_config()`, `get_config()`, `reload_config()`
  - Automatic defaults for missing values
  - 7 new config tests

- **PEP 561 Type Checker Support**:
  - Added `py.typed` marker file (`src/numchuck/py.typed`)
  - Added "Typing :: Typed" classifier to pyproject.toml

- **TUI Refactoring**:
  - Extracted `ChuckCompleter` to standalone class (`src/numchuck/tui/completer.py`)
  - Enhanced `ChuckApplication` base class with audio lifecycle management
  - Added `setup()`, `start_audio_playback()`, `stop_audio_playback()` methods
  - Unified output capture with `setup_output_capture()` and `set_log_callback()`
  - 12 new completer tests

- **TUI Logging Module** (`src/numchuck/tui/logging.py`):
  - Centralized logging for TUI components
  - `LogLevel` enum (DEBUG, INFO, WARNING, ERROR)
  - `TUILogger` class with callbacks, stream output, timestamps
  - Message storage with level filtering via `get_messages(level=...)`
  - Global logger functions: `get_logger()`, `set_logger()`, `debug()`, `info()`, `warning()`, `error()`
  - 15 new logging tests

- **Service Layer Architecture** (`src/numchuck/services/`):
  - New `services` package providing business logic separation from UI
  - `AudioService` - Audio lifecycle management (start/stop/restart/shutdown)
  - `ShredService` - Shred compilation, replacement, and removal with structured results
  - `GlobalsService` - Global variable get/set operations and event signaling
  - `FileService` - Snippet loading and project file operations
  - Services are stateless with dependency injection via constructor
  - Returns structured dataclasses (`ShredResult`, `GlobalInfo`, `SnippetInfo`) instead of formatted strings
  - Used by both CLI and TUI for shared business logic
  - 89 new service tests with 84% coverage

- **TUI Widget Factories** (`src/numchuck/tui/widgets.py`):
  - `create_help_window()` - Conditional help display
  - `create_shreds_table()` - Dynamic shreds table
  - `create_log_window()` - Scrollable log display
  - `create_status_bar()` - Status bar with dynamic content
  - `create_message_area()` - Text area for messages

- **AudioService Class** (`src/numchuck/services/audio.py`):
  - RAII-style audio lifecycle management
  - Methods: `start()`, `stop()`, `restart()`, `shutdown()`
  - Property: `is_running`
  - Optional callbacks: `set_callbacks(on_start=..., on_stop=...)`
  - Logger integration for consistent error reporting
  - Used by CLI (`executor.py`, `watcher.py`) and TUI (`common.py`)
  - 8 new AudioService tests

- **TUI Type Hints Completion**:
  - `common.py` - Full annotations for AudioManager and ChuckApplication
  - `commands.py` - All 20+ command methods annotated with return types
  - `session.py` - ChuckSession fully typed with logger integration
  - `repl.py` - Key methods typed (run, setup, process_input, cleanup)
  - `completer.py` - ChuckCompleter with TYPE_CHECKING imports
  - `editor.py` - EditorTab and ChuckEditor classes fully typed

- **TUI Error Handling Standardization**:
  - Command methods return error strings instead of raising exceptions
  - Logger integration for warnings and debug output
  - Specific exception types instead of broad `Exception` catches

- **REPL Stdin Mode** (`src/numchuck/tui/repl.py`, `src/numchuck/tui/tui.py`):
  - Non-interactive REPL mode for piped input and scripting
  - Automatic detection: uses stdin mode when input is not a TTY
  - New `ChuckREPLStdin` class for processing commands from stdin
  - Comment support: lines starting with `#` are ignored
  - Exit commands: `quit`, `exit`, or `q` to stop processing
  - Usage examples:
    - `echo '+ test.ck' | numchuck repl` - Pipe commands
    - `numchuck repl < commands.txt` - Redirect input
    - `cat script.txt | numchuck repl` - Script execution
  - New `--stdin` CLI flag to force stdin mode even in interactive terminals
  - 63 new tests for stdin REPL mode (`tests/test_repl_stdin.py`)

### Changed

- **CommandExecutor Refactoring** (`src/numchuck/tui/commands.py`):
  - Now uses `ShredService`, `GlobalsService`, and `FileService` for all operations
  - Added `shred_service`, `globals_service`, and `file_service` properties with proper None handling
  - Snippet loading (`@name`) now uses `FileService` instead of direct path functions
  - Simplified command methods to delegate to services
  - `_cmd_list_shreds` now uses session data instead of VM query (works without audio running)

- **ChuckApplication Service Integration** (`src/numchuck/tui/common.py`):
  - Added `shred_service`, `globals_service`, and `file_service` lazily-created properties
  - Services are cached after first access for reuse
  - UI factory methods now delegate to `tui/widgets.py` module
  - `chuck` and `session` are now properties that raise `RuntimeError` if accessed after cleanup
  - Cleanup method properly handles None state and circular reference breaking
  - Fixed `close()` to `shutdown()` for ChucK instance cleanup

- **Editor Refactoring** (`src/numchuck/tui/editor.py`):
  - F5/Ctrl-R (spork) now uses `ShredService.spork_code()` instead of direct ChucK calls
  - F6 (replace) now uses `ShredService.replace_shred()` instead of direct ChucK calls
  - Session tracking handled automatically by ShredService
  - Simplified error handling with structured `ShredResult` returns

- **REPL Refactoring** (`src/numchuck/tui/repl.py`):
  - Direct code compilation now uses `ShredService.spork_code()` instead of direct ChucK calls
  - Consistent with CommandExecutor's service-based approach

- **API Refactoring** - Moved general-purpose modules from `tui/` to top level for library use:
  - `numchuck.render` - Offline rendering API (new, from `cli/export.py`)
  - `numchuck.osc` - OSC server/client (from `tui/osc_server.py`)
  - `numchuck.midi` - MIDI mappings (from `tui/midi.py`)
  - `numchuck.watcher` - File watcher (from `tui/watcher.py`)
  - `numchuck.recorder` - Session recording (from `tui/recording.py`)
  - `numchuck.paths` - Path utilities (from `tui/paths.py`)

- **New `numchuck.lang` Subpackage** - ChucK language support:
  - `numchuck.lang.constants` - Keywords, types, UGens, operators (from `chuck_lang.py`)
  - `numchuck.lang.lexer` - Pygments lexer for syntax highlighting (from `lexer.py`)
  - Convenience imports: `from numchuck.lang import ChuckLexer, KEYWORDS, UGENS`

- **Package Exports** (`src/numchuck/__init__.py`):
  - Core: `Chuck`, `Shred`, `GlobalInt`, `GlobalFloat`, `GlobalString`
  - Rendering: `render`, `render_file`, `to_wav`, `RenderError`
  - Config: `Config`, `load_config`, `get_config`, `save_config`
  - Specialized modules require explicit imports:
    - `from numchuck.osc import OSCServer, OSCClient, ...`
    - `from numchuck.midi import MIDIMapping, MIDIMappings, ...`
    - `from numchuck.watcher import FileWatcher, ...`
    - `from numchuck.recorder import SessionRecorder, ...`
    - `from numchuck.lang import ChuckLexer, KEYWORDS, ...`

- **Python Version Support**:
  - Dropped Python 3.8 and 3.9 support (3.9 EOL October 2025, union type syntax requires 3.10+)
  - Now requires Python 3.10+
  - Added Python 3.13 classifier

- **Test Count**: 963 tests (up from 603)

- **CLI Test Suite** (`tests/test_executor.py`, `tests/test_watcher_cli.py`):
  - Added 28 new tests for CLI executor and watcher modules
  - Mock-based testing for `execute_files()` and `watch_files()` functions
  - Tests cover: file validation, compilation, audio start/stop, signal handling, cleanup
  - Refactored `executor.py` to use high-level API for better testability

### Removed

- **Chump Package Manager Integration**:
  - Removed `_chump.cpp`, `_chump.py`, `packages.py`, `cli/packages.py`
  - Removed `numchuck pkg` CLI commands
  - Removed chump documentation from README.md and CHANGELOG.md
- **`tui` CLI subcommand** - Use `numchuck repl` instead (the `tui` alias is no longer supported)
- **`AudioManager` backward compatibility alias** - Use `AudioService` directly from `numchuck.services`

### Fixed

- **Linux Build Failure** (`src/_web.cpp`):
  - Added missing `#include <algorithm>` for `std::remove`
  - GCC 14 was resolving `std::remove` to C's `remove(const char*)` from `<cstdio>`

- **Windows Build Failure** (`src/_numchuck.cpp`):
  - Added `#define NOMINMAX` to prevent Windows `min`/`max` macros from conflicting with `std::min`/`std::max`
  - Fixes C2589 "illegal token" errors in audio metering code

- **Web IDE Server Crash on Page Load** (`src/_numchuck.cpp`):
  - Fixed segfault (exit code 139) when browser connects to Web IDE
  - Root cause: `get_all_globals()` called `self.globals()->get_all_global_variables()` without null check
  - When no globals are defined, `self.globals()` returns nullptr
  - Browser's JavaScript polls `/api/globals` every 2 seconds, triggering crash on page load
  - Added null pointer check to return empty list when globals manager is unavailable

- **Web IDE Audio Status Incorrect** (`src/_numchuck.cpp`, `src/numchuck/web/__init__.py`):
  - Fixed audio toggle showing "Running" when audio was actually stopped
  - Root cause: `_is_audio_running()` checked `audio_info()["sample_rate"] > 0` which is always true
  - ChucK always has a sample rate configured regardless of audio running state
  - Added new `is_audio_running()` C++ function that checks actual audio context state
  - Updated Python wrapper to use new function for accurate status

- **Windows File Compilation** (`src/_numchuck.cpp`):
  - Normalize Windows backslash paths to forward slashes before passing to ChucK
  - Fixes "Failed to compile" errors on Windows CI with temp file paths

- **CI Test Stability**:
  - Added `@pytest.mark.realtime` to `test_audio_commands` to skip on CI without audio devices
  - Fixes ALSA errors on Linux CI runners

- **macOS Script Compatibility** (`scripts/remove_chump.sh`):
  - Replaced BSD-incompatible sed commands with Python for cross-platform file modifications

- **Type Safety Improvements** (full `mypy --strict` compliance):
  - `api.py`: Added `_chuck` property with proper None handling after `close()`
  - `common.py`: `chuck` and `session` properties raise `RuntimeError` if accessed after cleanup
  - `commands.py`: `shred_service` and `globals_service` properties with None checks
  - `globals.py`: Fixed variable reuse in `get_global()` method, explicit array type annotations
  - `completer.py`: Renamed shadowed `match` variable, added explicit `return None`

- **Nanobind memory leak warnings on REPL exit**:
  - `ChuckCompleter` was holding references to `chuck` and `session` that weren't cleaned up
  - Added proper cleanup of completer references before ChucK instance is closed
  - Added `gc.collect()` calls to ensure C++ objects are released before interpreter shutdown
  - REPL now exits cleanly without "leaked instances/types/functions" warnings

- **REPL cleanup method idempotency** (`src/numchuck/tui/repl.py`):
  - `ChuckREPL.cleanup()` can now be safely called multiple times
  - Added `is not None` checks before accessing completer, executor, and app_state
  - Prevents `AttributeError` when cleanup is called on already-cleaned instance

- **Segfault on test suite exit** (`src/numchuck/tui/repl.py`):
  - Removed problematic static callback clearing from `ChuckREPL.cleanup()`
  - Setting `set_stdout_callback`/`set_stderr_callback` to lambdas during cleanup caused segfault at interpreter shutdown
  - Tests now use `app_state.setup()` instead of `repl.setup()` to avoid setting static callbacks

- **Full `mypy --strict` compliance** (150 type errors fixed across 17 files):
  - `parser.py`: Added type annotations to all 50+ command handler methods, `Command.args` typed as `dict[str, Any]`
  - `midi.py`: Fixed `dict` type parameters, added `Iterator` return type for `__iter__`
  - `recorder.py`: Fixed `dict` type parameters, added explicit casts in `from_dict` methods
  - `waveform.py`: Fixed `deque` type parameter
  - `render.py`: Fixed `NDArray` type parameters for return types
  - `api.py`: Added `TracebackType` for `__exit__`, typed `shred_info` return as `dict[str, Any]`
  - `packages.py`: Fixed `_from_info` parameter type
  - `cli/packages.py`: Added `_get_manager` return type annotation
  - `cli/snippets.py`: Fixed `get_snippet_info` return type
  - `session.py`: Added `_file_watcher` attribute, fixed `get_shred_name` return type
  - `common.py`: Added type parameters to `generate_shreds_table`
  - `commands.py`: Fixed `_get_or_create_watcher` return type, removed unnecessary `hasattr` check
  - `executor.py`: Added return type and `FrameType` parameter type to `signal_handler`
  - `repl.py`: Added type annotations to all inner functions (15+ nested handlers), removed unused type ignores
  - `editor.py`: Added type annotations to all 10 key binding handlers
  - `cli/main.py`: Added return type annotations to all 12 command functions

## [0.1.8]

### Fixed

- **Missing pygments dependency**. This is now added.

## [0.1.7]

### Added

- **Pip Install Test Workflow** (`.github/workflows/pip-test.yml`):
  - Installs numchuck from PyPI and runs full test suite
  - Verifies installed package comes from site-packages (not local src/)
  - Tests on Linux and macOS with Python 3.9-3.12

- **WAV File Rendering Tests** (`tests/test_wavfile.py`):
  - `test_render_sine_to_wav` - mono recording with `WvOut`
  - `test_render_stereo_to_wav` - stereo recording with `WvOut2`
  - `test_me_dir_path` - tests `me.dir()` path construction

### Fixed

- **Duplicate macOS wheel builds** (`.github/workflows/wheels.yml`):
  - Removed redundant `macos-15` runner (same ARM64 arch as `macos-14`)
  - Added `CIBW_ARCHS_MACOS: "x86_64 arm64"` for cross-compilation
  - Now builds both Intel and Apple Silicon wheels from single runner

- **Windows access violation during VM cleanup** (upstream fix in `thirdparty/chuck`):
  - Added 50ms delay after VM stop on Windows in `ChucK::shutdown()` (`chuck.cpp`)
  - Allows WASAPI/DirectSound audio threads to fully terminate before cleanup
  - Made `ChucK::shutdown()` public in `chuck.h` for explicit cleanup from bindings
  - Python API: `Chuck.close()` method for explicit shutdown

### Changed

- **Updated platform testing in wheels.yml**:
  - Re-enabled tests on `macosx_arm64` and Windows
  - `manylinux_aarch64` skipped (cross-compiled, no native runner)
  - `wavfile` tests skipped in CI (WvOut timing issues)
  - `chugin` tests skipped in CI (not bundled in wheel)

### Removed

- **install-test.yml** - consolidated into pip-test.yml
- **render-test.yml** - functionality covered by test_wavfile.py

## [0.1.6]

- version bump due to corrupted wheel: `numchuck-0.1.5-cp310-cp310-macosx_11_0_arm64.whl`

## [0.1.5]

### Added

- **Thread Safety Documentation**:
  - Added prominent warning block in `docs/architecture.md` listing unsafe operations during real-time audio playback
  - Documented safe operations (global variable access, event signaling, read-only queries)
  - Added recommended patterns for stopping audio before modifications
  - Added Thread Safety section to `src/numchuck/api.py` module docstring
  - Added Warning sections to `compile()`, `compile_file()`, `remove_shred()`, and `clear()` method docstrings

- **Comprehensive Code Review** (`CODE_REVIEW.md`):
  - Architecture analysis and code quality assessment
  - Identified issues with recommendations
  - Code quality metrics and ratings

- **Install Test Workflow** (`.github/workflows/install-test.yml`):
  - Tests `pip install numchuck` from PyPI on all platforms
  - Verifies extension imports correctly on Linux, macOS, and Windows
  - Tests Python 3.9-3.12 in virtualenv environments

- **TUI Component Tests**:
  - `tests/test_command_parser.py` - 44 tests for REPL command parsing
    - Shred management commands (add, remove, replace)
    - Status and info commands
    - Global variable get/set
    - Event signaling
    - Audio and VM control
    - File operations and snippets
  - `tests/test_tui_common.py` - 15 tests for shared TUI utilities
    - `format_elapsed_time()` edge cases
    - `format_shred_name()` path handling and truncation
    - `generate_shreds_table()` with mock ChucK

- **Expanded test_api.py Coverage**:
  - Added `TestEventCallbacks` class with 5 tests for event signaling and callbacks
  - Added `TestAdvanceMethod` class with 2 tests for advance() behavior
  - Added `TestBufferReuseModes` class with 4 tests for buffer management modes
  - Total test count increased from 143 to 213

### Fixed

- **Broken `numchuck run` command** (`cli/executor.py`):
  - Fixed call to non-existent `ChucK.create()` method
  - Now uses proper initialization sequence: `ChucK()` + `set_param()` + `init()`

- **Hardcoded version strings** (`cli/main.py`):
  - `cmd_version()` and `cmd_info()` now import `__version__` from `_version.py`
  - Previously hardcoded "0.1.1" instead of current version

- **Per-instance callback storage** (`src/_numchuck.cpp`):
  - `set_chout_callback()` and `set_cherr_callback()` now use per-instance storage
  - Previously used static variables shared across all ChucK instances
  - Added thread-local `g_current_chuck` to track active instance during calls
  - Added `ChuckContextGuard` RAII wrapper for compile/run methods
  - Multiple ChucK instances can now have independent output callbacks

- **Memory leak in `replace_shred`** (`src/_numchuck.cpp`):
  - Used `std::unique_ptr` for exception safety during `Chuck_Msg` construction
  - Previously, if argument parsing threw, both `msg` and `msg->args` would leak

- **Improved error propagation for sync getters** (`src/numchuck/api.py`):
  - `get_int()`, `get_float()`, `get_string()` now provide specific error messages
  - Error message explains that callback wasn't invoked and suggests increasing `run_frames`
  - Previously raised generic "Failed to get global X" without actionable guidance

- **Inconsistent error handling in REPL cleanup** (`src/numchuck/tui/repl.py`):
  - Now catches `RuntimeError` specifically for ChucK operations
  - Catches `(RuntimeError, OSError)` for audio operations
  - Previously broad `Exception` catch masked specific errors

- **Flaky test patterns** (multiple test files):
  - `test_global_events.py`: Replaced `try/except pass` with explicit outcome tracking
  - `test_realtime_audio.py`: Fixed bare `except:` to catch specific exceptions with assertions
  - `test_error_handling.py`: dtype tests now explicitly document both valid outcomes

### Changed

- **Documented thread safety in editor** (`src/numchuck/tui/editor.py`):
  - Added docstring explaining prompt_toolkit's single-threaded model
  - Clarifies that `current_tab_index` access is safe (no race condition)

- **Consolidated shreds table rendering** (`tui/common.py`, `tui/repl.py`):
  - Created shared utility functions: `format_elapsed_time()`, `format_shred_name()`, `generate_shreds_table()`
  - Eliminated ~60 lines of duplicated code between REPL and editor
  - Fixed bug in `common.py` using wrong method (`get_param()` instead of `get_param_int()`)
  - Unified time formatting: seconds, minutes+seconds, or hours+minutes

- **Moved imports to module level** in TUI components for better performance:
  - `tui/parser.py`: `ast`
  - `tui/commands.py`: `os`, `sys`, `tempfile`, `time`, `pathlib.Path`, snippet utilities
  - `tui/common.py`: `ChucK`, `ChuckSession`
  - `tui/session.py`: `Project`, `get_projects_dir`

## [0.1.4]

- **Project Renamed**: `numchuck` -> `numchuck`
  - Package import: `from numchuck import Chuck`
  - CLI: `numchuck edit`, `numchuck repl`, `numchuck run`
  - Config directory: `~/.numchuck/`
  - All internal references updated

## [0.1.2]

**Summary:** This release introduces a high-level Pythonic API, cross-platform wheel building, and build system enhancements. The new `Chuck` class provides properties and simplified methods while the low-level API remains available for fine-grained control.

**Key Highlights:**

- New high-level `Chuck` class with Pythonic properties and methods
- Cross-platform wheel building via cibuildwheel (Linux, macOS, Windows)
- Full Linux support with ALSA audio backend
- Multiple `run()` variants for different use cases (zero-allocation real-time loops)
- Full `mypy` type checking support with proper stubs
- Dynamic chugins now output to `examples/chugins/` (not bundled in wheel)
- Improved build system with `scikit-build-core` and `uv`

### Added

- **Cross-Platform Wheel Building** (`.github/workflows/wheels.yml`):
  - cibuildwheel v3.3.0 for automated wheel building
  - Platforms: Linux (manylinux), macOS (ARM64), Windows (x64)
  - Python versions: 3.9, 3.10, 3.11, 3.12, 3.13
  - Source distribution (sdist) building
  - Artifact collection job aggregates all wheels
  - PyPI publishing on tag push (trusted publisher)

- **Consolidated Run API** (`numchuck.api.Chuck`):
  - `run(num_frames, *, output=None, input=None, reuse=False)` - Unified audio processing
    - No args: allocates new buffer each call (prototyping, offline)
    - `output=buf`: uses provided buffer (zero allocation)
    - `output=buf, input=buf`: effect mode with both buffers
    - `reuse=True`: uses internal buffer (zero GC without manual management)
  - `advance(num_frames)` - Advance VM time without returning audio (callbacks/events)
  - Clean two-method API replaces previous five methods
  - Comprehensive tests for all usage patterns

- **Linux Build Support**:
  - Parser generation with bison/flex on Linux
  - ALSA audio backend (`__LINUX_ALSA__`, `__PLATFORM_LINUX__`)
  - Link libraries: `-ldl`, `-lpthread`, `-lm`, `-lasound`, `-lsndfile`
  - Position-independent code (`-fPIC`) for shared library linking

- **High-Level Python API** (`numchuck.api.Chuck`):
  - Pythonic wrapper class with properties instead of get/set methods
  - Properties: `sample_rate`, `version`, `chugin_enable`, `working_directory`, etc.
  - Simplified methods: `compile()`, `run()`, `set_int()`, `get_int()`, etc.
  - Synchronous global variable getters (handles async callbacks internally)
  - Constructor with all parameters as kwargs with sensible defaults
  - Access low-level API via `chuck.raw` property
  - Exported directly from `numchuck` package: `from numchuck import Chuck`

- **Type Stub Improvements** (`_numchuck.pyi`):
  - Added 8 missing PARAM_* constants (TTY_COLOR, TTY_WIDTH_HINT, COMPILER_HIGHLIGHT_ON_ERROR, etc.)
  - Renamed from `__init__.pyi` to `_numchuck.pyi` to match module
  - Added `py.typed` marker for PEP 561 compliance

- **Developer Dependencies**:
  - Added `types-Pygments>=2.18.0` for mypy compatibility

- **Strict Chugin Tests** (`tests/test_examples.py`):
  - `test_chugin_bitcrusher_strict` - Verifies Bitcrusher chugin loads and produces audio
  - `test_chugin_gverb_strict` - Verifies GVerb chugin loads and processes reverb
  - `test_chugin_convrev_example` - Tests loading `examples/convrev/ConvRev.ck` with IR file
  - Uses `PARAM_IMPORT_PATH_SYSTEM` to set chugin search path (matching chuck-max)
  - Uses `@import "<chugin-name>";` syntax to load chugins
  - Tests skip gracefully if chugins not built

### Changed

- **Package Exports**:
  - `numchuck` now exports only the high-level `Chuck` class
  - Low-level API available via `from numchuck._numchuck import ChucK`
  - Internal modules import from `_numchuck` directly

- **Chugin Build System** (`scripts/cmake/fn_add_chugin.cmake`):
  - Dynamic chugins now output to `examples/chugins/` directory
  - Removed wheel installation of `.chug` files
  - Chugins managed externally
  - Codesigning moved from install-time to post-build command

- **API Method Signatures** (`api.py`):
  - `remove_shred()` returns `None` (not `bool`)
  - `replace_shred()` returns `int` (new shred ID, 0 on failure)
  - `signal_event()` and `broadcast_event()` return `None`
  - `on_event()` returns `int` callback ID, added `stop_listening_for_event()`

### Changed

- **macOS Deployment Target**:
  - Updated from 10.14/10.15 to 11.0 (required for ARM64 Macs)
  - Applied consistently in CMakeLists.txt, pyproject.toml, and wheels.yml

- **cibuildwheel Configuration**:
  - Removed `pp*` from skip selector (PyPy not enabled, was causing warnings)
  - Test skip includes Windows (access violation in tests)
  - Before-build command uses correct shell operator precedence

### Fixed

- **Windows Build** (LNK1149 linking error):
  - Fixed `chuck_lib` output naming conflict with `chuck` executable
  - Renamed library output to `chuckcore.lib` on Windows
  - Both targets can now coexist without import library collision

- **GCC 14+ Compatibility** (manylinux builds):
  - Fixed `invalid conversion from 'void*' to '__timezone_ptr_t'` error
  - Added `-fpermissive` flag for GCC 14+ in ChucK core compilation
  - Allows implicit void* conversions in legacy C code

- **Linux Shared Library Linking** (relocation error):
  - Added `-fPIC` to chuck_lib on Linux
  - Required for linking static library into Python extension (.so)
  - Fixes `R_X86_64_32S` relocation error on x86_64

- **Type Checking** (`make typecheck` now passes):
  - Fixed `set_param` vs `set_param_string` for working_directory
  - Fixed `compile_code` return type handling in executor.py
  - Added type annotation for `shred_versions` dict in project.py
  - Fixed variable shadowing (`f` -> `fh`) in executor.py

- **Linting** (`make lint` passes):
  - Removed unused variables (`version_parser`, `info_parser`, `count`)
  - Changed bare `except:` to `except Exception:`

---

## [0.1.1]

**Summary:** This release focuses on critical bug fixes, comprehensive documentation, developer experience improvements, and productivity enhancements. All critical and high-priority issues identified in the code review have been resolved, along with low-priority code quality improvements.

**Key Highlights:**

- Fixed segmentation fault on test exit (exit code 139 -> 0)
- Standardized error handling with comprehensive documentation
- Documented event listener cleanup to prevent memory leaks
- Renamed `exec` -> `run` CLI subcommand for consistency
- Updated build system to use `uv` throughout
- Increased test coverage (96 -> 114 tests, all passing)
- Added 15 integration tests for end-to-end workflows
- Fixed all 15 remaining bare except clauses in TUI code
- Added shell completion support (bash and zsh)
- Added performance benchmarks for regression detection
- Single version source following Python best practices
- CI/CD pipeline with multi-platform testing
- Type stubs for IDE autocomplete and type checking
- Sphinx documentation structure ready to deploy

### Added

- **Comprehensive Error Handling Documentation** (`docs/error_handling.md`):
  - Complete guide to exception-based error handling in numchuck
  - Examples for all API patterns (initialization, compilation, events, etc.)
  - Best practices for error handling and resource cleanup
  - Input validation rules and error message formats
  - Debugging tips and common patterns
  - ~400 lines of detailed documentation

- **Event Listener Cleanup Tests** (`tests/test_global_events.py`):
  - `test_listen_for_event()` - Verifies listener registration and callback invocation
  - `test_stop_listening_for_event()` - Verifies cleanup prevents memory leaks
  - `test_multiple_event_listeners()` - Verifies cleanup API functionality
  - Total event tests increased from 3 to 6
  - Documents proper usage of `stop_listening_for_global_event()` API

### Fixed

- **Segmentation Fault on Test Exit** (Critical):
  - Fixed exit code 139 (SIGSEGV) that occurred after all tests passed
  - Root cause: Global callback map held Python objects that outlived interpreter
  - Solution: Added `atexit` cleanup to destroy Python objects before shutdown
  - Implemented `_cleanup_callbacks()` function registered with Python's `atexit`
  - All tests now exit cleanly with exit code 0
  - See `SEGFAULT_FIX.md` for detailed technical analysis

- **Error Handling Consistency** (Critical):
  - Standardized all error handling to use exceptions consistently
  - `ValueError` for invalid input parameters (empty strings, zero/negative values)
  - `RuntimeError` for operational failures (not initialized, operation failed)
  - Compilation errors return `(False, [])` tuple (syntax errors are expected)
  - Added comprehensive module docstring documenting error strategy
  - See `docs/ERROR_HANDLING.md` for complete guide

- **Event Listener Memory Leak Documentation** (Critical):
  - Documented that `listen_for_global_event()` returns listener ID for cleanup
  - Added examples showing proper use of `stop_listening_for_global_event()`
  - Memory leak prevention pattern now clearly documented and tested
  - No API changes needed (cleanup already existed but was undocumented)

- **CLI Subcommand Renamed**: `exec` -> `run`:
  - `numchuck run` replaces `numchuck exec` for consistency with common CLI conventions
  - Updated all documentation (README, CLAUDE.md, CHANGELOG.md, architecture.md)
  - Updated tests and Makefile
  - Backward compatibility can be added if needed

- **Build System Updates**:
  - Makefile now uses `uv` for all Python operations
  - `make install` -> `uv sync --reinstall-package numchuck`
  - `make test` -> `uv run pytest` (uses pyproject.toml config)
  - `make repl` -> `uv run python -m numchuck repl`
  - pytest configuration in pyproject.toml to skip thirdparty/

- **Module Documentation**:
  - Added comprehensive docstring to `src/numchuck/__init__.py`
  - Documents exception types and when they're raised
  - Includes usage examples
  - Clear error handling contract

- **Bare Except Clauses** (Code Quality):
  - Fixed all 15 remaining bare except clauses in TUI code
  - Replaced with specific exception types: RuntimeError, AttributeError, ValueError, etc.
  - Improved error handling in completion handlers
  - Better error handling in UI display code (shred tables, status bars)
  - Prevents masking of critical exceptions (KeyboardInterrupt, SystemExit)

- **Type Stubs** (`src/numchuck/__init__.pyi`):
  - Complete type annotations for all public APIs
  - ChucK class with all methods typed
  - Module-level functions with signatures
  - All constants declared with types
  - Enables IDE autocomplete and type checking with mypy
  - ~200 lines of comprehensive type hints

- **CI/CD Pipeline** (`.github/workflows/ci.yml`):
  - Multi-platform testing (Ubuntu, macOS, Windows)
  - Python 3.9-3.13 support matrix
  - Automated build and test on push/PR
  - Lint job with ruff and mypy
  - Wheel building with cibuildwheel
  - Coverage reporting with codecov
  - Exit code verification for clean test runs

- **API Documentation Structure** (`docs/api/`):
  - Sphinx configuration with autodoc and napoleon
  - RTD theme setup
  - Complete ChucK class reference
  - Quick start guide and examples
  - Build requirements and instructions
  - Intersphinx mapping to Python/NumPy docs

- **Version Management** (`src/numchuck/_version.py`):
  - Single source for version number
  - Imported by `__init__.py` for `__version__` and `__version_info__`
  - Eliminates version duplication across the codebase
  - Follows Python packaging best practices

- **Shell Completion Support** (`completions/`):
  - Bash completion script (`numchuck-completion.bash`)
  - Zsh completion script (`numchuck-completion.zsh`)
  - Complete all subcommands: edit, repl, run, version, info
  - Complete command-line options for each subcommand
  - Complete `.ck` file paths automatically
  - Complete project names from `~/.numchuck/projects/`
  - Suggest common sample rates and channel counts
  - Installation instructions in `completions/README.md`

- **Performance Benchmarks** (`benchmarks/`):
  - `benchmark_simple.py` - Core performance measurements
  - Benchmarks code compilation speed (ops/sec)
  - Benchmarks audio rendering throughput (MB/s)
  - Benchmarks global variable access latency
  - Benchmarks event signaling performance
  - Comprehensive README with usage examples and performance targets
  - Baseline measurements for performance regression detection

- **Integration Tests** (`tests/test_integration.py`):
  - 15 comprehensive end-to-end workflow tests
  - TestLiveCodingWorkflow - Spork/replace/remove cycles
  - TestGlobalCommunication - Python-ChucK variable and event communication
  - TestAudioProcessingWorkflows - Offline rendering and real-time transitions
  - TestFileWorkflows - File compilation and multi-file scenarios
  - TestVMLifecycle - VM initialization and state management
  - TestErrorRecovery - Compilation error handling and recovery
  - TestConcurrentOperations - Rapid operations and stability testing
  - Increased test count from 99 to 114 tests

### Changed

- **Test Suite Improvements**:
  - Total tests increased from 96 to 114 (+18 tests)
  - Added 15 comprehensive integration tests
  - Added 3 event listener cleanup tests
  - All tests pass with clean exit (exit code 0)
  - pytest config excludes thirdparty/ and other non-test directories
  - Comprehensive end-to-end workflow coverage

- **Multi-Tab Editor** (`numchuck edit`):
  - Full-screen ChucK editor with syntax highlighting
  - Multi-tab support: Ctrl-T (new), Ctrl-W (close), Ctrl-N/Ctrl-P (navigate)
  - F5 or Ctrl-R to spork (compile and run current buffer)
  - F6 to replace running shred with current buffer
  - Ctrl-O to open files with interactive dialog
  - Ctrl-S to save files
  - Ctrl-A to start audio
  - Tab names show shred IDs after sporking (e.g., `bass-1.ck`)
  - Project versioning integration
  - F1/F2/F3 for help/shreds/log windows
  - Ctrl-Q for clean exit with proper resource cleanup
  - Implemented in `tui/editor.py` (~410 lines)

- **Project Versioning System** (`tui/project.py`):
  - Automatic file versioning for livecoding sessions
  - Versioning scheme: `file.ck` -> `file-1.ck` (spork) -> `file-1-1.ck` (replace)
  - Stored in `~/.numchuck/projects/<project_name>/`
  - Tracks spork and replace operations with shred IDs
  - Chronological timeline support with modification times
  - `ProjectVersion` class for parsing and generating versioned filenames
  - `Project` class for managing project directories and version history
  - Complete test coverage in `test_project_versioning.py` (10 tests)

- **Shared TUI Base Class** (`tui/common.py`):
  - `ChuckApplication` base class for editor and REPL
  - Common key bindings: F1 (help), F2 (shreds), F3 (log), Ctrl-Q (exit)
  - Reusable UI components: help window, shreds table, log window
  - Centralized ChucK instance and session management
  - Proper cleanup with circular reference breaking (no memory leaks)

- **Command-Line Execution Mode** (`numchuck run`):
  - Non-interactive file execution from command line
  - Multiple file support
  - Duration parameter: `--duration N` runs for N seconds then exits
  - Silent mode: `--silent` runs without audio (useful for testing)
  - Custom sample rate: `--srate N`
  - Custom channel count: `--channels N`
  - Signal handling for graceful shutdown (Ctrl-C)
  - Implemented in `cli/executor.py` (~120 lines)

- **Subcommand-Based CLI** (`cli/main.py`):
  - `numchuck edit [files...] [--project name] [--start-audio]` - Launch editor
  - `numchuck repl [files...] [--project name] [--start-audio]` - Launch REPL
  - `numchuck run <files...> [options]` - Execute files
  - `numchuck version` - Show version information
  - `numchuck info` - Show ChucK and numchuck info
  - `numchuck tui` - Backward compatibility alias for repl
  - Comprehensive argument parsing with help text
  - Command handlers in separate module
  - ~220 lines of clean CLI code

- **Chuck-Style REPL Commands**:
  - `add <file>` or `+ <file>` - Spork a file as new shred
  - `remove <id>` or `- <id>` - Remove shred by ID
  - `remove all` or `- all` - Remove all shreds
  - `replace <id> <file>` - Replace shred with code from file
  - `status` - Show VM status (shreds, audio, now time)
  - `time` - Show current ChucK time
  - Consistent with chuck executable command style
  - Updated parser to support word-based commands
  - Shortcut symbols still supported for compatibility

- **REPL File Loading on Startup**:
  - Load ChucK files on REPL startup: `numchuck repl file1.ck file2.ck`
  - Files are automatically sporked before entering interactive mode
  - Works with project versioning when `--project` specified
  - Implemented in `tui/repl.py` run() method

- **Test Suite Expansion**:
  - `test_project_versioning.py` - 10 tests for versioning system
  - `test_cli.py` - 10 tests for CLI argument parsing
  - **Total: 93 tests, 100% passing**
  - Comprehensive coverage of new features
  - No regressions in existing tests

- **Full-Screen REPL Application**:
  - Converted to full-screen `prompt_toolkit` Application with stable layout
  - Mouse support enabled for scrolling in log/help windows
  - No layout disruption from ChucK VM or error messages
  - Clean separation of input, output, status, and auxiliary windows

- **Topbar for Active Shreds**:
  - Minimal topbar displaying shred IDs only
  - Format: `Shreds: [1] [2] [3]  (F2: table)`
  - Symmetrical with bottom status toolbar
  - Gap between topbar and input area for clean layout
  - Topbar updates automatically when shreds are added/removed

- **Shreds Table Window**:
  - Toggle detailed shreds table with F2
  - Displays comprehensive shred information in tabular format
  - Columns: ID, Name (filename or code snippet), Time (ChucK VM time when launched)
  - Shows only filename for file shreds (not full path)
  - Time displayed relative to audio thread start (ChucK VM samples/seconds)
  - Auto-formats time: samples (< 1s), seconds, minutes, hours
  - Styled with cyan on dark blue (matching WebChucK aesthetic)
  - Updates in real-time when toggled
  - Clean, aligned table with Unicode separators

- **Help Window**:
  - Toggle help display with F1 or `help` command
  - Two-column compact layout fitting in 20 lines
  - Non-scrollable, static content
  - Displays all REPL commands and keyboard shortcuts
  - Appears above status bar without disrupting layout

- **Log Window**:
  - Toggle ChucK VM log with Ctrl+L
  - Scrollable display of last 100 VM messages
  - Captures all stdout/stderr from ChucK VM
  - Auto-scrolls to bottom for new messages
  - Mouse and keyboard scrolling support
  - Distinct styling (lighter gray) from help window

- **Edit Shred Command**:
  - Edit and replace running shreds with `edit <id>` (e.g., `edit 1`, `edit 2`)
  - Uses ChucK shred IDs consistently with remove command
  - Opens shred source in $EDITOR
  - Automatically replaces shred with modified code on save
  - Converts relative file paths to absolute paths for editing

- **Error Display Bar**:
  - Errors shown in dedicated red error bar above log/help windows
  - Appears only when there's an error (conditional display)
  - All errors routed through error bar instead of `print()` calls
  - Prevents layout disruption in full-screen mode
  - Auto-clears on next command
  - Handles unknown commands gracefully

- **ChucK Language Module** (`src/numchuck/chuck_lang.py`):
  - Single source of truth for all ChucK language elements
  - Complete sets: KEYWORDS, TYPES, OPERATORS, TIME_UNITS, UGENS, STD_CLASSES
  - 80+ UGens including oscillators, filters, reverbs, STK instruments, chugins
  - Standard library: MATH_FUNCTIONS, STD_FUNCTIONS
  - REPL_COMMANDS for command completion
  - Helper functions: `is_keyword()`, `is_type()`, `is_ugen()`, `is_builtin()`, `get_category()`
  - Comprehensive documentation of ChucK language specification

- **ChucK Code Completion in REPL**:
  - Tab completion for ChucK keywords (if, while, for, class, fun, etc.)
  - Tab completion for ChucK types (int, float, time, dur, etc.)
  - Tab completion for UGens (SinOsc, LPF, JCRev, ADSR, etc.)
  - Tab completion for standard library (Math, Std, FileIO, MidiIn, etc.)
  - Visual distinction with 'ChucK' metadata in completion menu
  - Context-aware: completes word under cursor
  - REPL commands retain first priority
  - Updates help text to document code completion

### Changed

- **REPL Architecture Refactoring**:
  - Migrated from `PromptSession` to full-screen `Application` with custom layout
  - Supports complex layouts (topbar, gap, input area, bottom toolbar)
  - Eliminated `print()` calls for state-changing commands to prevent layout disruption
  - Silent operation for audio control and shred management
  - Better control over rendering and event handling
  - Enables future enhancements (multiple panes, advanced UI features)

- **ChucK Lexer Refactoring**:
  - Now uses `chuck_lang` module as source of truth
  - Dynamically builds patterns from KEYWORDS, TYPES, UGENS, STD_CLASSES, TIME_UNITS
  - Removed hardcoded language element lists
  - Moved `dac`, `adc`, `blackhole` from keywords to UGens for correct highlighting

- **REPL Command Completion**:
  - Now uses `chuck_lang.REPL_COMMANDS` instead of hardcoded list
  - Ensures consistency across all components

- **Shreds Table Display**:
  - Updated to show parent folder + filename instead of just filename
  - Widened table from 60 to 78 characters for better readability
  - Elapsed time column shows time since shred was sporked (not raw VM samples)
  - Format: `parentfolder/file.ck` with up to 56 characters for name

### Fixed

- **Shreds Table Display Bug**:
  - Fixed shreds table showing source code instead of filenames (both REPL and editor)
  - Table now correctly displays filename from `info['name']` instead of `info['source']`
  - Extracts just filename or parent/filename from full path for cleaner display
  - Elapsed time calculated correctly from current VM time minus spork time

- **REPL Exit Crash with Audio**:
  - Fixed segmentation fault when pressing Ctrl-Q with audio running
  - Cleanup now properly calls `stop_audio()` before `shutdown_audio()`
  - Added proper error handling for each cleanup step
  - Shreds are now removed before stopping audio to prevent callback issues

- **Editor File Open Dialog**:
  - Fixed Ctrl-O crash caused by nested event loop conflict
  - Implemented proper floating dialog with `CompletionsMenu` support
  - Tab completion now works like standard shell completion (inserts common prefix first)
  - Added custom key bindings to prevent Tab from being used for focus navigation
  - Dialog properly cleans up floats list on close

- **Editor Dynamic Tab Switching**:
  - Fixed opened files not appearing after Ctrl-O
  - Layout now uses `DynamicContainer` to update editor content when switching tabs
  - New tabs are automatically focused after opening

### Technical Details

- All 93 tests pass (73 original + 20 new)
- ChucK lexer tests verify correct categorization of language elements
- Completion system preserves REPL command priority
- `chuck_lang` module provides forward compatibility for language specification updates
- Zero memory leaks with proper cleanup and circular reference breaking

## [0.1.3]

### Added

- **ChucK Pygments Lexer** (`src/numchuck/cli/chuck_lexer.py`):
  - Complete syntax highlighting for ChucK language
  - Recognizes ChucK operators (`=>`, `+=>`, `@=>`, etc.)
  - Time duration literals (`100::ms`, `1::second`, etc.)
  - 80+ built-in UGens (SinOsc, LPF, ADSR, JCRev, dac, etc.)
  - Keywords, types, standard library (Math, Std, Machine)
  - Comments, strings, numbers (int, float, hex)
  - Integrated into REPL for syntax-highlighted input
  - 16 comprehensive tests in `tests/test_chuck_lexer.py`
  - Documentation: `docs/CHUCK_LEXER.md`

- **Centralized Path Management** (`src/numchuck/cli/paths.py`):
  - `get_numchuck_home()` - Returns `~/.numchuck`
  - `get_snippets_dir()` - Returns `~/.numchuck/snippets`
  - `get_history_file()` - Returns `~/.numchuck/history`
  - `get_sessions_dir()`, `get_logs_dir()`, `get_projects_dir()`, `get_config_file()` - Future directories
  - `ensure_numchuck_directories()` - Creates directory structure
  - `list_snippets()`, `get_snippet_path()` - Snippet utilities

- **REPL Enhancements**:
  - `cls` command - Clear screen without affecting VM state
  - Colored prompt `[=>]` with orange brackets and green chuck operator
  - Screen clears on REPL startup for clean interface
  - Prompt updated to `[=>]` matching ChucK logo
  - **Smart Enter mode (enabled by default)**:
    - Enter on REPL commands (quit, help, +, -, etc.) submits immediately
    - Enter on ChucK code inserts newline (multiline editing)
    - Esc+Enter always submits code
    - Continuation prompt shows `...` for multiline input
  - **Direct ChucK code compilation** - Multiline code automatically detected and compiled
  - Auto-detection based on ChucK markers (=>, ;, {, newlines)
  - No need for special commands or mode switching

- **Documentation**:
  - `docs/numchuck_home.md` - Complete guide to `~/.numchuck/` directory structure
  - `docs/chuck_lexer.md` - ChucK lexer usage and implementation guide

### Changed

- **Directory Structure Migration**:
  - `~/.chuck_repl_history` -> `~/.numchuck/history`
  - `~/.chuck_snippets/` -> `~/.numchuck/snippets/`
  - REPL now creates full `~/.numchuck/` directory structure on startup
  - Updated all code to use new path utilities from `paths.py`
  - Updated `.gitignore` to ignore `~/.numchuck/` instead of individual files

- **REPL Improvements**:
  - REPL version display updated to show "PyChucK REPL v0.1.1"
  - Help text updated with `cls` command under "Screen:" section
  - Help text updated with "Multiline Input (Smart Enter Mode):" section
  - Tab completion includes `cls` command (removed `ml`)
  - README.md mentions ChucK syntax highlighting feature
  - **prompt-toolkit is now a required dependency** (no longer optional)
  - Simplified REPL initialization by removing readline/libedit fallback code
  - REPL mode display simplified (removed mode indicator)
  - **Multiline editing enabled by default** (no special mode needed)
  - **Smart Enter mode**: Context-aware Enter behavior
  - Added prompt continuation (`...`) for multiline input
  - Auto-detection of ChucK code (checks for `=>`, `;`, `{`, or newlines)
  - Parser suppresses "Unknown command" for ChucK code patterns
  - `smart_enter` parameter in ChuckREPL constructor (defaults to True)

- **Command-line interface**:
  - `python -m numchuck tui` now launches vanilla REPL directly
  - Added `--start-audio` flag to automatically start audio on REPL startup
  - Added `--no-smart-enter` flag to disable smart Enter mode
  - Removed `--rich`, `--simple`, `--basic` command-line flags
  - `tui.py` simplified to only launch vanilla REPL
  - Updated README.md to reflect vanilla REPL as sole interface

### Removed

- **Textual/Rich TUI implementation removed**:
  - Removed `tui_rich.py`, `tui_simple.py`, `tui_basic.py` implementations
  - Removed `tui_rich.tcss` stylesheet
  - Removed `widgets/` directory and all custom widgets
  - Removed `test_textual_minimal.py` test file
  - Removed textual-related documentation files:
    - `docs/dev/DEBUG_BLACK_SCREEN.md`
    - `docs/dev/MOUSE_FIX.md`
    - `docs/dev/RICH_TUI_IMPROVEMENTS.md`
    - `docs/dev/TUI_README.md`

- **Old Path Structure**:
  - Removed references to `~/.chuck_snippets/`
  - Removed references to `~/.chuck_repl_history`

- **Readline/libedit fallback code removed**:
  - Removed ~85 lines of readline/libedit fallback code from `repl.py`
  - Removed `use_prompt_toolkit` and `use_readline` flags
  - Removed conditional input prompt logic
  - Simplified multiline mode to only use prompt-toolkit

- **Multiline mode command removed**:
  - Removed `ml` command (multiline mode is now always enabled)
  - Removed `_multiline_mode()` method from REPL
  - Removed `_cmd_multiline()` from command executor
  - Removed multiline pattern from command parser
  - Removed `ml` from tab completion list

### Technical Details

- All 76 tests pass (60 original + 16 lexer tests)
- ChucK lexer follows Pygments best practices (RegexLexer)
- Colored prompt uses HTML formatting for prompt_toolkit
- Smart Enter mode uses `@Condition` decorator for dynamic multiline behavior
- Path management provides forward compatibility for sessions, logs, projects, config
- Migration guide included in `docs/PYCHUCK_HOME.md`
- prompt-toolkit is now a required dependency (imported directly, no fallbacks)
- Pygments is a dependency of prompt_toolkit, so no need to declare it separately

### Summary

Version 0.1.3 represents a major REPL overhaul focused on user experience:

**Key Improvements:**

1. **Smart multiline editing** - Context-aware Enter behavior eliminates mode switching
2. **ChucK syntax highlighting** - Full Pygments lexer for ChucK language
3. **Automatic code detection** - ChucK code is compiled, commands are executed
4. **Unified directory structure** - All user data in `~/.numchuck/`
5. **Required prompt-toolkit** - Simplified codebase, better UX
6. **CLI options** - `--start-audio` and `--no-smart-enter` flags

The REPL now provides a modern, intuitive interface for both quick REPL commands and multiline ChucK programming.

---

## [0.1.2]

### Added

#### Global Variable Management

- **Bidirectional Python/ChucK communication** via ChucK globals manager:
  - `set_global_int()`, `set_global_float()`, `set_global_string()` - Set primitive globals from Python
  - `get_global_int()`, `get_global_float()`, `get_global_string()` - Get primitives via async callbacks
  - `set_global_int_array()`, `set_global_float_array()` - Set entire arrays
  - `get_global_int_array()`, `get_global_float_array()` - Get arrays via callbacks
  - `set_global_int_array_value()`, `set_global_float_array_value()` - Set individual array elements by index
  - `set_global_associative_int_array_value()`, `set_global_associative_float_array_value()` - Set associative array (map) values by key
  - `get_all_globals()` - List all global variables as (type, name) tuples
  - **Use case**: Real-time parameter control, data exchange between Python and ChucK shreds

#### Global Event Signaling

- **Event-driven Python/ChucK communication**:
  - `signal_global_event()` - Wake one waiting shred on global event
  - `broadcast_global_event()` - Wake all waiting shreds on global event
  - `listen_for_global_event()` - Register Python callback for ChucK events (returns listener ID)
  - `stop_listening_for_global_event()` - Unregister callback by ID
  - **Use case**: Trigger musical events from Python, receive notifications from ChucK

#### Shred Management & Introspection

- **Advanced shred control and debugging**:
  - `remove_shred()` - Remove shred by ID
  - `get_all_shred_ids()` - List all running shreds
  - `get_ready_shred_ids()` - List ready (non-blocked) shreds
  - `get_blocked_shred_ids()` - List blocked shreds
  - `get_last_shred_id()` - Get most recently sporked shred ID
  - `get_next_shred_id()` - Query what next shred ID will be
  - `get_shred_info()` - Get detailed shred info (ID, name, running status, done status)
  - **Use case**: Live coding workflows, debugging, monitoring VM state

#### VM Control Messages

- **Fine-grained VM state management**:
  - `clear_vm()` - Remove all shreds
  - `clear_globals()` - Clear global variables without removing shreds
  - `reset_shred_id()` - Reset shred ID counter
  - `replace_shred()` - Hot-swap running shred with new code (returns new shred ID)
  - **Use case**: Live coding, iterative development, performance workflows

#### Additional Parameter Constants

- **8 new ChucK parameter constants** for advanced configuration:
  - `PARAM_OTF_PRINT_WARNINGS` - Print on-the-fly compiler warnings
  - `PARAM_IS_REALTIME_AUDIO_HINT` - Hint for real-time audio mode
  - `PARAM_COMPILER_HIGHLIGHT_ON_ERROR` - Syntax highlighting in error messages
  - `PARAM_TTY_COLOR` - Enable color output in terminal
  - `PARAM_TTY_WIDTH_HINT` - Terminal width hint for formatting
  - `PARAM_IMPORT_PATH_SYSTEM` - System import search paths
  - `PARAM_IMPORT_PATH_PACKAGES` - Package import search paths
  - `PARAM_IMPORT_PATH_USER` - User import search paths

#### Callback Management & Output Control

- **Enhanced console output handling**:
  - `set_chout_callback()` - Capture ChucK console output (chout)
  - `set_cherr_callback()` - Capture ChucK error output (cherr)
  - `set_stdout_callback()` - Capture global stdout (static)
  - `set_stderr_callback()` - Capture global stderr (static)
  - `toggle_global_color_textoutput()` - Enable/disable color output
  - `probe_chugins()` - Print info on all loaded chugins
  - **Use case**: Custom logging, GUI integration, debugging

#### Testing

- **14 new comprehensive tests** (60 total, 100% pass rate):
  - **Global variables**: 6 tests covering primitives, arrays, associative arrays
  - **Global events**: 3 tests for signal, broadcast, error handling
  - **Shred management**: 5 tests for removal, introspection, VM control
  - All tests use audio cycle processing for proper message queue handling
  - Helper function `run_audio_cycles()` for reliable async operation testing

### Changed

- **Type stub file (`_numchuck.pyi`)** updated with all new methods:
  - 30+ new method signatures with full type annotations
  - Callback types use `Callable` with proper signatures
  - Return types for introspection methods (`list[int]`, `dict[str, Any]`, etc.)
  - Complete docstrings for all new methods

### Technical Details

#### Thread-Safe Callback Architecture

- **Global callback storage** with mutex protection:
  - `g_callbacks` map stores Python callables by ID
  - `g_callback_mutex` ensures thread-safe access
  - `store_callback()`, `get_callback()`, `remove_callback()` helper functions
  - Automatic cleanup for one-shot callbacks (get operations)
  - Persistent storage for event listeners (until explicitly removed)

- **C++ callback wrappers** with GIL management:
  - `cb_get_int_wrapper()`, `cb_get_float_wrapper()`, `cb_get_string_wrapper()`
  - `cb_get_int_array_wrapper()`, `cb_get_float_array_wrapper()`
  - `cb_event_wrapper()` for persistent event listeners
  - All wrappers use `nb::gil_scoped_acquire` for Python callback invocation

#### Message Queue Integration

- **Proper ChucK VM integration**:
  - Global operations use `Chuck_Globals_Manager` message queue
  - VM operations use `Chuck_VM::queue_msg()` and `process_msg()`
  - All operations validated with `!self.vm()` and `!self.globals()` checks
  - Error handling with descriptive `RuntimeError` messages

#### Code Architecture Improvements

- Added `chuck_globals.h` and `chuck_vm.h` includes
- Added `<unordered_map>` and `<memory>` for callback storage
- Event listener IDs returned to Python for lifecycle management
- `replace_shred()` compiles code with `count=0` then sends `CK_MSG_REPLACE`

### Design Decisions

- **Asynchronous global variable gets** via callbacks (not blocking):
  - ChucK's message queue is processed during audio cycles
  - Blocking would deadlock if VM not running audio
  - Callback pattern matches ChucK's threading model
  - Consistent with Max/MSP chuck~ external architecture

- **Event listener persistence**:
  - Event callbacks stored until explicitly removed
  - Allows Python to react to ChucK events continuously
  - Listener ID returned for lifecycle control
  - `listen_forever` parameter controls one-shot vs persistent behavior

### Security

- All global variable operations validated before queue insertion
- Shred ID bounds checking in `get_shred_info()`
- VM/globals manager null pointer checks before operations
- Callback ID validation prevents accessing invalid callbacks

### Performance

- Callback lookup: O(1) via `unordered_map`
- Minimal overhead for global variable operations (message queue only)
- Event listeners don't remove callbacks on trigger (persistent)
- No memory leaks with proper callback cleanup

### Inspired By

Implementation based on analysis of `chuck_tilde.cpp` (Max/MSP external):

- Global variable management patterns (lines 1398-1497, 1631-1783)
- Event signaling architecture (lines 1506-1526, 1785-1801)
- Shred introspection methods (lines 662-710, 1255-1269)
- VM message passing (lines 884-904, 1100-1253)

---

## [0.1.1]

### Added

- Comprehensive architecture documentation in `ARCHITECTURE.md`
  - System architecture diagrams and data flow
  - Component details and responsibilities
  - Current limitations and future improvements
  - Thread safety analysis
  - Performance characteristics
  - Security considerations

- **Extensive error handling test suite** (`tests/test_error_handling.py`):
  - **30 new comprehensive tests** covering all error paths
  - **Parameter validation tests** (4 tests):
    - Empty code/file path rejection
    - Zero count validation
  - **Initialization state tests** (4 tests):
    - Compilation requires initialization
    - Audio processing requires initialization
    - Start audio requires initialization
  - **Buffer validation tests** (10 tests):
    - Negative/zero frame validation
    - Input/output buffer size mismatch detection
    - Wrong dtype handling (float64 vs float32)
    - Multidimensional array rejection
    - Zero input channels with input data
    - Large buffer stress test (10 seconds of audio)
  - **Audio system validation tests** (3 tests):
    - Zero sample rate rejection
    - Zero channels validation
    - Zero buffer size rejection
  - **Compilation error tests** (4 tests):
    - Invalid ChucK syntax (returns False, not crash)
    - Non-existent file handling
    - Undefined class detection
    - Type mismatch errors
  - **Edge cases and boundary conditions** (5 tests):
    - Multiple shred compilation (count > 1)
    - Multiple init calls handling (returns 0 when already initialized)
    - Sequential compile and remove cycles
    - Audio stop/shutdown without start (safe, no crash)
  - **Test coverage**: 45 total tests (15 original + 30 new), 100% pass rate
  - All tests validate descriptive error messages and proper exception types

- **Python example scripts** (`examples/python/` - 9 comprehensive examples):
  - **01_basic_sine.py**: Real-time sine wave playback (basic setup)
  - **02_offline_render.py**: Offline rendering to numpy arrays with frequency sweep, optional plotting/WAV export
  - **03_load_chuck_file.py**: Loading external .ck files from `examples/basic/`
  - **04_multiple_shreds.py**: Running multiple concurrent shreds, harmonic series, dynamic management
  - **05_bitcrusher_chugin.py**: Using Bitcrusher effect plugin with parameter sweeping
  - **06_reverb_chugin.py**: Using GVerb reverb plugin for spatial effects
  - **07_parameter_control.py**: ChucK VM configuration and parameter inspection
  - **08_advanced_synthesis.py**: FM synthesis with filtering, envelopes, and melodic sequences
  - **09_sequenced_shreds.py**: Time-sequenced shred playback, building composition layer by layer with rhythmic patterns
  - **README.md**: Comprehensive guide with usage patterns, troubleshooting, and learning path
  - All examples include detailed docstrings and comments
  - Progressive learning path from basic to advanced techniques
  - Demonstrates both real-time and offline processing
  - Shows chugin integration and file loading

### Changed

- **Type stub file (`_numchuck.pyi`)** completely rewritten to match actual implementation
  - Fixed incorrect method signatures (module functions vs class methods)
  - Added all parameter constants
  - Added comprehensive docstrings
  - Proper static type checking support
- **License classifier** corrected from invalid `GPL3 License` to `GNU General Public License v2 (GPLv2)`
- Added development status classifier: `Development Status :: 3 - Alpha`
- Added Python version classifiers (3.8-3.12)

### Fixed

#### Critical Fixes

- **Input validation and error handling** throughout C++ bindings:
  - Added `validate_audio_buffer()` template function for numpy array validation
  - Validates array dimensions, sizes, and types before passing to ChucK
  - `compile_code()` now validates non-empty code, count > 0, and initialization state
  - `compile_file()` now validates non-empty path, count > 0, and initialization state
  - `run()` now validates initialization, num_frames > 0, and correct buffer sizes
  - All validation errors throw descriptive Python exceptions

- **Audio callback architecture** improved for safety:
  - Replaced global `g_chuck_for_audio` pointer with `userData` parameter mechanism
  - ChucK instance passed directly to audio callback via `userData`
  - Added mutex protection for audio state (`g_audio_mutex`)
  - Eliminated dangling pointer risks

- **RAII resource management** for audio system:
  - Created `AudioContext` class with automatic cleanup
  - Destructor ensures cleanup on all paths (success/failure/exception)
  - Deleted copy/move constructors for single ownership semantics
  - Global audio context managed via `std::unique_ptr`
  - `start_audio()` now performs cleanup on initialization/start failures
  - `stop_audio()` and `shutdown_audio()` properly manage lifecycle

- **Test suite bug** caught by new validation:
  - Fixed `test_chuck_now` using wrong dtype (float64 -> float32)
  - Fixed `test_chuck_now` missing channel configuration
  - All 15 tests now pass

### Security

- Input validation prevents buffer overruns and segmentation faults
- Array dimension and size checks before native code access
- Initialization state checked before operations
- Thread-safe audio operations with mutex protection

### Technical Details

- Simplified `validate_audio_buffer()` using template parameters instead of runtime dtype checks
- Type safety enforced at compile-time via nanobind's typed ndarrays
- Writable vs read-only buffers enforced by nanobind template parameters
- Mutex: `std::mutex` for audio state protection
- Smart pointers: `std::unique_ptr<AudioContext>` for resource ownership

### Design Decisions

- **Single global audio context**: Only one ChucK instance can have real-time audio active at a time
  - This is **intentional and appropriate** - ChucK VM handles concurrency via shreds
  - Multiple audio streams should use multiple shreds within one ChucK instance
  - Running multiple ChucK instances is inefficient and unnecessary
  - Documented in `docs/ARCHITECTURE.md` with rationale and correct usage patterns

## [0.1.0]

### Added

#### Core Features

- Initial Python bindings for ChucK using nanobind
- Complete ChucK class wrapper with all core functionality:
  - Parameter configuration (sample rate, channels, VM settings)
  - Code compilation from strings with `compile_code()`
  - **File compilation** with `compile_file()` - Load and run `.ck` files
  - Audio processing with numpy array integration (synchronous)
  - Shred management and VM control
  - Time tracking and status queries

#### Real-Time Audio (RtAudio)

- **Asynchronous audio playback** using RtAudio (cross-platform):
  - `start_audio()` - Start real-time audio stream
  - `stop_audio()` - Stop audio stream
  - `shutdown_audio()` - Shutdown audio system
  - `audio_info()` - Get audio system information
- **Offline audio processing** with numpy array integration
- Platform support:
  - macOS: CoreAudio backend
  - Windows: DirectSound/WASAPI (prepared, not tested)
  - Linux: ALSA/JACK (prepared, not tested)

#### Plugin Support (Chugins)

- **Chugin loading and usage**:
  - `PARAM_CHUGIN_ENABLE` - Enable/disable chugin support
  - `PARAM_USER_CHUGINS` - Set chugin search paths
- Pre-built chugins included in `examples/chugins/`:
  - Effects: Bitcrusher, ABSaturator, FoldbackSaturator, etc.
  - Filters: Elliptic, FIR, etc.
  - Delays: ExpDelay, ConvRev, etc.
  - Utilities: AbletonLink, Binaural, AmbPan, etc.

#### Examples and Resources

- **ChucK example files** in `examples/`:
  - `examples/basic/` - Basic synthesis examples
  - `examples/effects/` - Audio effect demonstrations
  - `examples/stereo/` - Stereo processing examples
  - More specialized examples (convrev, deep, extend, etc.)
- All examples can be loaded with `compile_file()`

#### Testing

- Comprehensive test suite (15 tests):
  - Basic functionality tests (7 tests)
  - Real-time audio tests (2 tests)
  - File loading and chugin tests (6 tests)
- Test coverage:
  - Version detection and initialization
  - Code and file compilation
  - Audio processing (sync and async)
  - Parameter configuration
  - Chugin loading
  - Multiple concurrent shreds
  - Error handling

#### Build System and Documentation

- Support for all ChucK parameter constants:
  - Core parameters (PARAM_SAMPLE_RATE, PARAM_INPUT_CHANNELS, PARAM_OUTPUT_CHANNELS)
  - VM configuration (PARAM_VM_ADAPTIVE, PARAM_VM_HALT, etc.)
  - Path configuration (PARAM_WORKING_DIRECTORY, PARAM_CHUGIN_ENABLE, PARAM_USER_CHUGINS)
- Float32 audio buffer support with interleaved layout
- CMake-based build system with scikit-build-core
- RtAudio and chuck_audio.cpp integrated into extension module
- Chugin build system integration
- Makefile with build, test, and clean targets
- Complete API documentation in README.md with examples:
  - Real-time audio examples
  - Offline rendering examples
  - File loading examples
  - Chugin usage examples
  - Multiple shred examples

### Technical Details

- ChucK core version: 1.5.5.3-dev (chai)
- Audio sample format: float32 (SAMPLE type)
- Buffer layout: Interleaved (e.g., [L0, R0, L1, R1, ...])
- Default sample rate: 44100 Hz
- Build system: CMake 3.15+ with Xcode generator on macOS
- Real-time audio: RtAudio with CoreAudio backend on macOS

### Fixed

- Float32 vs float64 audio buffer compatibility
- ChucK VM time advancement synchronization
- C source file compilation in ChucK core library
- Extension module output directory configuration
- Lambda capture issues in audio callback (using static function instead)

### Notes

- Requires numpy for audio processing
- macOS support with CoreAudio/CoreMIDI frameworks
- ChucK code must explicitly advance time for continuous audio generation
- Real-time audio plays asynchronously in background thread
