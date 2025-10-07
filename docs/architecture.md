# Architecture Documentation

## Overview

pychuck is a Python wrapper for ChucK that uses nanobind to create efficient C++/Python bindings. The project follows a layered architecture with clear separation between the ChucK core library, the C++ binding layer, the Python package interface, and terminal user interfaces for interactive development.

## File Structure

```text
pychuck/
├── src/
│   ├── _pychuck.cpp              # C++ nanobind extension
│   ├── CMakeLists.txt            # Extension build configuration
│   └── pychuck/
│       ├── __init__.py           # Public Python API
│       ├── _pychuck.pyi          # Type stubs
│       ├── cli/
│       │   ├── main.py           # CLI argument parser & dispatcher
│       │   └── executor.py       # Non-interactive execution
│       └── tui/
│           ├── editor.py         # Multi-tab editor
│           ├── repl.py           # REPL implementation
│           ├── tui.py            # REPL main entry
│           ├── session.py        # Shred tracking & metadata
│           ├── project.py        # File versioning system
│           ├── commands.py       # REPL commands (@, :)
│           ├── chuck_lexer.py    # Pygments syntax highlighter
│           ├── parser.py         # ChucK code parsing
│           ├── paths.py          # ~/.pychuck/ management
│           └── common.py         # Shared UI components
├── thirdparty/
│   ├── chuck/                    # ChucK core (git submodule)
│   │   ├── core/                 # VM, compiler, UGens
│   │   ├── host/                 # Standalone ChucK + RtAudio
│   │   └── CMakeLists.txt
│   ├── chugins/                  # ChucK plugins (git submodule)
│   └── nanobind/                 # Python binding library (git submodule)
├── tests/                        # pytest test suite
│   ├── test_basic.py
│   ├── test_realtime_audio.py
│   ├── test_project_versioning.py
│   ├── test_chuck_lexer.py
│   └── ...
├── docs/
│   ├── dev/
│   │   └── architecture.md       # This file
│   └── pychuck_home.md           # ~/.pychuck/ documentation
├── examples/                     # ChucK example files
├── scripts/
│   ├── update.sh                 # Update ChucK core from upstream
│   └── lowercase_docs.py         # Normalize documentation filenames
├── pyproject.toml                # Python package configuration
├── CMakeLists.txt                # Root CMake configuration
├── Makefile                      # Convenience wrapper for CMake
├── CHANGELOG.md
└── README.md

User Data (~/.pychuck/):
├── history                       # REPL command history
├── snippets/                     # Reusable ChucK snippets
│   ├── sine.ck
│   ├── reverb.ck
│   └── ...
└── projects/                     # Versioned project files
    ├── myproject/
    │   ├── melody-1.ck
    │   ├── melody-1-1.ck
    │   ├── bass-2.ck
    │   └── ...
    └── liveset/
        └── ...
```

## System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Python Application                       │
│                  (or User via CLI Commands)                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                          │
│  - pychuck.cli.main: Command dispatcher                     │
│  - Subcommands: edit, repl, exec, version, info             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Terminal User Interfaces (TUI)                 │
│  - pychuck.tui.editor: Multi-tab editor (prompt_toolkit)    │
│  - pychuck.tui.repl: Interactive REPL (prompt_toolkit)      │
│  - pychuck.tui.session: Shred tracking & project versioning │
│  - pychuck.tui.commands: REPL commands (@snippet, :help)    │
│  - pychuck.tui.project: File versioning system              │
│  - pychuck.tui.chuck_lexer: Syntax highlighting (Pygments)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              pychuck Package (Python)                       │
│  - __init__.py: Public API, imports from _pychuck           │
│  - _pychuck.pyi: Type stubs for IDE/type checkers           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│        _pychuck Extension Module (C++ via nanobind)         │
│  - ChucK class bindings                                     │
│  - Audio callback infrastructure                            │
│  - Parameter management                                     │
│  - Error handling & validation                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  ChucK Core Library (C++)                   │
│  - Virtual Machine (chuck_vm.cpp)                           │
│  - Compiler (chuck_compile.cpp, chuck_emit.cpp)             │
│  - Type system (chuck_type.cpp)                             │
│  - Unit generators (ugen_*.cpp)                             │
│  - I/O systems (chuck_io.cpp, midiio_rtmidi.cpp)            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Platform Audio Layer (RtAudio)                │
│  - CoreAudio (macOS)                                        │
│  - WASAPI/DirectSound (Windows)                             │
│  - ALSA/JACK (Linux)                                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. CLI Layer (`src/pychuck/cli/`)

