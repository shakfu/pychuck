# pychuck

Python bindings for the [ChucK](https://chuck.stanford.edu) audio programming language using [nanobind](https://github.com/wjakob/nanobind).

The pychuck library now complete interactive control over ChucK, enabling sophisticated live coding workflows, bidirectional Python/ChucK communication, and comprehensive VM introspection—all while maintaining the existing real-time and offline audio capabilities.

## Highlights

- **Real-Time Audio** - Play ChucK code through your speakers with asynchronous RtAudio playback
- **File Support** - Load and run `.ck` files directly
- **Plugin System** - Use chugins to extend ChucK with effects and instruments
- **Two Modes** - Real-time playback or offline rendering to `numpy` arrays
- **Interactive Control** - Bidirectional communication via global variables and events
- **Live Coding** - Hot-swap running code, manage shreds, introspect VM state
- **Complete ChucK** - Full access to ChucK's powerful synthesis and sound processing
- **Examples Included** - 50+ ChucK examples and pre-built chugins ready to use

## Overview

`pychuck` provides a high-performance Python wrapper for ChucK, allowing you to:

- Run ChucK code from Python (both inline code and `.ck` files)
- Real-time audio playback using RtAudio (cross-platform, asynchronous)
- Offline audio processing for rendering audio to numpy arrays
- **Interactive communication** - Set/get global variables, signal events, register callbacks
- **Live coding support** - Replace running shreds, introspect VM state, manage shred lifecycle
- Chugin support - Load and use ChucK plugins (effects, instruments, etc.)
- Process audio using ChucK's powerful synthesis and sound processing
- Control ChucK VM parameters and manage running shreds
- Run multiple concurrent ChucK programs (shreds)

## Installation

### Build from source

```bash
# Clone the repository
git clone <repository-url>
cd pychuck

# Build the extension
make build

# Run tests
make test
```

## Quick Start

### Real-Time Audio

```python
import pychuck
import time

# Create and configure ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile ChucK code
chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    while(true) { 1::samp => now; }
''')

# Start real-time audio playback
pychuck.start_audio(chuck)
time.sleep(2)  # Play for 2 seconds
pychuck.stop_audio()
pychuck.shutdown_audio()
```

### Offline Rendering

```python
import pychuck
import numpy as np

# Create ChucK instance
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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

### ChucK Class

#### Initialization Methods

- **`__init__()`** - Create a new ChucK instance
- **`init() -> bool`** - Initialize ChucK with current parameters
- **`start() -> bool`** - Explicitly start ChucK VM (called implicitly by `run()` if needed)

#### Parameter Configuration

- **`set_param(name: str, value: int) -> int`** - Set integer parameter
- **`set_param_float(name: str, value: float) -> int`** - Set float parameter
- **`set_param_string(name: str, value: str) -> int`** - Set string parameter
- **`set_param_string_list(name: str, value: list[str]) -> int`** - Set string list parameter
- **`get_param_int(name: str) -> int`** - Get integer parameter
- **`get_param_float(name: str) -> float`** - Get float parameter
- **`get_param_string(name: str) -> str`** - Get string parameter
- **`get_param_string_list(name: str) -> list[str]`** - Get string list parameter

#### Compilation Methods

- **`compile_code(code: str, args: str = "", count: int = 1, immediate: bool = False, filepath: str = "") -> tuple[bool, list[int]]`**
  - Compile ChucK code from string
  - Returns: `(success, shred_ids)`
  - Parameters:
    - `code`: ChucK code to compile
    - `args`: Additional arguments (separated by ':')
    - `count`: Number of shred instances to spork
    - `immediate`: If True, schedule immediately; if False, queue for next time step
    - `filepath`: Optional filepath for path-related operations

- **`compile_file(path: str, args: str = "", count: int = 1, immediate: bool = False) -> tuple[bool, list[int]]`**
  - Compile ChucK code from file
  - Returns: `(success, shred_ids)`

#### Audio Processing

- **`run(input: np.ndarray, output: np.ndarray, num_frames: int)`**
  - Process audio for specified number of frames (synchronous/offline)
  - `input`: Input buffer (1D numpy array, dtype=np.float32)
    - Size must be `num_frames * input_channels`
  - `output`: Output buffer (1D numpy array, dtype=np.float32, C-contiguous)
    - Size must be `num_frames * output_channels`
  - `num_frames`: Number of audio frames to process

#### Real-Time Audio (RtAudio)

- **`start_audio(chuck: ChucK, sample_rate: int = 44100, num_dac_channels: int = 2, num_adc_channels: int = 0, dac_device: int = 0, adc_device: int = 0, buffer_size: int = 512, num_buffers: int = 8) -> bool`**
  - Start real-time audio playback using RtAudio
  - Audio plays asynchronously in the background
  - Returns: True if successful

- **`stop_audio() -> bool`**
  - Stop real-time audio playback
  - Returns: True if successful

- **`shutdown_audio(msWait: int = 0)`**
  - Shutdown audio system completely
  - `msWait`: Milliseconds to wait before shutdown

- **`audio_info() -> dict`**
  - Get current audio system information
  - Returns dict with keys: `sample_rate`, `num_channels_out`, `num_channels_in`, `buffer_size`

#### Global Variable Management

- **`set_global_int(name: str, value: int)`** - Set a global int variable
- **`set_global_float(name: str, value: float)`** - Set a global float variable
- **`set_global_string(name: str, value: str)`** - Set a global string variable
- **`get_global_int(name: str, callback: Callable[[int], None])`** - Get a global int (async via callback)
- **`get_global_float(name: str, callback: Callable[[float], None])`** - Get a global float (async via callback)
- **`get_global_string(name: str, callback: Callable[[str], None])`** - Get a global string (async via callback)
- **`set_global_int_array(name: str, values: list[int])`** - Set a global int array
- **`set_global_float_array(name: str, values: list[float])`** - Set a global float array
- **`set_global_int_array_value(name: str, index: int, value: int)`** - Set array element by index
- **`set_global_float_array_value(name: str, index: int, value: float)`** - Set array element by index
- **`set_global_associative_int_array_value(name: str, key: str, value: int)`** - Set map value by key
- **`set_global_associative_float_array_value(name: str, key: str, value: float)`** - Set map value by key
- **`get_global_int_array(name: str, callback: Callable[[list[int]], None])`** - Get int array (async)
- **`get_global_float_array(name: str, callback: Callable[[list[float]], None])`** - Get float array (async)
- **`get_all_globals() -> list[tuple[str, str]]`** - Get list of all globals as (type, name) pairs

#### Global Event Management

- **`signal_global_event(name: str)`** - Signal a global event (wakes one waiting shred)
- **`broadcast_global_event(name: str)`** - Broadcast a global event (wakes all waiting shreds)
- **`listen_for_global_event(name: str, callback: Callable[[], None], listen_forever: bool = True) -> int`** - Listen for event, returns listener ID
- **`stop_listening_for_global_event(name: str, callback_id: int)`** - Stop listening using listener ID

#### Shred Management

- **`remove_shred(shred_id: int)`** - Remove a shred by ID
- **`remove_all_shreds()`** - Remove all running shreds from VM
- **`get_all_shred_ids() -> list[int]`** - Get IDs of all running shreds
- **`get_ready_shred_ids() -> list[int]`** - Get IDs of ready (not blocked) shreds
- **`get_blocked_shred_ids() -> list[int]`** - Get IDs of blocked shreds
- **`get_last_shred_id() -> int`** - Get ID of last sporked shred
- **`get_next_shred_id() -> int`** - Get what the next shred ID will be
- **`get_shred_info(shred_id: int) -> dict`** - Get shred info (id, name, is_running, is_done)

#### VM Control

- **`clear_vm()`** - Clear the VM (remove all shreds)
- **`clear_globals()`** - Clear global variables without clearing the VM
- **`reset_shred_id()`** - Reset the shred ID counter
- **`replace_shred(shred_id: int, code: str, args: str = "") -> int`** - Replace running shred with new code

#### Status and Utility

- **`is_init() -> bool`** - Check if ChucK is initialized
- **`vm_running() -> bool`** - Check if VM is running
- **`now() -> float`** - Get current ChucK time in samples

#### Console Output Control

- **`set_chout_callback(callback: Callable[[str], None]) -> bool`** - Capture ChucK console output
- **`set_cherr_callback(callback: Callable[[str], None]) -> bool`** - Capture ChucK error output
- **`toggle_global_color_textoutput(onOff: bool)`** - Enable/disable color output
- **`probe_chugins()`** - Print info on all loaded chugins

#### Static Methods

- **`version() -> str`** - Get ChucK version string
- **`int_size() -> int`** - Get ChucK integer size in bits
- **`num_vms() -> int`** - Get number of active ChucK VMs
- **`set_log_level(level: int)`** - Set global log level
- **`get_log_level() -> int`** - Get global log level
- **`poop()`** - ChucK poop compatibility
- **`set_stdout_callback(callback: Callable[[str], None]) -> bool`** - Set global stdout callback (static)
- **`set_stderr_callback(callback: Callable[[str], None]) -> bool`** - Set global stderr callback (static)
- **`global_cleanup()`** - Global cleanup for all ChucK instances

### Parameter Constants

#### Core Parameters

- `PARAM_VERSION` - ChucK version
- `PARAM_SAMPLE_RATE` - Sample rate (default: 44100)
- `PARAM_INPUT_CHANNELS` - Number of input channels
- `PARAM_OUTPUT_CHANNELS` - Number of output channels

#### VM Configuration

- `PARAM_VM_ADAPTIVE` - Adaptive VM mode
- `PARAM_VM_HALT` - VM halt on errors
- `PARAM_OTF_ENABLE` - On-the-fly programming enable
- `PARAM_OTF_PORT` - On-the-fly programming port
- `PARAM_DUMP_INSTRUCTIONS` - Dump VM instructions
- `PARAM_AUTO_DEPEND` - Auto dependency resolution
- `PARAM_DEPRECATE_LEVEL` - Deprecation warning level

#### Paths

- `PARAM_WORKING_DIRECTORY` - Working directory path
- `PARAM_CHUGIN_ENABLE` - Enable chugins (plugins)
- `PARAM_USER_CHUGINS` - User chugin paths
- `PARAM_IMPORT_PATH_SYSTEM` - System import search paths
- `PARAM_IMPORT_PATH_PACKAGES` - Package import search paths
- `PARAM_IMPORT_PATH_USER` - User import search paths

#### Display & Debugging

- `PARAM_OTF_PRINT_WARNINGS` - Print on-the-fly compiler warnings
- `PARAM_IS_REALTIME_AUDIO_HINT` - Hint for real-time audio mode
- `PARAM_COMPILER_HIGHLIGHT_ON_ERROR` - Syntax highlighting in error messages
- `PARAM_TTY_COLOR` - Enable color output in terminal
- `PARAM_TTY_WIDTH_HINT` - Terminal width hint for formatting

### Module Functions

- **`version() -> str`** - Get ChucK version (convenience function)

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

- For stereo output: `[L0, R0, L1, R1, L2, R2, ...]`
- Buffer size = `num_frames * num_channels`

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
import pychuck
import time

# Create and initialize ChucK
chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile ChucK code
chuck.compile_code('''
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while(true) { 1::samp => now; }
''')

# Start real-time audio (plays asynchronously)
pychuck.start_audio(chuck, sample_rate=44100, num_dac_channels=2)

# Audio plays in background
time.sleep(3)  # Play for 3 seconds

# Stop audio
pychuck.stop_audio()
pychuck.shutdown_audio()
```

### Offline Audio Processing

```python
import pychuck
import numpy as np

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
print(f"ChucK version: {pychuck.version()}")

# Configure VM
chuck.set_param(pychuck.PARAM_VM_HALT, 0)
chuck.set_param_string(pychuck.PARAM_WORKING_DIRECTORY, "/path/to/files")

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
import pychuck

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()

# Compile from file
success, shred_ids = chuck.compile_file("examples/basic/blit2.ck")

# Start playback
pychuck.start_audio(chuck)
import time; time.sleep(2)
pychuck.stop_audio()
pychuck.shutdown_audio()
```

### Using Chugins (Plugins)

```python
import pychuck

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)

# Enable chugins and set search path
chuck.set_param(pychuck.PARAM_CHUGIN_ENABLE, 1)
chuck.set_param_string(pychuck.PARAM_USER_CHUGINS, "./examples/chugins")

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
import pychuck
import numpy as np

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
import pychuck
import numpy as np

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
import pychuck
import numpy as np

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
import pychuck
import numpy as np

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_INPUT_CHANNELS, 2)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
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
import pychuck

chuck = pychuck.ChucK()
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

## Architecture

- **Core**: ChucK virtual machine and compiler (C++)
- **Bindings**: nanobind for efficient Python/C++ interop
- **Build**: CMake + scikit-build-core for modern Python packaging
- **Audio**:
  - Real-time: RtAudio (CoreAudio on macOS, DirectSound/WASAPI on Windows, ALSA/JACK on Linux)
  - Offline: Float32 sample processing, interleaved buffer format
- **Plugins**: Chugin support for extending ChucK functionality

## Features

### Complete ChucK Integration

- Full ChucK VM and compiler access
- Compile from strings or files
- Parameter configuration and introspection
- Advanced shred (thread) management and introspection

### Interactive Python/ChucK Communication

- **Global Variables**: Bidirectional data exchange between Python and ChucK
  - Set/get primitives (int, float, string)
  - Set/get arrays (indexed and associative)
  - Async callbacks for getting values
- **Global Events**: Event-driven communication
  - Signal/broadcast events from Python to ChucK
  - Listen for events from ChucK in Python
  - Persistent or one-shot event listeners
- **Console Capture**: Redirect ChucK output to Python callbacks

### Live Coding Support

- **Shred Introspection**: List, query, and monitor running shreds
- **Shred Control**: Remove individual shreds or clear entire VM
- **Hot Swapping**: Replace running shred code without stopping audio
- **VM Management**: Clear globals, reset IDs, fine-grained control

### Two Audio Modes

- **Real-time**: Asynchronous playback through system audio
- **Offline**: Synchronous rendering to numpy arrays

### Plugin Support

- Load chugins (ChucK plugins)
- Configurable search paths
- Examples included in `examples/chugins/`

### Examples Included

- Basic synthesis examples in `examples/basic/`
- Effect examples in `examples/effects/`
- Pre-built chugins in `examples/chugins/`
- Comprehensive test suite

## Requirements

- Python 3.8+
- CMake 3.15+
- C++17 compatible compiler
- macOS: Xcode with CoreAudio/CoreMIDI frameworks
- numpy (for audio processing)

## Development

```bash
# Build
make build

# Run tests
make test

# Clean build artifacts
make clean
```

## License

ChucK is licensed under the GNU General Public License v2.0.

## Credits

- **ChucK**: Ge Wang, Perry Cook, and the ChucK team
- **nanobind**: Wenzel Jakob and contributors
- **claude-code**: Anthropic
