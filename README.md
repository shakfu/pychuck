# numchuck

Python bindings for the [ChucK](https://chuck.stanford.edu) audio programming language using [nanobind](https://github.com/wjakob/nanobind).

The numchuck library provides interactive control over ChucK, enabling live coding workflows, bidirectional Python/ChucK communication, and comprehensive VM introspection—all while maintaining the existing real-time and offline audio capabilities.

## Overview

`numchuck` is a high-performance Python wrapper for ChucK that provides:

### Library

* **Python Programmatic Access to ChucK API** — Load, compile, and concurrently execute `.ck` files and ChucK code into audio processing or generated shreds. Manage the VM using python code: configure parameters, monitor timing, and control shred lifecycles.

* **Flexible Execution** — Choose between real-time audio playback and recording using asynchronous RtAudio or offline input from and rendering to `numpy` arrays.

* **Advanced Audio Processing** — Harness ChucK's complete synthesis, filtering, and DSP capabilities.

* **Live Coding** — Hot-swap code, replace active shreds, and inspect VM state in real time.

* **Plugin Support** — Extend functionality with ChucK *chugins* for additional instruments and effects.

* **Dynamic Interaction** - Bidirectional communication between ChucK and Python through global variables, event triggers, and callbacks.

### User Interface

* **Multi-Tab Editor** — Full-screen ChucK editor with syntax highlighting; use F5 to spork and F6 to replace.

* **Interactive REPL** — Terminal-style interface supporting ChucK commands and code completion.

* **Automatic Versioning** — Keeps track of live coding sessions (`file.ck → file-1.ck → file-1-1.ck`).

* **Command-Line Mode** — Run ChucK files directly from the terminal, with support for duration and silent modes.

## Installation

### Install from pypi

```sh
pip install numchuck
```

or

```sh
uv add numchuck
```

### Build from source

```sh
# Clone the repository
git clone https://github.com/shakfu/numchuck.git
cd numchuck

# Build the extension
make build

# Run tests
make test
```

## Quick Start

### Command-Line Interface

numchuck provides three modes of operation:

#### 1. Multi-Tab Editor (for livecoding)

```sh
# Launch the editor
numchuck edit

# Open specific files in tabs
numchuck edit bass.ck melody.ck

# Enable project versioning
numchuck edit --project mymusic

# Start with audio enabled
numchuck edit --start-audio --project mymusic
```

**Editor Features:**

* Multi-tab editing with ChucK syntax highlighting
* F5 or Ctrl-R to spork (compile and run current buffer)
* F6 to replace running shred with current buffer
* Ctrl-O to open files with interactive dialog (Tab for path completion)
* Ctrl-S to save files
* Ctrl-T for new tab, Ctrl-W to close tab
* Ctrl-N/Ctrl-P (or Ctrl-PageDown/PageUp) to navigate tabs
* Tab names show shred IDs after sporking (e.g., `bass-1.ck`)
* Project versioning: file.ck → file-1.ck → file-1-1.ck
* F1/F2/F3 for help/shreds/log windows
* Ctrl-Q to exit

#### 2. Interactive REPL

```sh
# Launch the REPL
numchuck repl

# Load files on startup
numchuck repl bass.ck melody.ck

# Enable project versioning
numchuck repl --project mymusic

# Start with audio enabled
numchuck repl --start-audio

# Disable smart Enter mode
numchuck repl --no-smart-enter

# Hide sidebar (can toggle with F2)
numchuck repl --no-sidebar
```

**REPL Commands:**

* `add <file>` or `+ <file>` - Spork a file
* `remove <id>` or `- <id>` - Remove a shred
* `remove all` or `- all` - Remove all shreds
* `abort.shred <id>` or `abort <id>` - Abort a shred (ChucK-native)
* `replace <id> <file>` or `= <id> <file>` - Replace shred with file
* `status` or `^` - Show VM status
* `time` or `.` - Show ChucK time
* `exit` or `quit` - Exit the REPL
* `@<name>` - Load a snippet (e.g., `@sine`, `@drum`)
* `watch <file>` - Auto-reload file on changes
* `record start/stop/save <name>` - Record session
* `playback <name>` - Replay recorded session
* Type `help` or press F1 for full command reference

#### 3. Command-Line Execution

```sh
# Execute ChucK files from command line
numchuck run myfile.ck

# Run multiple files
numchuck run bass.ck melody.ck

# Run for 10 seconds then exit
numchuck run myfile.ck --duration 10

# Silent mode (no audio)
numchuck run myfile.ck --silent

# Custom sample rate
numchuck run myfile.ck --srate 48000
```

#### 4. Snippet Management

```sh
# List all available snippets
numchuck snippets list

# Show snippet content
numchuck snippets show sine

# Show snippets directory path
numchuck snippets path
```

#### 5. File Watch Mode

```sh
# Watch files and auto-reload on changes
numchuck watch bass.ck melody.ck
```

#### 6. WAV Export

```sh
# Export ChucK files to WAV
numchuck export output.wav --files sine.ck --duration 10
```

#### 7. Web IDE (Browser-Based)

```sh
# Launch browser-based ChucK IDE
numchuck web

# Specify port
numchuck web --port 9000

# Load files on startup with audio enabled
numchuck web --start-audio bass.ck melody.ck

# Don't auto-open browser
numchuck web --no-browser
```

**Web IDE Features:**

* Browser-based code editor with syntax highlighting
* Multi-file tabs with local storage persistence (files saved automatically)
* Examples dropdown with built-in ChucK examples (click to load)
* Globals panel with auto-discovery of ChucK global variables
  - Interactive sliders for int/float globals with real-time control
  - Real-time sync via WebSocket (updates pushed, not polled)
  - Event buttons to signal/broadcast global events
* Shred management panel:
  - View all running shreds with elapsed time
  - Replace shred with current editor code
  - Preview shred source code
  - Remove individual shreds
* Real-time audio level meters:
  - RMS and peak levels for left/right channels
  - Visual meter bars updated in real-time
  - Calculated in C++ audio callback for accuracy
* Theme toggle (dark/light mode) with system preference detection
* Real-time console output via WebSocket
* Audio start/stop controls
* Keyboard shortcuts:
  - Ctrl+Enter: Spork code
  - Ctrl+S: Save current tab
  - Ctrl+N: New tab

**REST API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get VM status, shreds, audio state |
| `/api/compile` | POST | Compile and spork code |
| `/api/shred/:id` | DELETE | Remove a shred |
| `/api/shred/:id/replace` | POST | Replace shred with new code |
| `/api/shred/:id/code` | GET | Get shred source code |
| `/api/globals` | GET | List all global variables with types |
| `/api/clear` | POST | Clear all shreds |
| `/api/audio/start` | POST | Start real-time audio |
| `/api/audio/stop` | POST | Stop real-time audio |
| `/ws` | WebSocket | Real-time console and status updates |

#### 8. Version and Info

```sh
# Show version
numchuck version

# Show ChucK and numchuck info
numchuck info
```

**Interface Features:**

* **Full-screen layout**: Professional terminal UI with multiple display areas
* **Live topbar**: Minimal display showing shred IDs `[1] [2] [3]`
* **Shreds table**: Detailed shred information table (F2) with ID, name (folder/file), and elapsed time since spork
* **Error display bar**: Red error bar shows command errors without disrupting layout
* **Help window**: Built-in command reference (toggle with F1)
* **Log window**: Scrollable ChucK VM output capture (toggle with Ctrl+L)
* **Mouse support**: Scroll through log output with mouse wheel
* **Scrollable input**: Main input area with scrollbar for long code

**Editing Features:**

* **Smart Enter mode**: Enter submits commands immediately, but allows multiline ChucK code editing
* **ChucK syntax highlighting**: Full Pygments lexer for ChucK language with color themes
* **ChucK code completion**: Tab completion for keywords, types, UGens, and standard library
* **Intelligent code detection**: Automatically compiles multiline ChucK code
* **Tab completion**: Commands, `.ck` files, and ChucK language elements
* **Command history**: Persistent history with Ctrl+R search
* **Colored prompt**: `[=>]` matches ChucK logo styling

**Common Keyboard Shortcuts (Editor & REPL):**

* `F1` - Toggle help window
* `F2` - Toggle shreds table (detailed view with ID, folder/filename, elapsed time)
* `F3` - Toggle log window (ChucK VM output)
* `Ctrl+Q` - Exit application
* `Tab` - Command and ChucK code completion
* `Up/Down` - Navigate command history

### User Directory (`.numchuck`)

numchuck uses a `.numchuck` directory for user configuration, snippets, and customization.

**Search Order:**
1. Local: `./.numchuck` (current working directory)
2. Global: `~/.numchuck` (home directory)

Local configuration takes precedence over global. This allows project-specific settings.

**Directory Structure:**
```
.numchuck/
  snippets/     # Code snippets loaded with @<name>
  themes/       # Color theme configurations (.toml)
  keybindings/  # Custom key binding configurations (.toml)
  examples/     # Example ChucK files
  chugins/      # User chugins (.chug plugins)
  config.toml   # Main configuration file
```

**Template Directory:**

The `_numchuck/` directory in the repository contains a template with examples:

```
_numchuck/
  snippets/
    sine.ck     # Simple sine wave oscillator
    fm.ck       # FM synthesis with modulation
    drum.ck     # Basic drum machine pattern
    noise.ck    # Noise generator with filter
    delay.ck    # Delay effect with feedback
  themes/
    dark.toml   # Dark theme colors
    light.toml  # Light theme colors
  keybindings/
    default.toml  # Default key bindings
  examples/
    hello.ck    # Hello world sine wave
    arpeggio.ck # Simple arpeggiator
    lfo.ck      # LFO modulation example
  chugins/
    README.md   # Chugins installation guide
```

Copy to your home directory to use globally:
```bash
cp -r _numchuck ~/.numchuck
```

Or copy to a project directory for project-specific settings:
```bash
cp -r _numchuck .numchuck
```

### Snippets

Snippets are reusable ChucK code files that can be loaded with `@<name>` in the REPL.

**Usage in REPL:**
```
[=>] @sine        # Loads snippets/sine.ck
[=>] @drum        # Loads snippets/drum.ck
[=>] @<TAB>       # Tab completion for available snippets
```

Snippets are searched in `.numchuck/snippets/` (local first, then global).

### Project Versioning

When using `--project <name>`, numchuck automatically versions your files as you livecode:

```sh
~/.numchuck/projects/mymusic/
  bass.ck           # Original file
  bass-1.ck         # After first spork (shred ID 1)
  bass-1-1.ck       # After first replace of shred 1
  bass-1-2.ck       # After second replace of shred 1
  melody-2.ck       # Second file sporked (shred ID 2)
  melody-2-1.ck     # After replace of shred 2
```

This creates a complete history of your livecoding session, making it easy to:

* Review your creative process
* Recover previous versions
* Replay session timeline
* Share reproducible livecoding performances

### Offline Rendering API

numchuck provides a simple API for rendering ChucK code to audio files or numpy arrays:

```python
from numchuck import render, render_file, to_wav

# Render code to numpy array
audio = render("SinOsc s => dac; 1::second => now;", duration=1.0)
print(audio.shape)  # (88200,) - 1 second of stereo audio

# Render files to numpy array
audio = render_file(["bass.ck", "melody.ck"], duration=5.0)

# Export directly to WAV file
to_wav("output.wav", code="SinOsc s => dac; 2::second => now;", duration=2.0)
to_wav("output.wav", files=["sine.ck"], duration=10.0, sample_rate=48000)
```

#### Rendering Functions

| Function | Description |
|----------|-------------|
| `render(code, duration, sample_rate, channels, dtype)` | Render ChucK code string to numpy array |
| `render_file(files, duration, sample_rate, channels, dtype)` | Render ChucK files to numpy array |
| `to_wav(output, code, files, duration, ...)` | Export to WAV file (provide either `code` or `files`) |

All functions support:
- `duration` - Seconds to render (default: 10.0)
- `sample_rate` - Sample rate in Hz (default: 44100)
- `channels` - Output channels (default: 2)
- `dtype` - Output type: `np.float32` or `np.int16` (default: float32)

### High-Level API (Recommended)

The `Chuck` class provides a Pythonic interface with properties and simplified methods:

```python
from numchuck import Chuck

# Create with parameters (auto-initializes)
chuck = Chuck(sample_rate=48000, output_channels=2)

# Properties instead of get_param/set_param
print(chuck.sample_rate)   # 48000
print(chuck.version)       # "1.5.5.3-dev (chai)"

# Compile and run
success, shreds = chuck.compile("SinOsc s => dac; 1::second => now;")
output = chuck.run(44100)  # Returns numpy array

# Shred management
print(chuck.shreds)        # [1]
chuck.remove_shred(1)
chuck.clear()

# Synchronous global variables
chuck.compile("global int tempo;")
chuck.run(100)
chuck.set_int("tempo", 120)
val = chuck.get_int("tempo")  # 120

# Events
chuck.signal_event("trigger")
chuck.on_event("response", my_callback)

# Access low-level API when needed
chuck.raw.set_param(...)
```

#### Context Manager Support

The `Chuck` class supports the context manager protocol for automatic cleanup:

```python
from numchuck import Chuck

# Automatic cleanup on exit (calls close())
with Chuck() as chuck:
    chuck.compile("SinOsc s => dac; 1::second => now;")
    output = chuck.run(44100)
# chuck.close() is called automatically, even on exceptions
```

#### Shred Handle Objects

Use `Shred` objects for more intuitive shred management:

```python
from numchuck import Chuck

chuck = Chuck()

# spork() returns a Shred object
shred = chuck.spork("SinOsc s => dac; 1::second => now;")
print(shred.id)          # 1
print(shred.is_running)  # True

# Methods for shred control
shred.replace("TriOsc t => dac; 1::second => now;")  # Hot-swap code
shred.remove()           # Remove the shred

# Load from file
shred = chuck.spork_file("melody.ck")

# Get detailed info
print(shred.info)  # {'id': 1, 'name': '...', 'is_running': True, ...}
```

#### Typed Global Variable Proxies

Property-based access to global variables:

```python
from numchuck import Chuck

chuck = Chuck()
chuck.compile("global int tempo; global float gain; global string mode;")
chuck.run(100)

# Create typed proxies
tempo = chuck.global_int("tempo")
gain = chuck.global_float("gain")
mode = chuck.global_string("mode")

# Property-based access
tempo.value = 120        # Instead of chuck.set_int("tempo", 120)
print(tempo.value)       # 120

gain.value = 0.8
mode.value = "minor"

# Also supports method-style access
tempo.set(140)
print(tempo.get())       # 140
```

#### Async/Await API

For integration with asyncio applications:

```python
import asyncio
from numchuck import Chuck

async def main():
    chuck = Chuck()
    chuck.compile("global int counter; 42 => counter;")
    chuck.run(100)

    # Async global variable access
    value = await chuck.get_int_awaitable("counter")
    print(value)  # 42

    # Also available for float and string
    # await chuck.get_float_awaitable("gain")
    # await chuck.get_string_awaitable("mode")

    # Proxies also support async
    counter = chuck.global_int("counter")
    value = await counter.get_async()

asyncio.run(main())
```

### Low-Level API

For fine-grained control, use the low-level API via `numchuck._numchuck`:

```python
from numchuck._numchuck import ChucK, start_audio, stop_audio
```

#### Real-Time Audio

```python
from numchuck._numchuck import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS
)
import time

# Create and configure ChucK
chuck = ChucK()
chuck.set_param(PARAM_SAMPLE_RATE, 44100)
chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile ChucK code
chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    while(true) { 1::samp => now; }
''')

# Start real-time audio playback
start_audio(chuck)
time.sleep(2)  # Play for 2 seconds
stop_audio()
shutdown_audio()
```

#### Offline Rendering

```python
from numchuck._numchuck import ChucK, PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS
import numpy as np

# Create ChucK instance
chuck = ChucK()
chuck.set_param(PARAM_SAMPLE_RATE, 44100)
chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile code
chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    while(true) { 1::samp => now; }
''')

# Render to numpy array
frames = 512
output = np.zeros(frames * 2, dtype=np.float32)
chuck.run(np.zeros(0, dtype=np.float32), output, frames)
```

## API Reference

### High-Level API (`numchuck.Chuck`)

The `Chuck` class provides a Pythonic wrapper with properties and simplified methods.

```python
from numchuck import Chuck
```

#### Constructor

```python
Chuck(
    sample_rate: int = 44100,
    input_channels: int = 2,
    output_channels: int = 2,
    working_directory: str = "",
    chugin_enable: bool = True,
    user_chugins: list[str] | None = None,
    vm_adaptive: bool = False,
    vm_halt: bool = False,
    auto_depend: bool = False,
    deprecate_level: int = 1,
    dump_instructions: bool = False,
    otf_enable: bool = False,
    otf_port: int = 8888,
    tty_color: bool = False,
    tty_width_hint: int = 80,
    auto_init: bool = True,
)
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `sample_rate` | `int` | Audio sample rate in Hz |
| `input_channels` | `int` | Number of input channels |
| `output_channels` | `int` | Number of output channels |
| `working_directory` | `str` | Working directory for file operations |
| `version` | `str` | ChucK version string (read-only) |
| `chugin_enable` | `bool` | Whether chugin loading is enabled |
| `user_chugins` | `list[str]` | List of user chugin paths |
| `vm_adaptive` | `bool` | Whether adaptive VM timing is enabled |
| `vm_halt` | `bool` | Whether VM halts when no shreds remain |
| `auto_depend` | `bool` | Whether automatic dependency resolution is enabled |
| `deprecate_level` | `int` | Deprecation warning level (0=none, 1=warn, 2=error) |
| `dump_instructions` | `bool` | Whether VM instruction dumping is enabled |
| `otf_enable` | `bool` | Whether on-the-fly programming is enabled |
| `otf_port` | `int` | Port for on-the-fly programming |
| `tty_color` | `bool` | Whether colored terminal output is enabled |
| `tty_width_hint` | `int` | Terminal width hint for formatting |
| `compiler_highlight_on_error` | `bool` | Syntax highlighting in error messages |
| `is_realtime_audio_hint` | `bool` | Hint for real-time audio mode |
| `otf_print_warnings` | `bool` | Whether OTF compiler warnings are printed |
| `shreds` | `list[int]` | List of all active shred IDs |
| `raw` | `ChucK` | Access to underlying low-level ChucK instance |

#### Core Methods

* **`init() -> bool`** - Initialize ChucK (called automatically if `auto_init=True`)
* **`close() -> None`** - Shutdown ChucK instance (important on Windows)
* **`__enter__() -> Chuck`** - Context manager entry (returns self)
* **`__exit__(...) -> None`** - Context manager exit (calls close())
* **`compile(code, args="", count=1, immediate=False) -> tuple[bool, list[int]]`** - Compile ChucK code
* **`compile_file(path, args="", count=1, immediate=False) -> tuple[bool, list[int]]`** - Compile from file
* **`run(num_frames, *, output=None, input=None, reuse=False) -> np.ndarray`** - Run VM and return output audio
  * No args: allocates new buffer each call
  * `output=buf`: uses provided buffer (zero allocation)
  * `input=buf`: uses provided input buffer
  * `reuse=True`: uses internal buffer (zero GC without manual management)
* **`advance(num_frames) -> None`** - Advance VM time without returning audio (for callbacks/events)
* **`spork(code, args="") -> Shred`** - Compile code and return Shred handle
* **`spork_file(path, args="") -> Shred`** - Compile file and return Shred handle

#### Shred Management

* **`remove_shred(shred_id) -> None`** - Remove a shred by ID
* **`replace_shred(shred_id, code, args="") -> int`** - Replace running shred with new code, returns new shred ID
* **`shred_info(shred_id) -> dict | None`** - Get shred information
* **`clear()`** - Remove all shreds from VM
* **`reset_id()`** - Reset shred ID counter

#### Global Variables

* **`set_int(name, value)`** - Set global int
* **`get_int(name, run_frames=256) -> int`** - Get global int (synchronous)
* **`set_float(name, value)`** - Set global float
* **`get_float(name, run_frames=256) -> float`** - Get global float (synchronous)
* **`set_string(name, value)`** - Set global string
* **`get_string(name, run_frames=256) -> str`** - Get global string (synchronous)
* **`get_int_async(name, callback)`** - Get global int via callback
* **`get_float_async(name, callback)`** - Get global float via callback
* **`get_string_async(name, callback)`** - Get global string via callback
* **`get_int_awaitable(name, run_frames=256) -> Awaitable[int]`** - Get global int (async/await)
* **`get_float_awaitable(name, run_frames=256) -> Awaitable[float]`** - Get global float (async/await)
* **`get_string_awaitable(name, run_frames=256) -> Awaitable[str]`** - Get global string (async/await)
* **`global_int(name) -> GlobalInt`** - Create typed int proxy
* **`global_float(name) -> GlobalFloat`** - Create typed float proxy
* **`global_string(name) -> GlobalString`** - Create typed string proxy

#### Events

* **`signal_event(name) -> None`** - Signal event (wakes one shred)
* **`broadcast_event(name) -> None`** - Broadcast event (wakes all shreds)
* **`on_event(name, callback, listen_forever=True) -> int`** - Register event callback, returns callback ID
* **`stop_listening_for_event(name, callback_id) -> None`** - Stop listening for event

#### Console Output

* **`set_stdout_callback(callback)`** - Capture ChucK stdout (chout)
* **`set_stderr_callback(callback)`** - Capture ChucK stderr (cherr)

---

### Low-Level API (`numchuck._numchuck.ChucK`)

The low-level API provides direct access to all ChucK functionality with explicit parameter management.

```python
from numchuck._numchuck import ChucK
```

#### Initialization Methods

* **`__init__()`** - Create a new ChucK instance
* **`init() -> bool`** - Initialize ChucK with current parameters
* **`start() -> bool`** - Explicitly start ChucK VM (called implicitly by `run()` if needed)

#### Parameter Configuration

* **`set_param(name: str, value: int) -> int`** - Set integer parameter
* **`set_param_float(name: str, value: float) -> int`** - Set float parameter
* **`set_param_string(name: str, value: str) -> int`** - Set string parameter
* **`set_param_string_list(name: str, value: list[str]) -> int`** - Set string list parameter
* **`get_param_int(name: str) -> int`** - Get integer parameter
* **`get_param_float(name: str) -> float`** - Get float parameter
* **`get_param_string(name: str) -> str`** - Get string parameter
* **`get_param_string_list(name: str) -> list[str]`** - Get string list parameter

#### Compilation Methods

* **`compile_code(code: str, args: str = "", count: int = 1, immediate: bool = False, filepath: str = "") -> tuple[bool, list[int]]`**
  * Compile ChucK code from string
  * Returns: `(success, shred_ids)`
  * Parameters:
    * `code`: ChucK code to compile
    * `args`: Additional arguments (separated by ':')
    * `count`: Number of shred instances to spork
    * `immediate`: If True, schedule immediately; if False, queue for next time step
    * `filepath`: Optional filepath for path-related operations

* **`compile_file(path: str, args: str = "", count: int = 1, immediate: bool = False) -> tuple[bool, list[int]]`**
  * Compile ChucK code from file
  * Returns: `(success, shred_ids)`

#### Audio Processing

* **`run(input: np.ndarray, output: np.ndarray, num_frames: int)`**
  * Process audio for specified number of frames (synchronous/offline)
  * `input`: Input buffer (1D numpy array, dtype=np.float32)
    * Size must be `num_frames * input_channels`
  * `output`: Output buffer (1D numpy array, dtype=np.float32, C-contiguous)
    * Size must be `num_frames * output_channels`
  * `num_frames`: Number of audio frames to process

#### Real-Time Audio (RtAudio)

* **`start_audio(chuck: ChucK, sample_rate: int = 44100, num_dac_channels: int = 2, num_adc_channels: int = 0, dac_device: int = 0, adc_device: int = 0, buffer_size: int = 512, num_buffers: int = 8) -> bool`**
  * Start real-time audio playback using RtAudio
  * Audio plays asynchronously in the background
  * Returns: True if successful

* **`stop_audio() -> bool`**
  * Stop real-time audio playback
  * Returns: True if successful

* **`shutdown_audio(msWait: int = 0)`**
  * Shutdown audio system completely
  * `msWait`: Milliseconds to wait before shutdown

* **`audio_info() -> dict`**
  * Get current audio system information
  * Returns dict with keys: `sample_rate`, `num_channels_out`, `num_channels_in`, `buffer_size`

#### Global Variable Management

* **`set_global_int(name: str, value: int)`** - Set a global int variable
* **`set_global_float(name: str, value: float)`** - Set a global float variable
* **`set_global_string(name: str, value: str)`** - Set a global string variable
* **`get_global_int(name: str, callback: Callable[[int], None])`** - Get a global int (async via callback)
* **`get_global_float(name: str, callback: Callable[[float], None])`** - Get a global float (async via callback)
* **`get_global_string(name: str, callback: Callable[[str], None])`** - Get a global string (async via callback)
* **`set_global_int_array(name: str, values: list[int])`** - Set a global int array
* **`set_global_float_array(name: str, values: list[float])`** - Set a global float array
* **`set_global_int_array_value(name: str, index: int, value: int)`** - Set array element by index
* **`set_global_float_array_value(name: str, index: int, value: float)`** - Set array element by index
* **`set_global_associative_int_array_value(name: str, key: str, value: int)`** - Set map value by key
* **`set_global_associative_float_array_value(name: str, key: str, value: float)`** - Set map value by key
* **`get_global_int_array(name: str, callback: Callable[[list[int]], None])`** - Get int array (async)
* **`get_global_float_array(name: str, callback: Callable[[list[float]], None])`** - Get float array (async)
* **`get_all_globals() -> list[tuple[str, str]]`** - Get list of all globals as (type, name) pairs

#### Global Event Management

* **`signal_global_event(name: str)`** - Signal a global event (wakes one waiting shred)
* **`broadcast_global_event(name: str)`** - Broadcast a global event (wakes all waiting shreds)
* **`listen_for_global_event(name: str, callback: Callable[[], None], listen_forever: bool = True) -> int`** - Listen for event, returns listener ID
* **`stop_listening_for_global_event(name: str, callback_id: int)`** - Stop listening using listener ID

#### Shred Management

* **`remove_shred(shred_id: int)`** - Remove a shred by ID
* **`remove_all_shreds()`** - Remove all running shreds from VM
* **`get_all_shred_ids() -> list[int]`** - Get IDs of all running shreds
* **`get_ready_shred_ids() -> list[int]`** - Get IDs of ready (not blocked) shreds
* **`get_blocked_shred_ids() -> list[int]`** - Get IDs of blocked shreds
* **`get_last_shred_id() -> int`** - Get ID of last sporked shred
* **`get_next_shred_id() -> int`** - Get what the next shred ID will be
* **`get_shred_info(shred_id: int) -> dict`** - Get shred info (id, name, is_running, is_done)

#### VM Control

* **`clear_vm()`** - Clear the VM (remove all shreds)
* **`clear_globals()`** - Clear global variables without clearing the VM
* **`reset_shred_id()`** - Reset the shred ID counter
* **`replace_shred(shred_id: int, code: str, args: str = "") -> int`** - Replace running shred with new code

#### Status and Utility

* **`is_init() -> bool`** - Check if ChucK is initialized
* **`vm_running() -> bool`** - Check if VM is running
* **`now() -> float`** - Get current ChucK time in samples

#### Console Output Control

* **`set_chout_callback(callback: Callable[[str], None]) -> bool`** - Capture ChucK console output
* **`set_cherr_callback(callback: Callable[[str], None]) -> bool`** - Capture ChucK error output
* **`toggle_global_color_textoutput(onOff: bool)`** - Enable/disable color output
* **`probe_chugins()`** - Print info on all loaded chugins

#### Static Methods

* **`version() -> str`** - Get ChucK version string
* **`int_size() -> int`** - Get ChucK integer size in bits
* **`num_vms() -> int`** - Get number of active ChucK VMs
* **`set_log_level(level: int)`** - Set global log level
* **`get_log_level() -> int`** - Get global log level
* **`poop()`** - ChucK poop compatibility
* **`set_stdout_callback(callback: Callable[[str], None]) -> bool`** - Set global stdout callback (static)
* **`set_stderr_callback(callback: Callable[[str], None]) -> bool`** - Set global stderr callback (static)
* **`global_cleanup()`** - Global cleanup for all ChucK instances

### Parameter Constants

#### Core Parameters

* `PARAM_VERSION` - ChucK version
* `PARAM_SAMPLE_RATE` - Sample rate (default: 44100)
* `PARAM_INPUT_CHANNELS` - Number of input channels
* `PARAM_OUTPUT_CHANNELS` - Number of output channels

#### VM Configuration

* `PARAM_VM_ADAPTIVE` - Adaptive VM mode
* `PARAM_VM_HALT` - VM halt on errors
* `PARAM_OTF_ENABLE` - On-the-fly programming enable
* `PARAM_OTF_PORT` - On-the-fly programming port
* `PARAM_DUMP_INSTRUCTIONS` - Dump VM instructions
* `PARAM_AUTO_DEPEND` - Auto dependency resolution
* `PARAM_DEPRECATE_LEVEL` - Deprecation warning level

#### Paths

* `PARAM_WORKING_DIRECTORY` - Working directory path
* `PARAM_CHUGIN_ENABLE` - Enable chugins (plugins)
* `PARAM_USER_CHUGINS` - User chugin paths
* `PARAM_IMPORT_PATH_SYSTEM` - System import search paths
* `PARAM_IMPORT_PATH_PACKAGES` - Package import search paths
* `PARAM_IMPORT_PATH_USER` - User import search paths

#### Display & Debugging

* `PARAM_OTF_PRINT_WARNINGS` - Print on-the-fly compiler warnings
* `PARAM_IS_REALTIME_AUDIO_HINT` - Hint for real-time audio mode
* `PARAM_COMPILER_HIGHLIGHT_ON_ERROR` - Syntax highlighting in error messages
* `PARAM_TTY_COLOR` - Enable color output in terminal
* `PARAM_TTY_WIDTH_HINT` - Terminal width hint for formatting

### Rendering API (`numchuck.render`)

* **`render(code, duration=10.0, sample_rate=44100, channels=2, dtype=np.float32) -> np.ndarray`** - Render ChucK code to numpy array
* **`render_file(files, duration=10.0, sample_rate=44100, channels=2, dtype=np.float32) -> np.ndarray`** - Render ChucK files to numpy array
* **`to_wav(output, code=None, files=None, duration=10.0, sample_rate=44100, channels=2) -> Path`** - Export to WAV file
* **`RenderError`** - Exception raised for rendering failures

### File Watcher (`numchuck.watcher`)

```python
from numchuck.watcher import FileWatcher, WatchedFile
```

* **`FileWatcher(chuck, session, on_reload=None, on_error=None)`** - Watch files for changes and auto-reload
* **`watch_file(filepath, shred_id=None) -> bool`** - Start watching a file
* **`unwatch_file(filepath) -> bool`** - Stop watching a file
* **`start() -> None`** - Start the file watcher
* **`stop() -> None`** - Stop the file watcher
* **`WatchedFile`** - Dataclass for watched file info

### Web Server (`numchuck.web`)

```python
from numchuck.web import WebChuckServer, WEB_AVAILABLE
```

* **`WEB_AVAILABLE`** - Boolean indicating if web module is available
* **`WebChuckServer(chuck, port=8080, static_dir=None)`** - Browser-based ChucK IDE server
  * `start() -> None` - Start the web server in background thread
  * `stop() -> None` - Stop the web server
  * `broadcast(msg: str) -> None` - Broadcast message to all WebSocket clients
  * `port` - Server port (read-only)
  * `url` - Server URL (e.g., "http://localhost:8080")
  * `is_running` - Check if server is running
  * `client_count` - Number of connected WebSocket clients

```python
# Example usage
from numchuck import Chuck
from numchuck.web import WebChuckServer

chuck = Chuck()
with WebChuckServer(chuck, port=8080) as server:
    print(f"IDE running at {server.url}")
    input("Press Enter to stop...")
```

### MIDI Support (`numchuck.midi`)

```python
from numchuck.midi import MIDIMapping, MIDIMappings, generate_midi_listener_code
```

* **`MIDIMapping(channel, cc_number, global_name, min_value=0.0, max_value=1.0)`** - Map MIDI CC to ChucK global
* **`MIDIMappings`** - Collection of MIDI mappings with `add()`, `remove()`, `get()`, `to_dict()` methods
* **`MIDILearnState`** - State machine for MIDI learn mode
* **`generate_midi_listener_code(mappings) -> str`** - Generate ChucK code for MIDI control
* **`generate_midi_monitor_code() -> str`** - Generate MIDI monitor code

### OSC Support (`numchuck.osc`)

```python
from numchuck.osc import OSCServer, OSCClient, generate_osc_listener_code
```

* **`OSCServer(port=9000)`** - UDP server for receiving OSC messages
* **`OSCClient(host, port)`** - UDP client for sending OSC messages
* **`OSCController(executor, port=9000)`** - Map OSC addresses to REPL actions
* **`OSCHandler`** - Dataclass for OSC address handlers
* **`generate_osc_listener_code(address, port, global_type, global_name) -> str`** - Generate ChucK OSC listener
* **`generate_osc_sender_code(host, port, address) -> str`** - Generate ChucK OSC sender

### Waveform Display (`numchuck.tui.waveform`)

```python
from numchuck.tui.waveform import samples_to_waveform, WaveformBuffer
```

* **`samples_to_waveform(samples, width=80, height=8, use_unicode=True) -> str`** - Convert audio to waveform string
* **`WaveformBuffer(size, channels=2)`** - Circular buffer for real-time waveform display
* **`format_waveform_bar(level, width=40, use_unicode=True) -> str`** - Format a level meter bar
* **`format_stereo_meters(left, right, width=20) -> str`** - Format stereo level meters
* **`calculate_rms(samples) -> float`** - Calculate RMS level
* **`calculate_peak(samples) -> float`** - Calculate peak level
* **`db_to_linear(db) -> float`** / **`linear_to_db(linear) -> float`** - Decibel conversions

### Session Recording (`numchuck.recorder`)

```python
from numchuck.recorder import SessionRecorder, SessionPlayer, list_recordings
```

* **`SessionRecorder()`** - Record REPL sessions with timestamps
  * `start(name) -> None` - Start recording
  * `stop() -> RecordedSession` - Stop and return session
  * `record_action(action_type, content) -> None` - Record an action
* **`SessionPlayer(session)`** - Playback recorded sessions
  * `start(speed=1.0) -> None` - Start playback
  * `tick() -> bool` - Advance playback, returns True if still playing
* **`RecordedAction(timestamp, action_type, content)`** - A recorded action
* **`RecordedSession(name, actions)`** - A complete recorded session
* **`get_recording_path(name) -> Path`** - Get path to recording file
* **`list_recordings() -> list[str]`** - List saved recordings

### ChucK Language Support (`numchuck.lang`)

The `lang` subpackage provides ChucK language constants and syntax highlighting:

```python
from numchuck.lang import ChuckLexer, KEYWORDS, TYPES, UGENS, REPL_COMMANDS

# Check if an identifier is a ChucK keyword
from numchuck.lang import is_keyword, is_ugen, get_category
is_keyword("while")  # True
is_ugen("SinOsc")    # True
get_category("LPF")  # "ugen"
```

**Constants:**
- `KEYWORDS` - ChucK keywords (if, while, class, fun, etc.)
- `TYPES` - ChucK types (int, float, time, dur, etc.)
- `OPERATORS` - ChucK operators (=>, +, -, etc.)
- `TIME_UNITS` - Time units (samp, ms, second, etc.)
- `UGENS` - Unit generators (SinOsc, LPF, ADSR, etc.)
- `STD_CLASSES` - Standard library classes (Std, Math, Machine, etc.)
- `REPL_COMMANDS` - REPL command prefixes (+, -, ~, etc.)
- `ALL_IDENTIFIERS` - All ChucK identifiers combined

**Lexer:**
- `ChuckLexer` - Pygments lexer for ChucK syntax highlighting

### Module Functions

* **`version() -> str`** - Get ChucK version (convenience function)

## Important Notes

### Audio Buffer Types

**ChucK uses `float` (32-bit) for audio samples by default.** Always use `np.float32` for numpy arrays:

```python
# Correct
output_buffer = np.zeros(num_frames * channels, dtype=np.float32)

# Incorrect - will produce silent output
output_buffer = np.zeros(num_frames * channels, dtype=np.float64)
```

### Buffer Layout

Audio buffers are **interleaved**:

* For stereo output: `[L0, R0, L1, R1, L2, R2, ...]`
* Buffer size = `num_frames * num_channels`

### Time Advancement

ChucK code must advance time to generate audio:

```python
# Good - infinite loop advances time
code = '''
SinOsc s => dac;
440 => s.freq;
while(true) { 1::samp => now; }
'''

# Bad - shred exits immediately, no audio
code = '''
SinOsc s => dac;
440 => s.freq;
'''
```

## Examples

### Real-Time Audio Playback

```python
import numchuck
import time

# Create and initialize ChucK
chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile ChucK code
chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while(true) { 1::samp => now; }
''')

# Start real-time audio (plays asynchronously)
numchuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2)

# Audio plays in background
time.sleep(3)  # Play for 3 seconds

# Stop audio
numchuck.stop_audio()
numchuck.shutdown_audio()
```

### Offline Audio Processing

```python
import numchuck
import numpy as np

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while(true) { 1::samp => now; }
''')