**Responsibilities:**

- Command-line interface and argument parsing
- Dispatching to appropriate subsystems
- Non-interactive ChucK execution

**Key Files:**

- `main.py`: Argument parser, command dispatcher
- `executor.py`: Execute ChucK files from command line

**Subcommands:**

- `edit`: Launch multi-tab editor with optional files and project versioning
- `repl`: Launch interactive REPL with smart Enter, sidebar, project support
- `exec`: Execute ChucK files headlessly with configurable audio parameters
- `version`: Display pychuck and ChucK versions
- `info`: Display ChucK VM information
- `tui`: Backward compatibility alias for `repl`

### 2. TUI Layer (`src/pychuck/tui/`)

**Responsibilities:**

- Terminal-based user interfaces using prompt_toolkit
- Interactive ChucK development environments
- Project versioning and session management
- Syntax highlighting and code completion

**Key Modules:**

#### Editor (`editor.py`)

- Multi-tab editor with Ctrl+N/W/PageUp/PageDown navigation
- File open dialog with tab completion (Ctrl+O)
- Integrated shreds table, help window, status bar
- Spork (Ctrl+R), replace (Ctrl+E), remove (Ctrl+X)
- ChucK syntax highlighting with pygments
- F1-F4 toggles for help/shreds/logs/status

#### REPL (`repl.py`, `tui.py`)

- Interactive command-line interface
- Smart Enter mode (auto-detects multiline ChucK code)
- Sidebar showing active shreds (toggleable with F2)
- REPL history with Up/Down arrows (~/.pychuck/history)
- Support for @snippet loading and :commands
- Clean shutdown handling (Ctrl+Q, Ctrl+D)

#### Session Management (`session.py`)

- Tracks active shreds with metadata (ID, name, source, spork time)
- Project-aware execution tracking
- Shred table generation for editor/REPL display
- Elapsed time calculation

#### Project Versioning (`project.py`)

- Automatic file versioning: `file.ck → file-1.ck → file-1-1.ck`
- Saves on spork (shred ID suffix) and replace (replace counter suffix)
- Timeline tracking with modification times
- Stored in `~/.pychuck/projects/<name>/`

#### Commands (`commands.py`)

- REPL command execution (@snippet, :help, :shreds)
- Snippet loading from `~/.pychuck/snippets/`
- Tab completion for snippets and files

#### Syntax Highlighting (`chuck_lexer.py`)

- Custom Pygments lexer for ChucK
- Keywords, operators, time durations, UGens, built-ins
- Used by editor and REPL

#### Path Management (`paths.py`)

- `~/.pychuck/` home directory management
- Subdirectories: history, snippets, projects, sessions, logs
- Helper functions: `get_pychuck_home()`, `get_snippets_dir()`, etc.

#### Common Utilities (`common.py`)

- Shared UI components (shreds table, status bar, help window)
- App state management across editor/REPL
- Lexer and syntax highlighting integration

### 3. Python Package Layer (`src/pychuck/`)

**Responsibilities:**

- Public API exposure
- Clean Python interface
- Re-export of C++ extension symbols

**Key Files:**

- `__init__.py`: Main entry point, imports and exposes all public symbols
- `_pychuck.pyi`: Type stub file for static type checking

**Design Pattern:**

