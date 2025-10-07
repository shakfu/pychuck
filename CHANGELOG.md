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

- **ChucK Language Module** (`src/pychuck/chuck_lang.py`):
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

### Technical Details

- All 76 tests pass
- ChucK lexer tests verify correct categorization of language elements
- Completion system preserves REPL command priority
- `chuck_lang` module provides forward compatibility for language specification updates

## [0.1.3]

### Added

- **ChucK Pygments Lexer** (`src/pychuck/cli/chuck_lexer.py`):
  - Complete syntax highlighting for ChucK language
  - Recognizes ChucK operators (`=>`, `+=>`, `@=>`, etc.)
  - Time duration literals (`100::ms`, `1::second`, etc.)
  - 80+ built-in UGens (SinOsc, LPF, ADSR, JCRev, dac, etc.)
  - Keywords, types, standard library (Math, Std, Machine)
  - Comments, strings, numbers (int, float, hex)
  - Integrated into REPL for syntax-highlighted input
  - 16 comprehensive tests in `tests/test_chuck_lexer.py`
  - Documentation: `docs/CHUCK_LEXER.md`

- **Centralized Path Management** (`src/pychuck/cli/paths.py`):
  - `get_pychuck_home()` - Returns `~/.pychuck`
  - `get_snippets_dir()` - Returns `~/.pychuck/snippets`
  - `get_history_file()` - Returns `~/.pychuck/history`
  - `get_sessions_dir()`, `get_logs_dir()`, `get_projects_dir()`, `get_config_file()` - Future directories
  - `ensure_pychuck_directories()` - Creates directory structure
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
  - `docs/PYCHUCK_HOME.md` - Complete guide to `~/.pychuck/` directory structure
  - `docs/CHUCK_LEXER.md` - ChucK lexer usage and implementation guide

### Changed

- **Directory Structure Migration**:
  - `~/.chuck_repl_history` → `~/.pychuck/history`
  - `~/.chuck_snippets/` → `~/.pychuck/snippets/`
  - REPL now creates full `~/.pychuck/` directory structure on startup
  - Updated all code to use new path utilities from `paths.py`
  - Updated `.gitignore` to ignore `~/.pychuck/` instead of individual files

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
  - `python -m pychuck tui` now launches vanilla REPL directly
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
4. **Unified directory structure** - All user data in `~/.pychuck/`
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

- **Type stub file (`_pychuck.pyi`)** updated with all new methods:
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

- **Type stub file (`_pychuck.pyi`)** completely rewritten to match actual implementation
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
  - Fixed `test_chuck_now` using wrong dtype (float64 → float32)
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