# Process audio synchronously
frames = 512
output = np.zeros(frames * 2, dtype=np.float32)
chuck.run(np.zeros(0, dtype=np.float32), output, frames)

# output now contains audio samples
```

### Parameter Control

```python
# Get ChucK version
print(f"ChucK version: {numchuck.version()}")

# Configure VM
chuck.set_param(numchuck.PARAM_VM_HALT, 0)
chuck.set_param_string(numchuck.PARAM_WORKING_DIRECTORY, "/path/to/files")

# Check status
print(f"Initialized: {chuck.is_init()}")
print(f"Current time: {chuck.now()} samples")
```

### Multiple Shreds

```python
# Compile the same code 3 times
success, ids = chuck.compile_code(code, count=3)
print(f"Spawned shreds: {ids}")  # [1, 2, 3]

# Remove all shreds
chuck.remove_all_shreds()
```

### Loading ChucK Files

```python
import numchuck

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile from file
success, shred_ids = chuck.compile_file("examples/basic/blit2.ck")

# Start playback
numchuck.start_audio(chuck)
import time; time.sleep(2)
numchuck.stop_audio()
numchuck.shutdown_audio()
```

### Using Chugins (Plugins)

```python
import numchuck

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)

# Enable chugins and set search path
chuck.set_param(numchuck.PARAM_CHUGIN_ENABLE, 1)
chuck.set_param_string(numchuck.PARAM_USER_CHUGINS, "./examples/chugins")