- Private module pattern: `_pychuck` (C++ extension) wrapped by `pychuck` (Python package)
- Follows Python convention for native extensions

### 4. C++ Binding Layer (`src/_pychuck.cpp`)

**Responsibilities:**

- Expose ChucK C++ API to Python via nanobind
- Type conversion between Python and C++
- Input validation and error handling
- Audio lifecycle management
- Memory safety

**Key Components:**

#### ChucK Class Binding

```cpp
nb::class_<ChucK>(m, "ChucK")
    .def(nb::init<>())
    .def("init", &ChucK::init)
    .def("compile_code", ...)
    .def("compile_file", ...)
    .def("run", ...)
    // ... parameter methods, status methods, etc.
```

Exposes core ChucK functionality with Python-friendly signatures.

#### Audio Callback Infrastructure

```cpp
static void audio_callback_func(SAMPLE* input, SAMPLE* output,
                                t_CKUINT numFrames, t_CKUINT numInChans,
                                t_CKUINT numOutChans, void* userData);
```

- Called by RtAudio on audio thread
- `userData` carries ChucK instance pointer
- Invokes `chuck->run()` for sample generation

#### AudioContext RAII Wrapper

```cpp
class AudioContext {
    bool initialize(...);
    bool start();
    void stop();
    void cleanup(t_CKUINT msWait = 0);
    ~AudioContext();  // Automatic cleanup
};
```

- Manages audio system lifecycle
- Ensures cleanup on all paths (success/failure/exception)
- Prevents resource leaks

#### Input Validation

```cpp
static void validate_audio_buffer(const nb::ndarray<>& array,
                                  const char* name,
                                  size_t expected_size,
                                  bool check_writable = false);
```

- Validates numpy arrays before passing to ChucK
- Checks: dimensions, size, dtype (float32), writability
- Throws descriptive exceptions on validation failure

### 5. ChucK Core Library (`thirdparty/chuck/core/`)

**Responsibilities:**

- ChucK language implementation
- Virtual machine execution
- Audio synthesis and processing
- MIDI/OSC/HID I/O

**Key Subsystems:**

#### Virtual Machine

- Bytecode execution (`chuck_vm.cpp`)
- Shred (thread) management
- Time advancement
- Sample-accurate scheduling

#### Compiler

- Lexing/parsing (`chuck_scan.cpp`, `chuck_parse.cpp`)
- Type checking (`chuck_type.cpp`)
- Code emission (`chuck_emit.cpp`)
- AST representation (`chuck_absyn.cpp`)

#### Audio Engine

- Unit generator graph (`chuck_ugen.cpp`)
- Built-in UGens (`ugen_osc.cpp`, `ugen_filter.cpp`, `ugen_stk.cpp`)
- DAC/ADC abstraction

#### Chugin System

- Dynamic plugin loading (`chuck_dl.cpp`)
- Plugin API
- User-defined UGens and classes

### 6. Audio Backend (RtAudio)

**Responsibilities:**

- Cross-platform audio I/O
- Device enumeration
- Buffer management
- Asynchronous callback handling

**Platform Support:**

- **macOS**: CoreAudio (primary)
- **Windows**: WASAPI, DirectSound
- **Linux**: ALSA, JACK, PulseAudio

## User Workflows

### Command-Line Usage

#### Interactive Editor

```bash
# Basic editor
python -m pychuck edit

# Open files in tabs
python -m pychuck edit melody.ck bass.ck drums.ck

# Enable project versioning
python -m pychuck edit --project myproject

# Start with audio on
python -m pychuck edit --start-audio
```

**User Flow:**

1. User runs `python -m pychuck edit`
2. CLI dispatcher (`cli.main`) invokes `cmd_edit(args)`
3. `tui.editor.main()` launches prompt_toolkit application
4. User edits ChucK code with syntax highlighting
5. User presses Ctrl+R to spork code → creates shred
6. Editor updates shreds table (F2) with new shred
7. If project enabled, file saved to `~/.pychuck/projects/<name>/file-1.ck`
8. User presses Ctrl+E to replace → replaces shred, saves `file-1-1.ck`

