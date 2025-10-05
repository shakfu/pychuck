# PyChuck Python Examples

This directory contains illustrated Python examples demonstrating how to use `pychuck` to integrate ChucK audio programming into Python applications.

## Overview

These examples progressively demonstrate pychuck features from basic synthesis to advanced techniques, chugin usage, and file loading.

## Examples

### Basic Examples

#### 01_basic_sine.py
**Real-time sine wave playback**

Demonstrates:
- Creating a ChucK instance
- Compiling inline ChucK code
- Starting real-time audio playback
- Basic audio lifecycle management

```bash
python examples/python/01_basic_sine.py
```

#### 02_offline_render.py
**Offline audio rendering to numpy arrays**

Demonstrates:
- Synchronous/offline audio processing
- Rendering ChucK audio to numpy arrays
- Analyzing generated audio data
- Frequency sweep synthesis
- Optional: Plotting waveforms and saving WAV files

```bash
python examples/python/02_offline_render.py
```

Requires: `numpy`, optional: `matplotlib`, `scipy`

#### 03_load_chuck_file.py
**Loading external ChucK files**

Demonstrates:
- Loading `.ck` files from disk
- Using the `examples/basic/` directory
- File path resolution
- Getting audio system information

```bash
python examples/python/03_load_chuck_file.py
```

Uses: `examples/basic/blit2.ck`

#### 04_multiple_shreds.py
**Running multiple concurrent ChucK shreds**

Demonstrates:
- Spawning multiple ChucK threads (shreds)
- Creating harmonic series
- Dynamic shred management
- Removing and replacing shreds at runtime

```bash
python examples/python/04_multiple_shreds.py
```

### Chugin Examples

#### 05_bitcrusher_chugin.py
**Using the Bitcrusher effect plugin**

Demonstrates:
- Enabling chugin support
- Setting chugin search paths
- Using the Bitcrusher effect
- Dynamic parameter sweeping

```bash
python examples/python/05_bitcrusher_chugin.py
```

Requires: `Bitcrusher.chug` in `examples/chugins/`

#### 06_reverb_chugin.py
**Using the GVerb reverb plugin**

Demonstrates:
- Spatial audio effects with GVerb
- Configuring reverb parameters
- Mixing dry and wet signals
- Rhythmic impulse generation

```bash
python examples/python/06_reverb_chugin.py
```

Requires: `GVerb.chug` in `examples/chugins/`

### Advanced Examples

#### 07_parameter_control.py
**ChucK VM parameter configuration**

Demonstrates:
- Configuring sample rate and channels
- Setting working directory
- Reading parameter values
- Checking initialization state
- VM status monitoring

```bash
python examples/python/07_parameter_control.py
```

#### 08_advanced_synthesis.py
**FM synthesis with filtering and envelopes**

Demonstrates:
- Frequency modulation (FM) synthesis
- Low-pass filtering
- ADSR envelope shaping
- Multiple unit generator (UGen) chains
- Sporking concurrent processes
- Melodic sequences

```bash
python examples/python/08_advanced_synthesis.py
```

#### 09_sequenced_shreds.py
**Time-sequenced shred playback**

Demonstrates:
- Launching shreds at different times (sequencing)
- Creating rhythmic patterns with delayed starts
- Building up a composition layer by layer
- Dynamic arrangement changes (removing/adding layers)
- Creating variations by rebuilding the arrangement
- Rhythmic elements: bass drum, snare, hi-hat, bass synth, pads, melody
- ~20 second evolving composition

```bash
python examples/python/09_sequenced_shreds.py
```

## Running Examples

### Prerequisites

All examples require:
- `pychuck` installed (from project root: `pip install .` or `pip install -e .`)
- `numpy`

Some examples have optional dependencies:
- `matplotlib` (for waveform plotting in example 02)
- `scipy` (for WAV export in example 02)

### Installation

```bash
# From project root
pip install -e .

# Optional dependencies for example 02
pip install matplotlib scipy
```

### Running

```bash
# From project root
python examples/python/01_basic_sine.py
python examples/python/02_offline_render.py
# ... etc
```

Or make them executable:

```bash
chmod +x examples/python/*.py
./examples/python/01_basic_sine.py
```

## Example Progression

The examples are numbered to provide a learning path:

1. **01-02**: Basic concepts (real-time vs offline, inline code)
2. **03-04**: File loading and multiple shreds
3. **05-06**: Using chugins (effects plugins)
4. **07-09**: Advanced configuration, synthesis, and sequencing

## ChucK Code Sources

Examples use ChucK code from:
- **Inline code**: Examples 01, 02, 04, 07, 08
- **External files**: Example 03 (from `examples/basic/blit2.ck`)
- **Chugins**: Examples 05, 06 (from `examples/chugins/`)

## Common Patterns

### Basic Setup

```python
import pychuck

chuck = pychuck.ChucK()
chuck.set_param(pychuck.PARAM_SAMPLE_RATE, 44100)
chuck.set_param(pychuck.PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
```

### Real-time Playback

```python
# Compile code
success, shred_ids = chuck.compile_code(code)

# Start audio
pychuck.start_audio(chuck)
time.sleep(duration)

# Cleanup
pychuck.stop_audio()
pychuck.shutdown_audio()
```

### Offline Rendering

```python
# Compile code
success, _ = chuck.compile_code(code)

# Prepare buffers (float32!)
input_buf = np.zeros(0, dtype=np.float32)
output_buf = np.zeros(num_frames * channels, dtype=np.float32)

# Render
chuck.run(input_buf, output_buf, num_frames)
```

### Using Chugins

```python
# Set chugin path and enable
chuck.set_param(pychuck.PARAM_CHUGIN_ENABLE, 1)
chuck.set_param_string(pychuck.PARAM_USER_CHUGINS, "/path/to/chugins")
chuck.init()

# Use chugin in code
code = "SinOsc s => Bitcrusher bc => dac;"
```

## Troubleshooting

### "ChucK instance not initialized"
Call `chuck.init()` before compiling or running audio.

### "Compilation failed" when using chugins
- Ensure chugins are built: `make build` in project root
- Check chugin path: `examples/chugins/*.chug`
- Verify `PARAM_CHUGIN_ENABLE` is set to 1

### "Buffer size mismatch"
- Use `dtype=np.float32` for all audio buffers
- Calculate size as: `num_frames * num_channels`
- Buffers are 1D interleaved: `[L0, R0, L1, R1, ...]`

### Silent audio output
- Ensure ChucK code advances time: `while(true) { 1::samp => now; }`
- Check gain levels (not set to 0)
- Verify dtype is `np.float32`, not `np.float64`

## Further Reading

- [pychuck README](../../README.md) - Main documentation
- [ChucK Documentation](https://chuck.stanford.edu/doc/) - ChucK language reference
- [ChucK Examples](../../examples/) - Original ChucK example scripts
- [Architecture Documentation](../../ARCHITECTURE.md) - Technical details

## Contributing

To add more examples:
1. Number them sequentially (09_, 10_, etc.)
2. Include comprehensive docstring
3. Add entry to this README
4. Test thoroughly
5. Follow the established pattern

## License

These examples are part of pychuck and follow the same license (GPL v2).