chuck.init()

# Use a chugin in code
code = '''
SinOsc s => Bitcrusher bc => dac;
440 => s.freq;
8 => bc.bits;
while(true) { 1::samp => now; }
'''
chuck.compile_code(code)
```

### Global Variables (Python/ChucK Communication)

```python
import numchuck
import numpy as np

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
chuck.start()

# Define global variables in ChucK
chuck.compile_code('''
    global int tempo;
    global float frequency;
    global string mode;

    SinOsc s => dac;

    while(true) {
        frequency => s.freq;
        1::samp => now;
    }
''')

# Helper to run audio cycles (VM processes messages during audio)
def run_cycles(count=5):
    buf_in = np.zeros(512 * 2, dtype=np.float32)
    buf_out = np.zeros(512 * 2, dtype=np.float32)
    for _ in range(count):
        chuck.run(buf_in, buf_out, 512)

# Set globals from Python
chuck.set_global_int("tempo", 120)
chuck.set_global_float("frequency", 440.0)
chuck.set_global_string("mode", "major")
run_cycles()

# Get globals via callback
result = []
chuck.get_global_float("frequency", lambda val: result.append(val))
run_cycles()
print(f"Current frequency: {result[0]} Hz")

# List all globals
globals_list = chuck.get_all_globals()
print(f"Globals: {globals_list}")
```

### Global Events (Event-Driven Communication)

```python
import numchuck
import numpy as np

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
chuck.start()

