# TODO

- [ ] enable advanced chugins {faust, warpbuf, fluidsynth}
- [x] evaluate and bundle additional chugins from https://github.com/shakfu/my-chugins:
  - **CLAP** -- load CLAP (CLever Audio Plugin) format plugins as ChucK UGens. Requires CLAP SDK.
  - **PdPatch** -- embed Pure Data patches as ChucK UGens. Requires libpd.
  - **VST3** -- load VST3 format plugins as ChucK UGens. Requires VST3 SDK.
  - Note: AbletonLink and AudioUnit from that repo are already bundled.

---

## Real-time Audio: Global UGen Taps

### High Priority

- [ ] **Remove the audio-thread allocation in tap capture** (`src/_numchuck.cpp`, `capture_taps`)
  - ChucK keeps `m_global_ugens` private (`chuck_globals.h:356`) and exposes only
    `getGlobalUGenSamples(const char *, ...)`, so every capture builds a `std::string`
    temporary for the map lookup -- heap-free only when the small-string optimization
    covers the name
  - Bounded in count (one lookup per active tap per block, taps capped at 8) and
    chuck-max's perform routine does the same, but it is still a potentially
    unbounded-latency call on the audio thread
  - Fix: vendored patch under `scripts/patches/` exposing a UGen accessor, resolve the
    `Chuck_UGen *` once in `add_tap()`, then read the buffer directly per block.
    `apply_patches()` in `scripts/update.sh` re-applies it after a chuck update

- [ ] **Run the tap tearing regression test in CI**
  (`tests/test_ugen_tap.py::test_realtime_tap_reads_are_never_torn`)
  - The test is marked `realtime`; every CI job filters with `-k "not realtime"`
    (`.github/workflows/ci.yml:71`, `wheels.yml:72`, `pip-test.yml:47`), so the check
    that catches spliced tap reads never runs there
  - It is the only guard against a regression that was silent in normal use: 0.3% of
    full-ring reads, correct-looking data with a discontinuity in the middle
  - Options: a dummy/virtual audio device on the CI runners, or a harness that drives
    the capture path from a worker thread without real hardware

### Notes

- [x] **Seqlock reader must back off, not spin** (`src/_numchuck.cpp`, `read_tap_snapshot`)
  - The first version retried 256 times with no delay and timed out spuriously: the
    collision check is so cheap that all attempts fit inside the single publish window
    they were waiting on
  - Now waits 200 us between attempts, with the GIL released, over 64 attempts.
    Worth remembering for any future lock-free reader in this codebase

---

## REPL Issues

### High Priority

- [x] **Implement 23 command handlers** (`commands.py`)
  - Waveform: `wave`, `wave on`, `wave off` toggle `session.show_waveform`
  - Recording: `record start/stop/save/discard/status` wired to `SessionRecorder`
  - Playback: `play <name>/pause/resume/stop`, `recordings` wired to `SessionPlayer`
  - MIDI: `midi learn <var> <cc> [ch] [min max]`, `midi list/remove/start/stop/status/monitor` wired to `MIDIMappings` + ChucK code generation
  - OSC: `osc start [port]/stop/status` wired to `OSCServer` + `OSCController`
  - Recording hook in `execute()` captures commands when recording is active

- [x] **Wrap `process_input` in exception handling** (`repl.py`)
  - Both `ChuckREPL.process_input` and `ChuckREPLStdin.process_line` now catch exceptions
  - Errors from `executor.execute()` and `spork_code()` shown as error messages instead of tracebacks

- [x] **Sanitize shell command execution** (`commands.py`)
  - `_cmd_shell` now uses `capture_output=True`, `text=True`, 30s timeout
  - Returns stdout/stderr via `_log()`, reports nonzero exit codes as errors
  - Catches `TimeoutExpired` and `OSError`

### Medium Priority

- [ ] **Guard `get_all_globals()` against segfault** (`completer.py:65-70`, `commands.py:215-226`)
  - Segfaults without audio running; completer silently returns empty
  - Check audio state before attempting global queries

- [ ] **Fix multiline detection for string literals/comments** (`repl.py:387-437`)
  - Substring checks (`"=>" in text`) false-trigger on string literals and comments
  - Use a ChucK-aware lexer pass or at minimum skip strings/comments

- [ ] **Fix completer `start_position` for `?`/`::` suffixes** (`completer.py:203-215`)
  - `start_position=-len(text)` should be `-len(prefix)`, causing incorrect replacement

- [ ] **Fix history file setup order** (`repl.py:377, 440`)
  - `FileHistory(get_history_file())` called before `ensure_numchuck_directories()`
  - Parent directory may not exist yet

- [ ] **Validate `EDITOR` env var in `edit_shred`** (`commands.py:351-389`)
  - Editor binary used directly with no validation or error handling
  - Temp file cleanup is best-effort

- [ ] **Deduplicate window visibility state** (`repl.py:217-225`, `common.py:292-295`)
  - Two independent sets of flags (`show_help_window` vs `show_help`) not synchronized
  - Risks UI state desync

- [ ] **Cap autocomplete results** (`completer.py:165-259`)
  - No result limit; single-character prefix yields all matching ChucK identifiers
  - Cap at ~50 results

### Low Priority

- [ ] **Use `deque` for log trimming** (`repl.py:545-561`, `common.py:534-537`)
  - `list.pop(0)` is O(n) per message; `collections.deque(maxlen=N)` is O(1)

- [ ] **Allow error bar to wrap or grow** (`repl.py:486-493`)
  - `height=D.exact(1)` truncates long compilation errors

- [ ] **Update session source after `edit_shred`** (`session.py:48-85`, `commands.py:351-389`)
  - Replaced shred code not reflected in `session.shreds[id]["source"]`

- [ ] **Document smart enter rules** (`repl.py:383-437`)
  - Multiline logic undocumented; help text and `--no-smart-enter` don't explain actual behavior

- [ ] **Add `--strict` mode for stdin REPL** (`repl.py:84-133`)
  - Currently fail-soft: errors set exit code but processing continues

- [ ] **Break reference cycle in log callbacks** (`common.py:401-413`)
  - `log_callback` closure captures `self`, ChucK holds reference back; use `weakref`

---

## Future Enhancements

### Tooling

- [ ] **LSP server for IDE integration**
  - Language Server Protocol implementation for ChucK
  - Would enable VS Code, Neovim, etc. integration
  - Features: syntax errors, completions, hover docs

### Documentation

- [ ] **Interactive tutorial**
  - Step-by-step livecoding introduction
  - Could be a guided REPL mode or web-based

- [ ] **Cookbook**
  - Common patterns and recipes
  - Examples: FM synthesis, drum machines, effects chains

- [ ] **Video documentation**
  - Screen recordings of livecoding sessions
  - Tutorial videos showing REPL/editor workflows