#### Interactive REPL

```bash
# Basic REPL
python -m pychuck repl

# With project versioning
python -m pychuck repl --project liveset

# Load files on startup
python -m pychuck repl melody.ck bass.ck

# Configure behavior
python -m pychuck repl --start-audio --no-smart-enter --no-sidebar
```

**User Flow:**

1. User runs `python -m pychuck repl`
2. CLI dispatcher invokes `cmd_repl(args)`
3. `tui.tui.main()` launches REPL with prompt_toolkit
4. User types ChucK code (smart Enter detects multiline)
5. User presses Esc+Enter to execute
6. REPL executor compiles and runs code
7. Sidebar (F2) shows active shreds with elapsed time
8. User types `@snippet` to load from `~/.pychuck/snippets/`
9. Tab completion works for snippets and commands
10. User presses Ctrl+Q to exit (clean shutdown with audio stop)

#### Non-Interactive Execution

```bash
# Execute files
python -m pychuck exec file1.ck file2.ck

# Custom audio configuration
python -m pychuck exec --srate 48000 --channels 1 file.ck

# Silent execution (testing)
python -m pychuck exec --silent --duration 10 file.ck
```

**User Flow:**

1. User runs `python -m pychuck exec`
2. CLI dispatcher invokes `cmd_exec(args)`
3. `cli.executor.execute_files()` creates ChucK instance
4. Files compiled sequentially
5. Audio runs for specified duration or until Ctrl+C
6. Clean shutdown

### Library Usage (Python API)

```python
import pychuck
import numpy as np

# Create and initialize
chuck = pychuck.ChucK()
chuck.set_param(44100, 2, 0)
chuck.init()

# Compile code
success, ids = chuck.compile_code("SinOsc s => dac; 440 => s.freq; ...")

# Real-time audio
pychuck.start_audio(chuck)
time.sleep(5)
pychuck.stop_audio()

# Offline processing
output = np.zeros(44100, dtype=np.float32)
chuck.run(None, output, 44100)
```

**Data Flow:**

1. Python creates `ChucK()` instance → nanobind constructs C++ object
2. `chuck.compile_code()` → C++ binding validates, calls ChucK compiler
3. ChucK compiler parses, type-checks, emits bytecode, creates UGen graph
4. `start_audio()` → Creates AudioContext, initializes RtAudio with callback
5. Audio thread calls `audio_callback_func()` → extracts ChucK from userData
6. Callback invokes `chuck->run()` → VM processes samples → returns to RtAudio

## Data Flow

### Offline Audio Processing (Synchronous)

```text
Python → chuck.run(input, output, num_frames)
    ↓
Validation (dimensions, dtype, size)
    ↓
ChucK::run(input_ptr, output_ptr, num_frames)
    ↓
VM executes shreds for num_frames samples
    ↓
UGen graph processes samples
    ↓
Output written to buffer
    ↓
Return to Python (output array modified in-place)
```

### Real-Time Audio (Asynchronous)

```text
Python → start_audio(chuck, sample_rate, channels, ...)
    ↓
AudioContext::initialize(&chuck, ...) with userData
    ↓
RtAudio::initialize(callback=audio_callback_func, userData=&chuck)
    ↓
AudioContext::start()
    ↓
RtAudio::start() → spawns audio thread
    ↓
[Audio thread runs independently]
    ↓
On each audio callback:
    RtAudio → audio_callback_func(input, output, frames, userData)
        ↓
    ChucK* chuck = (ChucK*)userData
        ↓
    chuck->run(input, output, frames)
        ↓
    VM processes samples
        ↓
    Output filled, return to RtAudio

[Main thread continues]
    ↓
Python → stop_audio() → AudioContext::stop()
    ↓
Python → shutdown_audio() → AudioContext::cleanup()
```

### Project Versioning Flow

