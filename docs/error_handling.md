# Error handling

numchuck raises exceptions rather than returning error codes, with one
deliberate exception: **compilation reports failure through its return value**,
not by raising. That asymmetry is the single most important thing on this page.

Every behaviour documented here was checked against the current build.

## Exception types

| Exception | Raised when | Example |
| --- | --- | --- |
| `ValueError` | An argument is invalid before ChucK is involved | empty code, non-positive frame counts, out-of-range tap capacity |
| `RuntimeError` | An operation failed, or the object is unusable | shred not found, instance already closed, VM not initialized |
| `RenderError` | A one-call render helper could not compile or render | `render("@@@ bad")` |
| `FileNotFoundError` | A `.ck` file passed to a render helper does not exist | `render_file("/nope.ck")` |
| `TypeError` | Wrong type entirely | passing an int where a name is expected |

## Compilation does not raise

`compile()` and `compile_file()` return `(success, shred_ids)`. A syntax error
is a normal, expected outcome for a live-coding tool, so it comes back as
`(False, [])` with ChucK's diagnostics on stderr:

```python
success, shred_ids = chuck.compile("this is not chuck @@@")
# -> (False, [])
```

A missing file is the same:

```python
success, shred_ids = chuck.compile_file("/nope/missing.ck")
# -> (False, [])
```

So checking the flag is not optional:

```python
success, shred_ids = chuck.compile(code)
if not success:
    handle_compilation_failure()      # nothing was raised
```

Capture the diagnostics if you need them in-process:

```python
errors = []
chuck.set_stderr_callback(errors.append)

success, _ = chuck.compile(code)
if not success:
    print("".join(errors))
```

The render helpers do the opposite, because they have no partial-success state
to report:

```python
import numchuck

numchuck.render("@@@ bad", duration=1.0)     # RenderError: Failed to compile code
numchuck.render_file("/nope.ck")             # FileNotFoundError
```

## Invalid arguments

These raise before ChucK sees them:

```python
chuck.compile("")                    # ValueError: Code cannot be empty
chuck.run(0)                         # ValueError: num_frames must be positive
chuck.add_tap("osc", 1, 0)           # ValueError: capacity_frames must be between 1 and 4194304
chuck.add_tap("osc", 1, 2**30)       # ValueError: capacity_frames must be between 1 and 4194304
```

The tap capacity is bounded on purpose: it allocates a ring plus a staging
buffer, so an unchecked large value would ask for tens of gigabytes.

## Missing globals read as zero

Reading a global that was never declared is **not** an error. ChucK creates it
on demand with a zero value:

```python
chuck.get_int("never_declared")      # 0
chuck.get_float("never_declared")    # 0.0
chuck.get_string("never_declared")   # ""
```

Signalling an event nobody declared is equally quiet. If you need to know
whether a name exists, ask for the list:

```python
declared = {name for _type, name in chuck.raw.get_all_globals()}
if "frequency" not in declared:
    ...
```

!!! note "Reads need the VM to advance"
    A read is answered by a callback the VM invokes on its next cycle, so
    `get_int()` runs the VM briefly to collect it. If the callback never fires
    it raises `RuntimeError` suggesting a larger `run_frames`. During real-time
    audio the audio thread is already advancing the VM, so the read returns
    without help.

## Shreds

```python
chuck.shred_info(9999)               # RuntimeError: Shred 9999 not found
chuck.remove_shred(9999)             # returns None -- removing a missing shred is quiet
```

The asymmetry is intentional: asking about a shred that is not there is a
question with no answer, whereas removing one that is already gone has achieved
what you asked for.

## Lifetime

`Chuck` refuses to work after `close()` rather than crashing:

```python
chuck.close()
chuck.compile("SinOsc s => dac;")    # RuntimeError: ChucK instance has been closed
```

Prefer the context manager, which closes for you even when the block raises:

```python
with Chuck(output_channels=2) as chuck:
    chuck.compile(code)
    audio = chuck.run(44100)
```

Explicit teardown matters most on Windows, where audio threads must be joined
before their memory is released.

## The low-level class

`numchuck._numchuck.ChucK` requires `init()` before anything else, and says so:

```python
from numchuck._numchuck import ChucK

chuck = ChucK()
chuck.compile_code("SinOsc s => dac;")
# RuntimeError: ChucK instance not initialized. Call init() first.
```

Its validation is otherwise the same:

```python
chuck.init()
chuck.compile_code("")                 # ValueError: Code cannot be empty
chuck.compile_code("...", "", 0)       # ValueError: Count must be at least 1
```

Buffers must be `float32` and correctly sized, or you get a `ValueError`
naming the mismatch:

```python
import numpy as np
from numchuck._numchuck import PARAM_INPUT_CHANNELS, PARAM_OUTPUT_CHANNELS

frames = 1024
chuck.run(
    np.zeros(frames * chuck.get_param_int(PARAM_INPUT_CHANNELS), dtype=np.float32),
    np.zeros(frames * chuck.get_param_int(PARAM_OUTPUT_CHANNELS), dtype=np.float32),
    frames,
)
```

A bare `ChucK` defaults to two channels each way, so an empty input buffer is a
mismatch, not a shortcut:

```python
chuck.run(np.zeros(0, dtype=np.float32), output, 1024)
# ValueError: input size mismatch: expected 2048 elements, got 0
```

Globals need a *running* VM, not merely an initialized one:

```python
chuck = ChucK()
chuck.init()
chuck.set_global_int("x", 1)
# RuntimeError: ChucK VM is not running: call start() before accessing globals
```

`start()` fixes it, and so does a first `run()`, which starts the VM implicitly.
`Chuck` starts it at construction, so the high-level API never sees this.

!!! note "This used to be a segfault"
    `ChucK::globals()` returns nothing until the VM is running, and the bindings
    called straight through the returned pointer -- so skipping `start()` was a
    null dereference that took the process down with no traceback. Every one of
    those call sites now raises instead.

## Cleaning up listeners

Event listeners live until removed. Keep their ids:

```python
callback_id = chuck.on_event("trigger", handler)
...
chuck.stop_listening_for_event("trigger", callback_id)
```

A shred watcher is one per instance and is unsubscribed on shutdown, so no
notification can arrive after the callable is dropped. Remove it earlier with
`chuck.remove_shred_watcher()`.

## What is not guarded

ChucK code runs with the privileges of the Python process, and nothing sandboxes
it:

- **The filesystem is reachable.** ChucK's `FileIO` reads and writes anything the
  process can.
- **A shred that never advances time blocks the VM.** `Chuck.abort_shred()` is
  the only way to break out of a loop that never reaches `=> now`, and it only
  works while the VM is being driven — so call it from another thread during
  real-time audio.
- **There is no memory ceiling inside the VM.** A spork loop can accumulate
  shreds faster than they retire until the VM saturates.

Do not run untrusted ChucK code.

## Recommended shape

```python
import numchuck
from numchuck import Chuck

def play(code: str, seconds: float = 1.0):
    errors: list[str] = []
    try:
        with Chuck(input_channels=0, output_channels=2) as chuck:
            chuck.set_stderr_callback(errors.append)

            success, shred_ids = chuck.compile(code)
            if not success:
                raise ValueError("compilation failed:\n" + "".join(errors))

            return chuck.run(int(chuck.sample_rate * seconds))
    except RuntimeError as e:
        # VM-level failure: not initialized, operation refused
        raise RuntimeError(f"ChucK VM error: {e}") from e
```

Three habits carry most of the weight: check the compile flag, use the context
manager, and register a stderr callback when you need to know *why* something
failed.
