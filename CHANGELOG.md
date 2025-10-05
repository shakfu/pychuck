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
