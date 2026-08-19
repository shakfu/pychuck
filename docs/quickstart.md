# Quickstart

This guide walks through the parts of numchuck you are most likely to need
first. Everything here uses the high-level [`Chuck`](api/chuck.md) class unless
it says otherwise.

## Installation

```bash
pip install numchuck
```

From source:

```bash
git clone https://github.com/shakfu/numchuck
cd numchuck
make build     # or: pip install -e .
```

## Creating a VM

`Chuck` takes keyword arguments and initializes itself, so there is no
parameter-constant dance and no separate `init()` call:

```python
from numchuck import Chuck

chuck = Chuck(sample_rate=44100, input_channels=0, output_channels=2)
```

Use it as a context manager when you can. Explicit teardown matters on Windows,
where audio threads need to be joined before memory is released:

```python
with Chuck(output_channels=2) as chuck:
    ...
# close() is called on the way out
```

## Compiling and running code

`compile()` returns `(success, shred_ids)`:

```python
success, shred_ids = chuck.compile("""
    SinOsc s => dac;
    440 => s.freq;
    0.5 => s.gain;
    while (true) { 100::ms => now; }
""")

if success:
    print(f"shred {shred_ids[0]} is running")
```

`spork()` is the same thing with a friendlier return value — a `Shred` object
you can remove or replace later:

```python
shred = chuck.spork("SinOsc s => dac; while (true) { 1::second => now; }")
shred.replace("TriOsc t => dac; while (true) { 1::second => now; }")
shred.remove()
```

!!! note "ChucK code must advance time"
    A shred that never reaches `=> now` produces no audio and blocks the VM.
    Every example here advances time, usually with a `while` loop.

## Rendering audio offline

This is the path that needs no audio hardware, and it is the easiest to test.
`run()` returns a flat float32 array of `num_frames * output_channels` samples,
interleaved as ChucK writes them:

```python
audio = chuck.run(44100)       # one second of stereo
print(audio.shape)             # (88200,) -- [L0, R0, L1, R1, ...]
```

Reshape when you want the channels apart:

```python
stereo = audio.reshape(-1, chuck.output_channels)   # (44100, 2)
left, right = stereo[:, 0], stereo[:, 1]
```

For long renders, `stream()` yields chunks and reuses its buffer by default:

```python
for chunk in chuck.stream(frames_per_chunk=512, max_chunks=100):
    process(chunk)             # (1024,) float32 for stereo
```

!!! warning "`stream()` reuses its buffer"
    With `reuse=True` (the default) every chunk is the same array, refilled.
    Copy it if you intend to keep it — appending chunks to a list gives you a
    list of references to one buffer.

If you only want the audio and not the VM, the module-level helpers do the whole
job in one call:

```python
import numchuck

audio = numchuck.render("SinOsc s => dac; 1::second => now;", duration=1.0)
numchuck.render_file("song.ck", duration=30.0)
numchuck.to_wav("out.wav", code="SinOsc s => dac;", duration=5.0)
```

## Real-time audio

Real-time playback is driven by RtAudio, started against a specific instance:

```python
from numchuck._numchuck import start_audio, stop_audio, shutdown_audio

chuck = Chuck(input_channels=0, output_channels=2)
chuck.compile("SinOsc s => dac; 440 => s.freq; while (true) { 100::ms => now; }")

start_audio(chuck.raw)         # takes the underlying ChucK instance
...
stop_audio()
shutdown_audio()
```

!!! warning "One instance at a time"
    Only one `Chuck` can have real-time audio active in a process. For
    concurrency, run several shreds inside one instance — that is what shreds
    are for.

## Shred management

```python
chuck.shreds                       # [1, 2, 3]
chuck.shred_info(1)                # {'id': 1, 'name': ..., 'is_blocked': ...}
chuck.remove_shred(1)
chuck.replace_shred(2, "SinOsc s => dac; while (true) { 1::second => now; }")
chuck.clear()                      # remove everything
```

To be told about lifecycle changes rather than polling for them:

```python
import numchuck

def on_change(event, shred_id, name):
    print(event, shred_id, name)

chuck.on_shred(on_change, options=numchuck.SHRED_WATCH_ALL)
```

## Global variables

Declare the global in ChucK, then read and write it from Python:

```python
chuck.compile("""
    global int counter;
    global float frequency;
    while (true) { 100::ms => now; }
""")

chuck.set_int("counter", 42)
chuck.set_float("frequency", 440.0)

print(chuck.get_int("counter"))       # 42
```

!!! note "Getters need the VM to advance"
    ChucK answers a read by queueing a message the VM picks up on its next
    cycle, so `get_int()` runs the VM briefly to collect the reply. During
    real-time audio the audio thread is already advancing it, so the read
    returns without help. Use `get_int_async()` and friends when you would
    rather supply a callback than block.

Typed accessors give you an attribute-like handle:

```python
freq = chuck.global_float("frequency")
freq.value = 880.0
print(freq.value)
```

## Events

```python
chuck.compile("global Event trigger; while (true) { trigger => now; }")

def on_trigger():
    print("fired")

callback_id = chuck.on_event("trigger", on_trigger)

chuck.signal_event("trigger")       # wake one waiting shred
chuck.broadcast_event("trigger")    # wake all of them

chuck.stop_listening_for_event("trigger", callback_id)
```

## Reading audio mid-graph

`dac` output is what `run()` returns. To read a signal from the middle of the
graph, declare a `global UGen` in ChucK, enable its buffer, and register a tap:

```python
chuck.compile("""
    global SinOsc osc;
    1 => osc.buffered;
    osc => dac;
    while (true) { 1::samp => now; }
""")

chuck.add_tap("osc", num_channels=1, capacity_frames=8192)
samples = chuck.ugen_samples("osc", 1024)     # float32, most recent first-to-last
```

The tap exists because reading a UGen buffer directly while the audio thread
writes it is a data race. Registering one moves the sample fetch onto the audio
thread, where nothing else is writing. During real-time audio an unregistered
read raises rather than returning possibly-spliced data.

## Command-line tools

```bash
numchuck repl                          # interactive REPL
numchuck repl bass.ck melody.ck        # with files loaded
numchuck repl --project my-project     # with file versioning

numchuck edit                          # multi-tab editor
numchuck edit --start-audio --otf      # audio on, OTF listener enabled

numchuck run file.ck                   # execute and exit
numchuck run file.ck --duration 10 --srate 48000

numchuck web                           # browser IDE: serves, then opens it
numchuck web --no-browser              # print the URL instead of opening it

numchuck version                       # numchuck and ChucK versions
numchuck info                          # detailed system info
```

`numchuck web` binds `127.0.0.1`, mints an access token, and opens your browser
on the URL that carries it. The token is required on every request, so a bare
`http://127.0.0.1:8080` typed from memory will not authenticate -- use the URL
it printed. `--token ""` turns auth off, `--host` widens the bind.

Add `--local` to any of these to use a project-local `./.numchuck` directory;
see [User directory](numchuck_home.md) for why that is opt-in.

## Next steps

- [Examples](examples.md) — worked patterns
- [Error handling](error_handling.md) — what raises, and when
- [API reference](api/chuck.md) — generated from the source
