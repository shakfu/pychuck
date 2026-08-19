# Constants

All of these live on the extension module, not the package namespace:

```python
from numchuck._numchuck import PARAM_SAMPLE_RATE, LOG_INFO
```

The shred-watcher flags are the exception — those are re-exported from
`numchuck` itself, since [`Chuck.on_shred`][numchuck.Chuck.on_shred] takes them.

## Parameters

Used with `ChucK.set_param()`, `set_param_float()`, `set_param_string()` and
`set_param_string_list()` on the [low-level class](lowlevel.md). Each constant
is a string key; the value type differs per parameter, which is why there are
four setters.

The high-level [`Chuck`](chuck.md) covers all of these as constructor arguments
and properties, so you rarely need the constants directly.

### Audio

| Constant | Type | Meaning |
| --- | --- | --- |
| `PARAM_SAMPLE_RATE` | int | Sample rate in Hz, e.g. 44100 or 48000 |
| `PARAM_INPUT_CHANNELS` | int | Number of input (adc) channels |
| `PARAM_OUTPUT_CHANNELS` | int | Number of output (dac) channels |
| `PARAM_IS_REALTIME_AUDIO_HINT` | int | Tells the VM whether it is driving real hardware |

### VM

| Constant | Type | Meaning |
| --- | --- | --- |
| `PARAM_VM_ADAPTIVE` | int | Maximum block size for adaptive processing, **not** a flag: any value `<= 1` disables it |
| `PARAM_VM_HALT` | int | Halt the VM when no shreds remain |
| `PARAM_AUTO_DEPEND` | int | Automatic dependency resolution |
| `PARAM_DEPRECATE_LEVEL` | int | How loudly to complain about deprecated syntax (0-2) |
| `PARAM_DUMP_INSTRUCTIONS` | int | Dump generated VM instructions |
| `PARAM_WORKING_DIRECTORY` | str | Directory relative paths in ChucK code resolve against |
| `PARAM_VERSION` | str | ChucK version string (read-only) |

!!! warning "`PARAM_VM_ADAPTIVE` is a size"
    Passing `True` sets it to 1, which ChucK reads as "off" — so adaptive mode
    silently stays disabled. `Chuck(vm_adaptive=True)` translates this for you
    into a real block size; setting the parameter by hand does not.

### Chugins and import paths

| Constant | Type | Meaning |
| --- | --- | --- |
| `PARAM_CHUGIN_ENABLE` | int | Load chugins at all |
| `PARAM_USER_CHUGINS` | list[str] | Explicit paths to individual `.chug` files |
| `PARAM_IMPORT_PATH_SYSTEM` | list[str] | Directories searched for `.chug` files and ChucK modules |
| `PARAM_IMPORT_PATH_USER` | list[str] | User import path |
| `PARAM_IMPORT_PATH_PACKAGES` | list[str] | Package import path |

!!! note "Chugins are native code"
    Anything on these paths is a shared library loaded into the process. That is
    why numchuck ignores a project-local `./.numchuck/chugins` unless you opt in
    with `--local`; see [User directory](../numchuck_home.md).

### On-the-fly programming

| Constant | Type | Meaning |
| --- | --- | --- |
| `PARAM_OTF_ENABLE` | int | Listen for OTF commands (`chuck --add`, `--remove`) |
| `PARAM_OTF_PORT` | int | OTF listener port, default 8888 |
| `PARAM_OTF_PRINT_WARNINGS` | int | Print OTF warnings |

### Terminal output

| Constant | Type | Meaning |
| --- | --- | --- |
| `PARAM_TTY_COLOR` | int | Colourize VM output |
| `PARAM_TTY_WIDTH_HINT` | int | Terminal width, for wrapping |
| `PARAM_COMPILER_HIGHLIGHT_ON_ERROR` | int | Highlight the offending source on a compile error |

## Log levels

Passed to `ChucK.set_log_level()`. Higher is more verbose; each level includes
everything below it.

| Constant | Value | What it adds |
| --- | --- | --- |
| `LOG_NONE` | 0 | Silence |
| `LOG_CORE` | 1 | Core VM messages |
| `LOG_SYSTEM` | 2 | System-level messages |
| `LOG_HERALD` | 3 | Startup banner and announcements |
| `LOG_WARNING` | 4 | Warnings |
| `LOG_INFO` | 5 | Informational messages |
| `LOG_DEBUG` | 6 | Debug detail |
| `LOG_FINE` | 7 | Fine-grained tracing |
| `LOG_FINER` | 8 | Finer still |
| `LOG_FINEST` | 9 | Everything ChucK will say |
| `LOG_ALL` | 10 | Alias for the maximum |

## Shred watcher flags

Combined with `|` and passed as `options` to
[`Chuck.on_shred`][numchuck.Chuck.on_shred]. Re-exported from `numchuck`.

| Constant | Meaning |
| --- | --- |
| `SHRED_WATCH_NONE` | Subscribe to nothing |
| `SHRED_WATCH_SPORK` | A shred was sporked |
| `SHRED_WATCH_REMOVE` | A shred was removed |
| `SHRED_WATCH_SUSPEND` | A shred was suspended |
| `SHRED_WATCH_ACTIVATE` | A shred was activated |
| `SHRED_WATCH_ALL` | All of the above |

```python
import numchuck

chuck.on_shred(
    callback,
    options=numchuck.SHRED_WATCH_SPORK | numchuck.SHRED_WATCH_REMOVE,
)
```
