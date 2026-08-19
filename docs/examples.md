# Examples

Worked patterns, ordered roughly from simplest to most involved. Each one runs
against the current build.

Most examples render offline, which needs no audio hardware and is the easiest
way to test ChucK code. Where real-time playback matters, it says so.

## Basic synthesis

### A sine wave

```python
import numchuck

audio = numchuck.render(
    "SinOsc s => dac; 440 => s.freq; 0.3 => s.gain; 2::second => now;",
    duration=2.0,
)
numchuck.to_wav("sine.wav", code="SinOsc s => dac; 440 => s.freq;", duration=2.0)
```

`render()` returns interleaved float32 samples: `duration * sample_rate *
channels` of them. Split the channels with `audio.reshape(-1, 2)`.

### A chord

```python
from numchuck import Chuck

CHORD = """
    [261.63, 329.63, 392.00] @=> float freqs[];

    for (0 => int i; i < freqs.size(); i++) {
        SinOsc s => dac;
        freqs[i] => s.freq;
        0.15 => s.gain;
    }

    3::second => now;
"""

with Chuck(input_channels=0, output_channels=2) as chuck:
    success, _ = chuck.compile(CHORD)
    assert success
    audio = chuck.run(chuck.sample_rate * 3)
```

### Building a graph in stages

```python
PATCH = """
    SawOsc saw => LPF filter => NRev reverb => dac;
    110 => saw.freq;
    0.2 => saw.gain;
    800 => filter.freq;
    0.1 => reverb.mix;
    while (true) { 1::samp => now; }
"""

with Chuck(input_channels=0) as chuck:
    chuck.compile(PATCH)
    audio = chuck.run(chuck.sample_rate)
```

## Live coding

### Driving parameters from Python

Declare globals in ChucK, then write to them while the shred runs:

```python
from numchuck import Chuck

CODE = """
    global float frequency;
    global float gain;

    SinOsc s => dac;
    440 => frequency;
    0.3 => gain;

    while (true) {
        frequency => s.freq;
        gain => s.gain;
        10::ms => now;
    }
"""

with Chuck(input_channels=0) as chuck:
    chuck.compile(CODE)

    chunks = []
    for freq in (220.0, 330.0, 440.0, 550.0):
        chuck.set_float("frequency", freq)
        chunks.append(chuck.run(chuck.sample_rate // 4).copy())
```

A typed accessor reads better when you touch one global repeatedly:

```python
freq = chuck.global_float("frequency")
for value in (220.0, 440.0, 880.0):
    freq.value = value
    chuck.run(4410)
```

### Hot-swapping a shred

`spork()` hands back a `Shred` that can be replaced in place, which is the
core live-coding move:

```python
with Chuck(input_channels=0) as chuck:
    shred = chuck.spork("SinOsc s => dac; while (true) { 1::samp => now; }")
    chuck.run(4410)

    shred.replace("SawOsc s => dac; 0.2 => s.gain; while (true) { 1::samp => now; }")
    chuck.run(4410)

    shred.remove()
```

### Watching the shred list change

Rather than polling `chuck.shreds`:

```python
import numchuck
from numchuck import Chuck

def on_change(event, shred_id, name):
    print(f"{event}: shred {shred_id} ({name})")

with Chuck(input_channels=0) as chuck:
    chuck.on_shred(on_change, options=numchuck.SHRED_WATCH_ALL)
    chuck.compile("SinOsc s => dac; while (true) { 1::samp => now; }")
    chuck.run(512)
```

## Events

### Triggering ChucK from Python

```python
from numchuck import Chuck

CODE = """
    global Event trigger;

    while (true) {
        trigger => now;
        SinOsc s => dac;
        800 => s.freq;
        0.3 => s.gain;
        100::ms => now;
        s =< dac;
    }
"""

with Chuck(input_channels=0) as chuck:
    chuck.compile(CODE)
    chuck.run(256)

    for _ in range(4):
        chuck.signal_event("trigger")
        chuck.run(chuck.sample_rate // 4)
```

### Both directions at once

```python
CODE = """
    global Event ready;
    global int result;

    while (true) {
        1::second => now;
        42 => result;
        ready.broadcast();
    }
"""

with Chuck(input_channels=0) as chuck:
    chuck.compile(CODE)

    got = []
    callback_id = chuck.on_event("ready", lambda: got.append(chuck.get_int("result")))

    chuck.run(chuck.sample_rate * 2)
    chuck.stop_listening_for_event("ready", callback_id)
```

!!! note "Callbacks run on the VM's thread"
    During real-time audio that is the audio thread, so keep them brief — queue
    the work instead of doing it inline.

## Audio processing

### Rendering in chunks

`stream()` avoids holding a long render in memory at once:

```python
import numpy as np
from numchuck import Chuck

with Chuck(input_channels=0) as chuck:
    chuck.compile("SinOsc s => dac; 440 => s.freq; while (true) { 1::samp => now; }")

    peak = 0.0
    for chunk in chuck.stream(frames_per_chunk=1024, max_chunks=100):
        peak = max(peak, float(np.abs(chunk).max()))
```

