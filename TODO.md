# TODO

- [ ] enable advanced chugins {faust, warpbuf, fluidsynth}
- [x] evaluate and bundle additional chugins from https://github.com/shakfu/my-chugins:
  - **CLAP** -- load CLAP (CLever Audio Plugin) format plugins as ChucK UGens. Requires CLAP SDK.
  - **PdPatch** -- embed Pure Data patches as ChucK UGens. Requires libpd.
  - **VST3** -- load VST3 format plugins as ChucK UGens. Requires VST3 SDK.
  - Note: AbletonLink and AudioUnit from that repo are already bundled.

---

## Known Crashes

### High Priority

- [x] **Intermittent SIGSEGV on a background thread during ConvRev playback**
  (`tests/test_examples.py::test_chugin_convrev_example`) -- FIXED
  - Root cause: chugins were `dlopen`ed without `RTLD_NODELETE`, so
    `~Chuck_DLL()` unmapped `ConvRev.chug` while the `std::thread` that
    `ConvRev::tick()` spawns per FFT block was still inside
    `FFTConvolver::process()`. See the CHANGELOG entry and
    `scripts/patches/0004-chugin-rtld-nodelete.patch`
  - Measured 7/152 before the fix, 0/400 after
  - Two notes for future crash hunts, both of which cost time here:
    - The `0x03e80002964c` address in the old ASAN report was never a corrupted
      pointer. `faulthandler` re-raises fatal signals with `raise()`, which glibc
      implements as `tgkill()`, so downstream handlers see `si_code == SI_TKILL`
      and an `si_addr` that is really the `si_pid`/`si_uid` pair sharing that
      union -- `0x3e8` is uid 1000, `0x2964c` is pid 169548. Run with
      `-p no:faulthandler` to see the actual fault
    - "Does not reproduce with `test_examples.py` alone (0/25)" did not support
      the conclusion that state from `test_api.py` was required: at the measured
      rate, 0/25 has ~43% probability. It was never an ordering dependency

- [ ] **Stack over-read in the GVerb chugin** (`thirdparty/chugins/GVerb/gverbdefs.h:114`)
  - AddressSanitizer reports `stack-buffer-overflow`, an 8-byte READ of the 4-byte
    stack float `x` in `gverb_do()` (inlined into `GVerb::tick`), ten occurrences per
    run of the suite
  - Real undefined behaviour, but a read of adjacent stack within the same frame, so
    it is not a plausible cause of a segfault and was left alone rather than guessed at
  - Fixing it needs a `scripts/patches/chugins/` patch, as GVerb is vendored upstream

---

## Memory Leaks

### High Priority

- [ ] **Chugin objects are never destroyed when a VM is shut down with live shreds**
  (`thirdparty/chuck/core/chuck_vm.cpp`, `Chuck_VM::shutdown()` / `removeAll()`)
  - A chugin's `CK_DLL_DTOR` runs when its shred *ends on its own* while the VM is
    running, but not when the shred is still alive at teardown. `remove_all_shreds()`
    followed by `shutdown()` never invokes it, so the C++ object the chugin's ctor
    allocated is leaked along with everything it owns
  - Measured with an instrumented ConvRev (an `fprintf` in `convrev_ctor`,
    `convrev_dtor` and `~ConvRev`), creating and tearing down VMs in a loop:

    | teardown path | `convrev_dtor` | RSS per VM |
    | --- | --- | --- |
    | shred ends naturally | fires | ~4.2 MB |
    | shred live at shutdown | never fires | ~23.6 MB |

    so ~19 MB per VM is the un-destroyed ConvRev -- mostly its 5513 FFT partition
    segments. The ~4.2 MB that remains when the dtor *does* run is a separate
    residual leak, not yet chased
  - General to every chugin, not specific to ConvRev; ConvRev is only where it was
    also a crash, because it is the sole bundled chugin that owns a thread, and the
    abandoned object means its `~ConvRev()` join never happens. That crash is fixed
    separately by `scripts/patches/0004-chugin-rtld-nodelete.patch`, which makes the
    orphaned thread survivable -- it does not address this leak
  - Not a use-after-free: because nothing is ever freed, the orphaned worker only
    ever writes to memory that stays allocated. This is why patching ConvRev's
    threading was considered and rejected
  - Ruled out as a workaround: calling `run()` again after `remove_all_shreds()` so
    the VM can process the removal message. The dtor still never fires and the leak
    is unchanged, so removal is not merely deferred
  - Matters for a long-lived host that creates and destroys VMs; harmless for the
    test suite, which exits. `tests/test_examples.py::test_chugin_convrev_example`
    hits it because `examples/convrev/ConvRev.ck` ends in `while(true)`, so its
    shred is always live at teardown

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