```text
User presses Ctrl+R in editor with --project enabled
    ↓
Editor calls chuck.compile_code(content)
    ↓
ChucK compiles and returns (success, [shred_id])
    ↓
session.add_shred(shred_id, filename, content, type='file')
    ↓
If project enabled: project.save_on_spork(filename, content, shred_id)
    ↓
Save to ~/.pychuck/projects/<name>/<base>-<shred_id>.ck
    e.g., melody.ck → melody-1.ck (first spork)

User presses Ctrl+E to replace shred
    ↓
Editor calls chuck.replace_shred(shred_id, content)
    ↓
session.update_shred(shred_id, content)
    ↓
If project enabled: project.save_on_replace(shred_id, content)
    ↓
Increment replace counter for this shred
Save to ~/.pychuck/projects/<name>/<base>-<shred_id>-<replace_num>.ck
    e.g., melody-1-1.ck (first replace of shred 1)
         melody-1-2.ck (second replace of shred 1)

Result: Complete timeline of all code versions
    melody-1.ck      (original spork, shred 1)
    melody-1-1.ck    (first replace)
    melody-1-2.ck    (second replace)
    bass-2.ck        (spork, shred 2)
    bass-2-1.ck      (replace)
```

## Current Limitations

### 1. Single Global Audio Context

**Location:** `src/_pychuck.cpp:99`

```cpp
static std::unique_ptr<AudioContext> g_audio_context;
```

**Design Decision:**

- Only one ChucK instance can have real-time audio active at a time
- Multiple ChucK instances can exist, but only one can use `start_audio()`
- Subsequent `start_audio()` calls replace the previous audio context

**Rationale:**
This constraint is **acceptable and appropriate** for pychuck because:

1. **ChucK is inherently multithreaded**: The ChucK VM already handles multiple concurrent audio streams internally via shreds (concurrent execution threads)
2. **Single audio device**: Most systems use one audio output device at a time
3. **Resource efficiency**: Running multiple ChucK VMs would waste system resources
4. **Typical use case**: Users should spawn multiple shreds within one ChucK instance, not multiple instances

**Correct Usage Pattern:**

```python
# Good: Multiple concurrent sounds in ONE ChucK instance
chuck = pychuck.ChucK()
chuck.init()

# Spawn multiple shreds (ChucK handles concurrency)
chuck.compile_code("SinOsc s => dac; 440 => s.freq; ...")  # Shred 1
chuck.compile_code("SinOsc s => dac; 550 => s.freq; ...")  # Shred 2
chuck.compile_code("SinOsc s => dac; 660 => s.freq; ...")  # Shred 3

pychuck.start_audio(chuck)  # All shreds play simultaneously
```

**Why Not Multiple Instances:**

```python
# Inefficient: Multiple ChucK instances (NOT recommended)
chuck1 = pychuck.ChucK()
chuck2 = pychuck.ChucK()  # Unnecessary - use shreds instead!
```

**Technical Implementation:**
RtAudio's callback mechanism requires a function pointer (not a method pointer). The current approach:

1. Uses a static callback function `audio_callback_func()`
2. Receives ChucK instance via `userData` parameter
3. Stores AudioContext globally for lifecycle management

**Conclusion:**
This is a **design choice, not a limitation**. Multiple audio streams should be handled by spawning multiple shreds within a single ChucK instance, leveraging ChucK's built-in concurrency model.

### 2. Audio Thread Safety

**Concern:** ChucK instance accessed from both main thread and audio callback thread

**Current Protection:**

- Mutex protection on `start_audio()`, `stop_audio()`, `shutdown_audio()`
- ChucK VM is designed for single-threaded use
- Audio callback only calls `chuck->run()` (designed for this)

**Remaining Risks:**

- No protection if user calls other ChucK methods during audio playback
- Deleting ChucK instance while audio running would crash
- Parameter changes during playback not thread-safe

**Mitigation:**

