# Audio

Real-time playback is driven by RtAudio and lives on the low-level extension
module, not on the package namespace:

```python
from numchuck._numchuck import (
    start_audio, stop_audio, shutdown_audio,
    audio_info, is_audio_running, get_audio_meters,
)
```

`start_audio` takes the `ChucK` instance whose VM the audio thread should drive.
From a high-level [`Chuck`](chuck.md), that is `chuck.raw`.

```python
from numchuck import Chuck
from numchuck._numchuck import start_audio, stop_audio, shutdown_audio

chuck = Chuck(input_channels=0, output_channels=2)
chuck.compile("SinOsc s => dac; 440 => s.freq; while (true) { 100::ms => now; }")

start_audio(chuck.raw)
try:
    ...
finally:
    stop_audio()
    shutdown_audio()
```

!!! warning "One instance at a time"
    Only one instance can have real-time audio active in a process. For
    concurrent sound, spork several shreds inside one instance rather than
    creating several instances.

!!! note "`stop_audio()` waits for the audio thread"
    It blocks until the current audio callback returns, which is unbounded if
    the VM is saturated. It releases the GIL while waiting, so other Python
    threads keep running and a supervisor can act, but the call itself can take
    a while under a heavy shred load.

## Functions

::: numchuck._numchuck.start_audio

::: numchuck._numchuck.stop_audio

::: numchuck._numchuck.shutdown_audio

::: numchuck._numchuck.audio_info

::: numchuck._numchuck.is_audio_running

::: numchuck._numchuck.get_audio_meters

## Offline alternative

Real-time audio is not required to produce sound. `Chuck.run()` and the
[rendering helpers](rendering.md) advance the VM synchronously and hand back
samples, which is also what makes ChucK code testable without hardware.

## Global UGen taps

`dac` output is what `run()` returns. Reading a signal from the middle of the
graph means declaring a `global UGen` in ChucK, enabling its buffer, and
registering a tap.

The indirection is not decoration. `Chuck_UGen` keeps an 8192-sample buffer
whose write offset is a plain integer, copied out with no synchronization, so
reading it from Python while the audio thread writes it is a data race —
measured at 831 spliced reads in 274,240, with discontinuities up to nine times
the waveform's own maximum sample-to-sample step. A registered tap is sampled on
the audio thread instead, immediately after the VM returns, and published under
a seqlock. While real-time audio runs, an unregistered read raises rather than
returning data that may be spliced.

```python
chuck.compile("""
    global SinOsc osc;
    1 => osc.buffered;
    osc => dac;
    while (true) { 1::samp => now; }
""")

chuck.add_tap("osc", num_channels=1, capacity_frames=8192)
samples = chuck.ugen_samples("osc", 1024)
```

Multichannel taps return channel-major `(channels, frames)`, matching ChucK's
non-interleaved layout — unlike `run()`, which is interleaved.

See [`Chuck.add_tap`][numchuck.Chuck.add_tap],
[`Chuck.remove_tap`][numchuck.Chuck.remove_tap],
[`Chuck.taps`][numchuck.Chuck.taps] and
[`Chuck.ugen_samples`][numchuck.Chuck.ugen_samples].
