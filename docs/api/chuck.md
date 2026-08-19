# Chuck

The high-level wrapper, and the class most code should use. It owns a
[`ChucK`](lowlevel.md) instance, exposes its parameters as properties, returns
NumPy arrays from the audio calls, and cleans up on context-manager exit.

```python
from numchuck import Chuck

with Chuck(sample_rate=48000, input_channels=0, output_channels=2) as chuck:
    chuck.compile("SinOsc s => dac; while (true) { 1::samp => now; }")
    audio = chuck.run(48000)
```

::: numchuck.Chuck

## Shred

Returned by [`Chuck.spork`][numchuck.Chuck.spork] and
[`Chuck.spork_file`][numchuck.Chuck.spork_file]. A handle on one running shred.

::: numchuck.Shred

## Typed global accessors

Returned by `Chuck.global_int()`, `global_float()` and `global_string()`. Each
reads and writes one ChucK global through a `value` property, which saves
repeating the variable name on every access.

```python
freq = chuck.global_float("frequency")
freq.value = 880.0
```

::: numchuck.GlobalInt

::: numchuck.GlobalFloat

::: numchuck.GlobalString