- Document: "Do not modify ChucK instance during real-time audio playback"
- Consider: Keep reference count of ChucK instance while audio active
- Consider: Add `is_audio_active()` check to mutable operations

### 3. Buffer Type Assumptions

**Location:** `src/_pychuck.cpp:52-57`

```cpp
if (array.dtype() != nb::dtype<SAMPLE>()) {
    throw std::invalid_argument("dtype must be float32");
}
```

**Assumption:** SAMPLE is float32

**Limitation:**

- Hardcoded to float32 (typical ChucK configuration)
- No support for float64 or other sample formats
- Runtime validation but compile-time assumption

**Impact:**

- Users must use `np.float32` arrays
- Silent audio if wrong dtype passed (caught by validation now)
- No automatic conversion

**Future Improvement:**

- Add dtype conversion layer
- Support multiple sample formats
- Make SAMPLE type configurable at build time

### 4. Error Message Propagation

**Current State:**

- Validation errors throw Python exceptions ✓
- ChucK compilation errors return bool (success/failure)
- ChucK VM errors printed to stderr
- No access to detailed error messages from ChucK

**Limitation:**

```python
success, ids = chuck.compile_code("invalid syntax!")
# success == False, but WHY? Error only in stderr
```

**Missing:**

- ChucK compiler error messages not captured
- VM errors not propagated as exceptions
- Line numbers, error context not available

**Future Improvement:**

- Redirect ChucK error output
- Parse error messages
- Return structured error information
- Add `get_last_error()` method

### 5. Platform-Specific Audio Behavior

**Current Support:**

- macOS: CoreAudio (well-tested)
- Windows: WASAPI/DirectSound (via RtAudio, untested)
- Linux: ALSA/JACK (via RtAudio, untested)

**Limitations:**

- CI only tests macOS
- Windows/Linux audio paths not validated
- Platform-specific quirks not documented
- Device enumeration not exposed

**Missing Features:**

- Audio device listing
- Device selection by name
- Device capabilities query
- Latency measurement/reporting

## Memory Management

### Python/C++ Boundary

**ChucK Instance Ownership:**

- Created in Python: `chuck = pychuck.ChucK()`
- Owned by Python (reference counted)
- C++ binding uses nanobind's automatic lifetime management
- Destructor called when Python reference count reaches zero

**Audio Buffers:**

- Numpy arrays passed by reference
- No copies made (zero-copy operation)
- Validation ensures buffers remain valid during `run()` call
- Python must keep buffer alive during processing

**String Handling:**

- Automatic conversion via `nanobind/stl/string.h`
- Temporary std::string created for C++ calls
- No manual memory management needed

### ChucK Internal Memory

**Shreds:**

- Created by `compile_code()` / `compile_file()`
- Managed by ChucK VM
- Removed by `remove_all_shreds()` or VM cleanup

**UGen Graph:**

- Built during compilation
- Reference counted internally by ChucK
- Cleaned up when shreds removed

**Audio Buffers:**

- Internal ChucK buffers separate from Python buffers
- `run()` copies between internal and Python buffers
- Size determined by channel count and frame count

## Build System Architecture

### Two-Level Build

**1. CMake (Low-level):**

- Builds ChucK core library (`chuck_lib`)
- Builds ChucK standalone executable (`chuck`)
- Builds chugins (plugins)
- Builds Python extension (`_pychuck`)
- Handles platform-specific compilation

**2. scikit-build-core (Python packaging):**

- Wraps CMake for Python ecosystem
- Handles `pip install` / `pip install -e`
- Creates Python wheels
- Manages installation

### Build Targets

```sh
CMakeLists.txt (root)
├── thirdparty/chuck/CMakeLists.txt
│   ├── chuck_lib (static library)
│   └── chuck (executable)
├── thirdparty/chugins/CMakeLists.txt
│   └── [individual chugin libraries]
└── src/CMakeLists.txt
    └── _pychuck (Python extension)
```

### Dependencies

**Build-time:**

