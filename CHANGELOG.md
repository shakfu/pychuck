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
