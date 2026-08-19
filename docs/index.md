# numchuck

Python bindings for the [ChucK](https://chuck.stanford.edu) audio programming
language, built with [nanobind](https://github.com/wjakob/nanobind).

numchuck gives Python programmatic control over a ChucK virtual machine: compile
and run `.ck` code, render audio offline into NumPy arrays or play it in real
time, exchange values and events with running shreds, and hot-swap code while it
plays.

## Two APIs

There are two layers, and most code should use the first.

| | Import | Use it for |
| --- | --- | --- |
| **High level** | `from numchuck import Chuck` | Everything. Keyword-argument construction, properties instead of parameter constants, NumPy in and out, context-manager cleanup. |
| **Low level** | `from numchuck._numchuck import ChucK` | The raw binding, mirroring ChucK's own C++ API. Reach for it when the wrapper does not expose something; `Chuck.raw` hands you the same object. |

The two are not alternatives so much as layers: `Chuck` holds a `ChucK` and
delegates to it.

## Quick start

```python
import numchuck

# Render a second of audio to a NumPy array, no audio hardware involved
audio = numchuck.render("SinOsc s => dac; 1::second => now;", duration=1.0)
print(audio.shape, audio.dtype)   # (88200,) float32 -- interleaved stereo

# Or write it straight to a file
numchuck.to_wav("out.wav", code="SinOsc s => dac; 440 => s.freq;", duration=5.0)
```

Driving a VM directly:

```python
from numchuck import Chuck

with Chuck(sample_rate=48000, output_channels=2) as chuck:
    chuck.compile("SinOsc s => dac; 440 => s.freq; while(true) { 100::ms => now; }")
    frames = chuck.run(48000)     # one second: 96000 interleaved float32 samples
```

See [Quickstart](quickstart.md) for the guided version.

## Installation

```bash
pip install numchuck
```

From source:

```bash
git clone https://github.com/shakfu/numchuck
cd numchuck
make build
```

The repository vendors ChucK, its chugins, nanobind and mongoose, so no
`--recursive` clone is needed — see
[`thirdparty/VERSIONS.md`](https://github.com/shakfu/numchuck/blob/main/thirdparty/VERSIONS.md).

## What is included

### Library

- **Full ChucK API access** — compilation, VM control, shred lifecycle
- **Real-time audio** through RtAudio, and **offline rendering** to NumPy
- **Global variables and events** for bidirectional Python/ChucK communication
- **Global UGen taps** for reading audio mid-graph without racing the audio thread
- **40+ bundled chugins**, working out of the box from a wheel
- **Type stubs** for both extension modules, checked with `mypy --strict`

### Interfaces

- **Interactive REPL** with ChucK syntax highlighting and completion
- **Multi-tab editor** for live coding, with automatic file versioning
- **Web IDE** in the browser — bound to loopback by default; see the
  [README](https://github.com/shakfu/numchuck#7-web-ide-browser-based) for its
  trust model
- **Command-line execution** of `.ck` files

## Where to go next

- [Quickstart](quickstart.md) — the guided introduction
- [Examples](examples.md) — worked patterns, from synthesis to live coding
- [Error handling](error_handling.md) — what raises what, and how to respond
- [API reference](api/chuck.md) — generated from the source
- [Architecture](architecture.md) — how the layers fit together
