# Rendering

One-call helpers for turning ChucK code into audio without managing a VM
yourself. Each creates an instance, compiles, renders and tears down.

All of them return (or write) **interleaved** float32 samples: a stereo render
of `n` frames is a flat array of `n * 2` values ordered `[L0, R0, L1, R1, ...]`.
Reshape with `audio.reshape(-1, channels)` when you want the channels apart.

```python
import numchuck

audio = numchuck.render("SinOsc s => dac; 1::second => now;", duration=2.0)
numchuck.render_file(["bass.ck", "melody.ck"], duration=30.0)
numchuck.to_wav("out.wav", code="SinOsc s => dac;", duration=5.0)
```

::: numchuck.render

::: numchuck.render_file

::: numchuck.to_wav

::: numchuck.RenderError

## Configuration

Settings read from `.numchuck/config.toml`. See
[User directory](../numchuck_home.md) for where that file is found, and note
that a project-local directory is only consulted when opted into.

::: numchuck.Config

::: numchuck.load_config

::: numchuck.get_config

::: numchuck.save_config