The chunk is reused between iterations, so copy it if you intend to keep it:

```python
collected = [chunk.copy() for chunk in chuck.stream(max_chunks=10)]
```

### Feeding audio in

Pass an input buffer to process external audio through a ChucK graph:

```python
import numpy as np
from numchuck import Chuck

frames = 44100
with Chuck(input_channels=2, output_channels=2) as chuck:
    chuck.compile("adc => LPF f => dac; 500 => f.freq; while (true) { 1::samp => now; }")

    noise = np.random.default_rng(0).standard_normal(frames * 2).astype(np.float32) * 0.1
    filtered = chuck.run(frames, input=noise)
```

### Zero-allocation rendering

For a render loop that must not touch the allocator, supply the output buffer:

```python
import numpy as np

buf = np.zeros(512 * 2, dtype=np.float32)
with Chuck(input_channels=0) as chuck:
    chuck.compile("SinOsc s => dac; while (true) { 1::samp => now; }")
    for _ in range(100):
        chuck.run(512, output=buf)      # writes into buf, returns it
```

### Reading a signal mid-graph

`run()` gives you the `dac` sum. To watch one UGen, declare it global, enable
its buffer, and register a tap:

```python
with Chuck(input_channels=0) as chuck:
    chuck.compile("""
        global SinOsc osc;
        1 => osc.buffered;
        osc => LPF f => dac;
        440 => osc.freq;
        while (true) { 1::samp => now; }
    """)
    chuck.run(8192)

    chuck.add_tap("osc", num_channels=1, capacity_frames=8192)
    chuck.run(4096)

    pre_filter = chuck.ugen_samples("osc", 1024)   # (1024,) float32
```

The tap is what makes this safe during real-time audio — see
[Audio](api/audio.md#global-ugen-taps) for why a direct read races.

## Files

### Running a `.ck` file

```python
import numchuck

audio = numchuck.render_file("song.ck", duration=30.0)
numchuck.to_wav("song.wav", files="song.ck", duration=30.0)
```

Or with a VM you keep:

```python
from numchuck import Chuck

with Chuck(input_channels=0) as chuck:
    success, shred_ids = chuck.compile_file("song.ck")
    if not success:
        raise RuntimeError("compilation failed")
    audio = chuck.run(chuck.sample_rate * 10)
```

### Several files together

Files compiled into one instance share the VM, so they can talk to each other
through globals:

```python
audio = numchuck.render_file(["bass.ck", "drums.ck", "melody.ck"], duration=30.0)
```

Set a working directory when the code refers to samples by relative path:

```python
with Chuck(working_directory="/path/to/project", input_channels=0) as chuck:
    chuck.compile_file("/path/to/project/main.ck")
```

## Advanced

### A sequencer driven from Python

```python
from numchuck import Chuck

CODE = """
    global float note;
    global Event play;

    SinOsc s => ADSR env => dac;
    env.set(10::ms, 50::ms, 0.3, 100::ms);
    0.3 => s.gain;

    while (true) {
        play => now;
        note => s.freq;
        env.keyOn();
        150::ms => now;
        env.keyOff();
        50::ms => now;
    }
"""

SEQUENCE = [261.63, 293.66, 329.63, 349.23, 392.00]

with Chuck(input_channels=0) as chuck:
    chuck.compile(CODE)
    chuck.run(256)

    rendered = []
    for freq in SEQUENCE:
        chuck.set_float("note", freq)
        chuck.signal_event("play")
        rendered.append(chuck.run(chuck.sample_rate // 4).copy())
```

### Real-time playback

Everything above renders offline. To hear it live:

```python
import time
from numchuck import Chuck
from numchuck._numchuck import start_audio, stop_audio, shutdown_audio

chuck = Chuck(input_channels=0, output_channels=2)
chuck.compile("SinOsc s => dac; 440 => s.freq; while (true) { 100::ms => now; }")

start_audio(chuck.raw)
try:
    time.sleep(5)
    chuck.set_float("frequency", 880.0)   # the VM advances on the audio thread
    time.sleep(5)
finally:
    stop_audio()
    shutdown_audio()
    chuck.close()
```

!!! warning "One instance can have real-time audio"
    For several sounds at once, spork several shreds into one instance. Separate
    `Chuck` objects are for separate offline renders, not for concurrent
    playback.

### Several instances, offline

```python
from numchuck import Chuck

renders = []
for freq in (220, 440, 880):
    with Chuck(input_channels=0) as chuck:
        chuck.compile(f"SinOsc s => dac; {freq} => s.freq; while (true) {{ 1::samp => now; }}")
        renders.append(chuck.run(44100))
```

## See also

- [Quickstart](quickstart.md) — the guided introduction
- [Error handling](error_handling.md) — what raises, and when
- [API reference](api/chuck.md) — generated from the source
- The [`examples/`](https://github.com/shakfu/numchuck/tree/main/examples)
  directory in the repository holds 500+ ChucK programs from the upstream
  distribution