# ChucK code with global events
chuck.compile_code('''
    global Event trigger;
    global Event response;
    global int noteValue;

    SinOsc s => dac;

    fun void player() {
        while(true) {
            trigger => now;
            Std.mtof(noteValue) => s.freq;
            100::ms => now;
            response.broadcast();
        }
    }

    spork ~ player();
''')

def run_cycles(count=5):
    buf_in = np.zeros(512 * 2, dtype=np.float32)
    buf_out = np.zeros(512 * 2, dtype=np.float32)
    for _ in range(count):
        chuck.run(buf_in, buf_out, 512)

# Listen for response from ChucK
response_count = []
def on_response():
    response_count.append(1)
    print(f"Response received! Total: {len(response_count)}")

listener_id = chuck.listen_for_global_event("response", on_response, listen_forever=True)

# Trigger notes from Python
for note in [60, 64, 67, 72]:  # C major chord
    chuck.set_global_int("noteValue", note)
    chuck.signal_global_event("trigger")
    run_cycles(10)

# Stop listening
chuck.stop_listening_for_global_event("response", listener_id)
```

### Shred Management & Introspection

```python
import numchuck
import numpy as np

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
chuck.start()

# Spork multiple shreds
code = "while(true) { 100::ms => now; }"
success1, ids1 = chuck.compile_code(code)
success2, ids2 = chuck.compile_code(code)
success3, ids3 = chuck.compile_code(code)