- [x] **Run the tap tearing regression test in CI**
  (`tests/test_ugen_tap.py::test_realtime_tap_reads_are_never_torn`)
  - A dedicated `realtime` job in `.github/workflows/ci.yml` loads `snd-dummy`
    and runs `pytest -m realtime` against it. The job asserts the device exists
    before running, so the tests cannot skip themselves into a green run
  - The other jobs still filter `-k "not realtime"`; that is now a division of
    labour rather than a gap

### Notes

- [x] **Seqlock reader must back off, not spin** (`src/_numchuck.cpp`, `read_tap_snapshot`)
  - The first version retried 256 times with no delay and timed out spuriously: the
    collision check is so cheap that all attempts fit inside the single publish window
    they were waiting on
  - Now waits 200 us between attempts, with the GIL released, over 64 attempts.
    Worth remembering for any future lock-free reader in this codebase

---

## REPL Issues

### Resolved in the review pass

- [x] **`clear` failed with no audio running** (`services/shreds.py`)
  - `clear_vm()` posts a CLEARVM message the VM only collects while it is being
    driven, so an offline session got a bare "Failed to clear VM"
  - Now falls back to removing the shreds directly, and
    `test_repl_stdin.py::test_clear_command` is no longer skipped

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

- [x] **Guard `get_all_globals()` against segfault** (`completer.py:65-70`, `commands.py:215-226`)
  - The stated cause was wrong: the trigger is not "no audio running" but "the
    VM was never started". `get_all_globals()` on a `Chuck` that had never run
    segfaulted; after a first `run()` it is fine, which is why `?g` in the REPL
    appeared healthy
  - `Chuck.__init__` now calls `start()` as well as `init()`, so every accessor
    is safe from construction. `test_repl_stdin.py::test_globals_query` runs
    again and `tests/test_api.py::TestGlobalsBeforeAnyRun` covers the rest

- [x] **Raise instead of crashing on globals access before `start()`**
  (`src/_numchuck.cpp`)
  - The earlier diagnosis here was wrong in a useful way: `ChucK::globals()`
    does *not* return non-null in this state. It checks
    `m_carrier->vm->running()` and returns NULL, so every unguarded call site
    was a plain null dereference -- 30 of the 33 had no check at all
  - `require_globals()` now fetches and validates in one place, and all 33 sites
    go through it. It distinguishes "not initialized" from "initialized but not
    started", since the remedy differs
  - Three sites allocated (`Chuck_Msg`, the sample buffer) before the check;
    the check moved ahead of the allocation so a raise cannot leak
  - `get_all_globals()` returned an empty list rather than raising, which said
    "there are no globals" when the truth was "I cannot tell you"; it raises
    like the rest now. Both callers (`completer.py`, `services/globals.py`)
    already caught `RuntimeError`
  - `tests/test_globals_preconditions.py` exercises all 27 reachable bindings in
    both states, plus the started path to show the guard cost nothing

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

- [x] **Documentation build** (`mkdocs.yml`, `Makefile`, `.github/workflows/ci.yml`)
  - The Sphinx tree had no build wiring and had drifted to documenting an API
    that no longer existed. Replaced with MkDocs + mkdocstrings, built by
    `make docs` under `--strict` and gated in CI
  - Remaining: publish it. `make docs-deploy` runs `mkdocs gh-deploy`, but
    GitHub Pages is not enabled for the repository and no workflow publishes on
    a tag

- [ ] **Interactive tutorial**
  - Step-by-step livecoding introduction
  - Could be a guided REPL mode or web-based

- [ ] **Cookbook**
  - Common patterns and recipes
  - Examples: FM synthesis, drum machines, effects chains

- [ ] **Video documentation**
  - Screen recordings of livecoding sessions
  - Tutorial videos showing REPL/editor workflows
