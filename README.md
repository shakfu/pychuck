# pychuck

Python bindings for the [ChucK](https://chuck.stanford.edu) audio programming language using [nanobind](https://github.com/wjakob/nanobind).

## Highlights

- **Real-Time Audio** - Play ChucK code through your speakers with asynchronous RtAudio playback
- **File Support** - Load and run `.ck` files directly
- **Plugin System** - Use chugins to extend ChucK with effects and instruments
- **Two Modes** - Real-time playback or offline rendering to `numpy` arrays
- **Complete ChucK** - Full access to ChucK's powerful synthesis and sound processing
- **Examples Included** - 50+ ChucK examples and pre-built chugins ready to use

## Overview

`pychuck` provides a high-performance Python wrapper for ChucK, allowing you to:

- Run ChucK code from Python (both inline code and `.ck` files)
- Real-time audio playback using RtAudio (cross-platform, asynchronous)
- Offline audio processing for rendering audio to numpy arrays
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

#### Shred Management

- **`remove_all_shreds()`** - Remove all running shreds from VM

#### Status and Utility

- **`is_init() -> bool`** - Check if ChucK is initialized
- **`vm_running() -> bool`** - Check if VM is running
- **`now() -> float`** - Get current ChucK time in samples

#### Static Methods

- **`version() -> str`** - Get ChucK version string
- **`int_size() -> int`** - Get ChucK integer size in bits
- **`num_vms() -> int`** - Get number of active ChucK VMs
- **`set_log_level(level: int)`** - Set global log level

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
- Shred (thread) management

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