- CMake 3.15+
- C++17 compiler
- Python 3.8+ (headers)
- nanobind (submodule)

**Runtime:**

- Python 3.8+
- numpy
- Platform audio frameworks (CoreAudio/WASAPI/ALSA)

**Optional:**

- bison/flex (macOS parser generation)
- ccache (build acceleration)

## Design Patterns

### 1. Private Module Pattern

```python
# _pychuck: C++ extension (private)
# pychuck: Python package (public)
from ._pychuck import ChucK, version, ...
```

**Benefits:**

- Clean API boundary
- Python-side enhancements possible
- Implementation hiding

### 2. RAII (Resource Acquisition Is Initialization)

```cpp
class AudioContext {
    ~AudioContext() { cleanup(); }
};
```

**Benefits:**

- Automatic cleanup
- Exception-safe
- No leaked resources

### 3. Validation Wrapper Pattern

```cpp
.def("run", [](ChucK& self, ...) {
    validate_inputs();
    return self.run(...);
})
```

**Benefits:**

- Input validation at boundary
- Descriptive error messages
- Protection of C++ layer

### 4. Smart Pointer Ownership

```cpp
static std::unique_ptr<AudioContext> g_audio_context;
```

**Benefits:**

- Clear ownership semantics
- Automatic deletion
- Move-only semantics

## Thread Safety

### Thread Model

**Main Thread:**

- Python code execution
- ChucK compilation
- Parameter setting
- Shred management

**Audio Thread (if real-time audio active):**

- RtAudio callback
- `chuck->run()` calls
- Sample generation
- High-priority, real-time scheduling

### Synchronization

**Protected Operations:**

- `start_audio()` - mutex protected
- `stop_audio()` - mutex protected
- `shutdown_audio()` - mutex protected

**Unprotected (Unsafe during audio playback):**

- `compile_code()` / `compile_file()`
- `remove_all_shreds()`
- Parameter modifications
- ChucK instance deletion

**Thread-Safe by Design:**

- `chuck->run()` - designed for audio thread
- Internal ChucK VM (single-threaded model)

### Race Conditions

**Known Safe:**

- Starting/stopping audio (mutex)
- Multiple `run()` calls from same thread (offline mode)

**Known Unsafe:**

- Modifying ChucK while audio callback active
- Deleting ChucK instance during audio playback
- Simultaneous compilation and audio processing

**Mitigation:**

- Document usage constraints
- Consider adding audio-active flag checks
- Future: Add fine-grained locking in ChucK VM

## Performance Characteristics

### Binding Overhead

**nanobind Efficiency:**

- ~10x lower overhead vs pybind11
- ~5x smaller binaries vs pybind11
- ~4x faster compilation vs pybind11

**Zero-Copy Audio:**

- Numpy arrays passed by pointer
- No memory allocation in hot path
- Direct memory access in `run()`

### Compilation Time

**ChucK Compilation:**

- Dependent on code complexity
- Parser, type-checker, code generator
- Creates VM bytecode + UGen graph

**C++ Compilation:**

- ChucK core: ~30-60s (depends on platform)
- nanobind binding: ~5-10s
- Total clean build: ~1-2 minutes

**Incremental Builds:**

- ccache reduces recompilation
- scikit-build-core caches CMake configuration

### Runtime Performance

**Offline Processing:**

- Overhead: Validation (~microseconds) + ChucK VM execution
- Throughput: Depends on UGen graph complexity
- Typical: 10-100x faster than real-time (simple patches)

**Real-Time Audio:**

- Latency: Determined by buffer size (default 512 samples = ~11.6ms @ 44.1kHz)
- CPU: Depends on ChucK code complexity
- Thread priority: High (real-time audio thread)

## Security Considerations

### Input Validation

**Validated:**

- Numpy array dimensions, sizes, dtypes
- Parameter value ranges (positive integers)
- Initialization state checks
- File path non-empty checks

**Not Validated:**

