# Low-level ChucK

`numchuck._numchuck.ChucK` is the nanobind binding, mirroring ChucK's own C++
API. The high-level [`Chuck`](chuck.md) holds one and delegates to it; reach for
this directly only when the wrapper does not expose what you need.

```python
from numchuck._numchuck import ChucK, PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS

chuck = ChucK()
chuck.set_param(PARAM_SAMPLE_RATE, 44100)
chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
chuck.init()
chuck.start()
```

An existing wrapper hands you the same object without a second VM:

```python
from numchuck import Chuck

wrapper = Chuck()
raw = wrapper.raw          # the underlying ChucK
```

## Differences from `Chuck`

| | `Chuck` | `ChucK` |
| --- | --- | --- |
| Construction | keyword arguments, initialized | `set_param()` with constants, then `init()` |
| Audio buffers | returns a fresh NumPy array | you pass in `input` and `output` arrays |
| Globals | `set_int` / `get_int`, blocking reads available | `set_global_int` / `get_global_int`, callback-only reads |
| Cleanup | `close()`, or context manager | destructor |

The buffer difference is the one that bites: `ChucK.run(input, output, frames)`
writes into arrays you allocate, and both must be `float32`.

```python
import numpy as np
from numchuck._numchuck import PARAM_INPUT_CHANNELS, PARAM_OUTPUT_CHANNELS

frames = 1024
in_channels = chuck.get_param_int(PARAM_INPUT_CHANNELS)
out_channels = chuck.get_param_int(PARAM_OUTPUT_CHANNELS)

chuck.run(
    np.zeros(frames * in_channels, dtype=np.float32),
    np.zeros(frames * out_channels, dtype=np.float32),
    frames,
)
```

Both buffers are `frames * channels` and interleaved. A bare `ChucK` defaults to
two channels each way, so the input buffer may not be empty unless you set
`PARAM_INPUT_CHANNELS` to 0 -- a size mismatch raises `ValueError` naming the
count it wanted.

## Preconditions the wrapper handles for you

```python
chuck.init()
chuck.start()          # required before any global access
```

`ChucK::globals()` returns nothing until the VM is *running*, so every
`set_global_*` / `get_global_*` call, the event methods and `clear_vm()` need
`start()` first -- or a first `run()`, which starts it implicitly. Skipping it
used to segfault; it now raises a `RuntimeError` naming the missing step.

::: numchuck._numchuck.ChucK

## Module functions

::: numchuck._numchuck.version