# Introspect running shreds
all_ids = chuck.get_all_shred_ids()
print(f"Running shreds: {all_ids}")

for shred_id in all_ids:
    info = chuck.get_shred_info(shred_id)
    print(f"Shred {info['id']}: {info['name']}, running={info['is_running']}")

# Remove specific shred
chuck.remove_shred(ids1[0])
print(f"After removal: {chuck.get_all_shred_ids()}")

# Get next shred ID
next_id = chuck.get_next_shred_id()
print(f"Next shred ID will be: {next_id}")

# Clear all
chuck.clear_vm()
print(f"After clear_vm: {chuck.get_all_shred_ids()}")
```

### Live Coding with replace_shred()

```python
import numchuck
import numpy as np

chuck = numchuck.ChucK()
chuck.set_param(numchuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(numchuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(numchuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
chuck.start()

# Start with one sound
code_v1 = '''
SinOsc s => dac;
440 => s.freq;
while(true) { 1::samp => now; }
'''
success, ids = chuck.compile_code(code_v1)
original_id = ids[0]

# ... play for a while ...

# Hot-swap to different sound
code_v2 = '''
TriOsc t => dac;
330 => t.freq;
0.5 => t.gain;
while(true) { 1::samp => now; }
'''
new_id = chuck.replace_shred(original_id, code_v2)
print(f"Replaced shred {original_id} with {new_id}")
```

### Capturing ChucK Console Output

```python
import numchuck

chuck = numchuck.ChucK()
chuck.init()

# Capture chout (console output)
output_log = []
chuck.set_chout_callback(lambda msg: output_log.append(msg))

# Capture cherr (error output)
error_log = []
chuck.set_cherr_callback(lambda msg: error_log.append(msg))

# Run code that prints
chuck.compile_code('''
    <<< "Hello from ChucK!" >>>;
    <<< "Value:", 42 >>>;
''')

# Check captured output
print("ChucK output:", output_log)
```

## Configuration

numchuck supports user configuration via `~/.numchuck/config.toml`:

```python
from numchuck import Config, load_config, save_config, get_config

# Load config (from ~/.numchuck/config.toml or defaults)
config = get_config()

# Access settings
print(config.audio.sample_rate)   # 44100
print(config.repl.smart_enter)    # True

# Modify and save
config.audio.sample_rate = 48000
config.repl.show_sidebar = False
save_config(config)
```

Example `~/.numchuck/config.toml`:

```toml
[audio]
sample_rate = 48000
output_channels = 2
input_channels = 0
buffer_size = 512

[repl]
smart_enter = true
show_sidebar = true
start_audio = false
max_log_lines = 100

[editor]
start_audio = false
tab_size = 4
wrap_lines = false

[paths]
working_directory = "~/chuck"
chugin_paths = ["~/.chuck/chugins"]

[chuck]
chugin_enable = true
vm_adaptive = false
deprecate_level = 1
```

### Configuration Classes

| Class | Description |
|-------|-------------|
| `Config` | Complete configuration (contains all sections) |
| `AudioConfig` | Audio settings (sample_rate, channels, buffer_size, etc.) |
| `REPLConfig` | REPL settings (smart_enter, show_sidebar, max_log_lines) |
| `EditorConfig` | Editor settings (start_audio, tab_size, wrap_lines) |
| `PathsConfig` | Path settings (working_directory, chugin_paths) |
| `ChuckConfig` | ChucK VM settings (chugin_enable, vm_adaptive, etc.) |

## Requirements

* Python 3.9+
* CMake 3.15+
* C++17 compatible compiler
* macOS: Xcode with CoreAudio/CoreMIDI frameworks
* numpy (for audio processing)

## Development

```sh
# Build
make build

# Run tests
make test

# Clean build artifacts
make clean
```

## What's with the name?

numchuck initially started off as `pychuck`. When I posted in the Chuck Discord about an earlier iteration of the project, [David Braun](https://github.com/dbraun) suggested the name NumChuck, which fits much better with the project’s use of [NumPy](https://numpy.org).

Nonetheless, the inertia of the initial name held until I went to publish the project on PyPI and discovered that there was already a [pychuck](https://pypi.org/project/pychuck/) project whose purpose is to implement (rather than wrap) the Chuck language in Python—-which is, in hindsight, a much stronger claim to the name.

Luckily, the name numchuck was available, allowing this project to narrowly avoid an unnecessary naming showdown.

## License

numchuck is licensed under the GNU General Public License v3.0

## Credits

* [ChucK](https://chuck.stanford.edu): Ge Wang, Perry Cook, and the ChucK team
* [nanobind](https://github.com/wjakob/nanobind): Wenzel Jakob and contributors
* [David Braun](https://github.com/dbraun): For suggesting the name, numchuck!
* [claude-code](https://github.com/anthropics/claude-code): Anthropic