- File system access (ChucK can read arbitrary files)
- Network access (OSC can bind to arbitrary ports)
- System command execution (not exposed but ChucK core has shell access)
- Memory limits (no guard against excessive allocations)

### ChucK Code Execution

**Security Model:**

- ChucK code runs with same privileges as Python process
- No sandboxing
- Can access file system via ChucK I/O
- Can open network sockets via OSC
- Infinite loops possible (can hang process)

**Recommendations:**

- Do not execute untrusted ChucK code
- Validate user-provided ChucK code paths
- Consider resource limits for production use

## Recent Improvements (v0.1.1)

### TUI Bug Fixes

1. **Shreds Table Display** (Fixed)
   - Changed from displaying source code to parent folder + filename
   - Added elapsed time calculation in seconds (from VM samples)
   - Widened table from 60 to 78 characters
   - Applied fixes to both editor and REPL
   - Location: `tui/common.py`, `tui/repl.py`

2. **REPL Exit Crash** (Fixed)
   - Segmentation fault when pressing Ctrl+Q with audio running
   - Root cause: Incorrect cleanup order
   - Solution: Remove shreds → stop_audio() → shutdown_audio()
   - Added proper error handling for each cleanup step
   - Location: `tui/repl.py:cleanup()`

3. **Editor File Open Dialog** (Fixed)
   - Ctrl+O causing crashes due to nested event loops
   - Solution: FloatContainer + Buffer + CompletionsMenu
   - Shell-like tab completion with `insert_common_part=True`
   - Custom key bindings to intercept Tab before focus navigation
   - Location: `tui/editor.py:_show_open_file_dialog()`

4. **Editor Tab Switching** (Fixed)
   - Files not appearing after opening with Ctrl+O
   - Solution: Wrapped editor content in DynamicContainer
   - Gets current tab dynamically based on `current_tab_index`
   - Location: `tui/editor.py:create_layout()`

5. **Case-Insensitive Filesystem Handling** (Fixed)
   - `lowercase_docs.py` incorrectly deleting uppercase files
   - Solution: Use `path.samefile()` to distinguish same file from duplicates
   - Location: `scripts/lowercase_docs.py`

### Documentation Updates

1. **README.md** - Separated highlights into "Library Features" and "User Interface"
2. **CHANGELOG.md** - Documented all bug fixes and improvements
3. **docs/pychuck_home.md** - Updated paths from `cli/` to `tui/`, moved projects to current features
4. **docs/dev/architecture.md** - Comprehensive architecture documentation (this file)

## Future Improvements

### Architecture Enhancements

1. **Per-Instance Audio Contexts**
   - Eliminate global audio context
   - Allow multiple concurrent audio streams
   - Use `nb::supplement<>` for instance data

2. **Error Message Capture**
   - Redirect ChucK stderr
   - Parse and structure error messages
   - Return detailed compilation errors

3. **Thread-Safe API**
   - Fine-grained locking
   - Message passing to audio thread
   - Safe parameter updates during playback

4. **Device Management**
   - Enumerate audio devices
   - Select device by name
   - Query device capabilities

### Feature Additions

1. **Python Callbacks**
   - Event callbacks (shred start/stop)
   - Custom UGen implementations in Python
   - Real-time parameter control callbacks

2. **Advanced Audio**
   - Multi-channel routing
   - Audio file I/O integration
   - JACK transport sync

3. **Debugging Support**
   - VM state introspection
   - Breakpoints in ChucK code
   - Performance profiling

4. **TUI Enhancements**
   - Session save/restore in REPL
   - Snippet editor/manager
   - Visual shred timeline browser
   - File browser for opening multiple files

## References

- [ChucK Language](https://chuck.stanford.edu/)
- [nanobind Documentation](https://nanobind.readthedocs.io/)
- [RtAudio](https://www.music.mcgill.ca/~gary/rtaudio/)
- [scikit-build-core](https://scikit-build-core.readthedocs.io/)
