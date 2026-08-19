# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Commons Changelog](https://common-changelog.org). This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Types of Changes

- Added: for new features.
- Changed: for changes in existing functionality.
- Deprecated: for soon-to-be removed features.
- Removed: for now removed features.
- Fixed: for any bug fixes.
- Security: in case of vulnerabilities.

---

## [Unreleased]

### Security

- **The web IDE bound every interface with no authentication** (`src/_web.cpp`, `web/__init__.py`, `cli/main.py`): `mg_http_listen` was called with a hardcoded `http://0.0.0.0:<port>`, and there was no token, no origin check and no `--host` flag -- while the CLI printed `http://localhost:<port>`, understating the exposure. Since `POST /api/compile` runs arbitrary ChucK, and ChucK's standard library includes `FileIO`, anyone who could reach the port could read and write files as the user; the WebSocket REPL additionally exposed `spork_file` and `replace_shred_file` against arbitrary paths. Confirmed against a running instance. The listen address is now a property defaulting to `127.0.0.1`, `numchuck web` gained `--host`, and any non-loopback bind is issued a random token automatically (`secrets.token_urlsafe`, 24 bytes) unless the caller passes one or explicitly waives it with `--token ""`. The token is required on every `/api/` request and on the WebSocket upgrade, accepted as `Authorization: Bearer` or `?token=` (browsers cannot set headers on a WebSocket handshake), and compared without an early exit on the first differing byte so response latency does not leak it a character at a time. `WebChuckServer.url` carries the token, and the CLI warns when bound wide.

- **`numchuck web` now serves and opens the IDE in one step, authenticated** (`cli/main.py`, `web/__init__.py`): the command already opened a browser, but only a non-loopback bind was issued a token, so the default run opened an unauthenticated page. That left a real hole: the origin check constrains browsers, but it only applies to requests that carry an `Origin`, and a local process sends none -- confirmed by an unauthenticated `POST /api/compile` from a plain HTTP client, which compiled and ran ChucK. On a shared machine that is every other user on the box. A token is now minted for every bind, loopback included, and the CLI prints and opens the URL carrying it -- the same model Jupyter uses for a localhost bind. `--token ""` still waives auth deliberately, and now says so loudly. The CLI also reports when it could not open a browser instead of appearing to do nothing.

- **Browsers served a cached page from a different server on the same port** (`src/_web.cpp`): no response carried a `Cache-Control` header, so browsers fell back to heuristic caching (RFC 9111 4.2.2) and could reuse a response without revalidating. A loopback port is shared ground -- every local tool wants 8080 -- so this meant a document cached for an unrelated server on `127.0.0.1:8080` could be served in place of the IDE. Reported as "the frontend only works in Chrome": Safari was rendering a cached llama.cpp UI on numchuck's port, whose JS then called llama.cpp endpoints and reported "Server unavailable: 404 Not Found". Every response -- documents, static assets, JSON, and the 401/403/404 refusals -- now carries `Cache-Control: no-store`. VM state was never cacheable either, so the API needed this regardless.

- **The web IDE lost its token in a new tab, and threw on copy/paste outside a secure context** (`web/static/index.html`): two cross-browser defects, both found while investigating a report that the frontend only worked in Chrome. The token was kept in `sessionStorage`, which is per-tab, so opening the IDE in a second tab authenticated nothing and its WebSocket closed immediately; it now uses `localStorage`, and a 401 discards the stored token so a stale one from an earlier run cannot wedge later loads. Separately, the REPL key handler called `navigator.clipboard` unguarded, and that API does not exist outside a secure context -- which any non-loopback bind is -- so Ctrl+C, Ctrl+X and Ctrl+V raised `TypeError`; both paths are now feature-detected with a fallback. Neither defect was browser-specific: the IDE was verified end to end in Chromium, Firefox and WebKit, and both bugs reproduced identically in all three.

- **The bundled web IDE did not send the auth token** (`web/static/index.html`): the server enforced the token but the shipped page never presented one, so the IDE worked on loopback and was broken in exactly the configuration that requires auth -- every API call would have answered 401 and the WebSocket upgrade would have been refused. The page now takes the token from the `?token=` the CLI opens it with, keeps it in `sessionStorage` so a reload does not lose it, and clears it from the address bar with `history.replaceState` so it does not linger in history or a screenshot. API calls carry it as `Authorization: Bearer`; the WebSocket URL carries it as a query parameter, since browsers cannot set headers on a handshake. A 401 or 403 is now reported in the console instead of the call silently doing nothing, and the socket scheme follows the page protocol rather than being hardcoded to `ws://`. Static files are deliberately still served without a token, because the page has to load before it can read one. Covered by raw WebSocket handshake tests and by a contract test asserting the shipped asset satisfies what the server enforces -- the gap existed because every other test drove the API directly rather than through the page.

- **Cross-site WebSocket hijacking** (`src/_web.cpp`): `mg_ws_upgrade` was called with no `Origin` validation. WebSocket connections are not subject to the same-origin policy, so any page the user happened to visit while the IDE was running could open `ws://localhost:8080/ws` and drive the REPL -- which meant a loopback-only bind would not have been sufficient on its own. Every request carrying an `Origin` is now checked against its own `Host` header and refused with 403 on a mismatch, across the API, the static files and the upgrade. Comparing the request against itself rather than against a configured address needs no configuration and works identically for loopback, LAN-IP and hostname binds. Requests with no `Origin` (curl and other non-browser clients) are allowed; `Origin: null`, which is what sandboxed iframes and `file://` pages send, does not match a `Host` and is refused.

- **A project-local `.numchuck` loaded native code without asking** (`paths.py`, `api.py`, `cli/main.py`): `get_numchuck_dir()` preferred `./.numchuck` whenever it existed, and `Chuck.__init__` independently added `./.numchuck/chugins` to the chugin search path. Chugins are native shared libraries loaded into the process, so cloning a repository and running numchuck inside it executed whatever native code that repository shipped, with no prompt and nothing printed. The local directory is now opt-in via `--local` (on `edit`, `repl`, `run`, `watch` and `web`) or `NUMCHUCK_LOCAL=1`; `enable_local_dir()` and `get_local_numchuck_dir()` expose the switch, and `Chuck.__init__` consults it before adding the local chugin path.

- **OSC server defaulted to all interfaces** (`osc.py`, `constants.py`): `OSCServer.host` defaulted to `0.0.0.0`, and `OSCController` maps incoming messages straight onto global writes and event signals, so the default handed VM control to anything on the network. It now defaults to `DEFAULT_OSC_HOST` (`127.0.0.1`); pass `host="0.0.0.0"` deliberately to accept messages from other machines.

### Fixed

- **Globals access on a VM that was not running segfaulted** (`src/_numchuck.cpp`): `ChucK::globals()` returns NULL until the VM is *running*, not merely initialized -- it checks `m_carrier->vm->running()` before handing back the manager. Thirty of the thirty-three binding call sites called straight through the returned pointer, so any `set_global_*`, `get_global_*`, event or VM-message call on a VM that had been `init()`'d but never `start()`'d was a plain null dereference: SIGSEGV, no traceback, nothing the caller could catch. A binding should not be able to take the process down. `require_globals()` now fetches and validates in one place and every site goes through it, raising a `RuntimeError` that distinguishes "not initialized" from "initialized but not started" because the remedy differs. Three sites allocated before the check ran (a `Chuck_Msg`, the sample buffer in `get_ugen_samples`); the check moved ahead of the allocation so raising cannot leak. `get_all_globals()` previously soft-failed to an empty list, reporting "there are no globals" when the truth was "I cannot tell you", and now raises like the rest -- both in-tree callers already caught `RuntimeError`. Regression tests exercise all 27 reachable bindings in both states.

- **Global access on a freshly constructed `Chuck` segfaulted** (`api.py`): every global accessor reaches into the VM's globals manager, which cannot be used on a VM that has never been started -- and `run()` was the only thing that started one implicitly. So `Chuck().set_int("x", 1)`, `Chuck().get_int("x")`, `Chuck().signal_event("e")` and `chuck.raw.get_all_globals()` all took the process down with SIGSEGV before any audio was rendered, which is the first thing a reader of the documentation would try. `Chuck.__init__` now calls `start()` alongside `init()`. Found while verifying the documentation examples against the build. The low-level `ChucK` still requires `start()` (or a first `run()`) before any `set_global_*`/`get_global_*` call and still crashes rather than raising if you skip it; the binding has 33 such call sites and guarding them is tracked separately in `TODO.md`. Regression tests cover the accessors that used to crash.

- **`WebChuckServer.stop()` deadlocked the interpreter** (`src/_web.cpp`): `WebServer::stop()` joined the server thread while the calling Python thread still held the GIL, and that thread blocks on `nb::gil_scoped_acquire` before every API callback -- so neither side could proceed. The freeze was total and unrecoverable: no other Python thread ran, so not even a watchdog could observe it, and `KeyboardInterrupt` could not be delivered. It reproduced on the first stop whenever any other Python work was runnable alongside an in-flight request; a single-threaded test passes either way, which is why the existing coverage missed it. `start()` and `stop()` now release the GIL around the condition-variable wait and the join. `PyGILState_Check` is outside the stable ABI this extension targets, so the release is unconditional, and the invariant that makes it safe -- every path into `start`/`stop` comes from a bound method or the nanobind type destructor, both of which hold the GIL, while the server thread calls neither -- is documented at the call site. Verified over 20 stop-under-traffic cycles.

- **Blocking audio teardown held the GIL** (`src/_numchuck.cpp`): `start_audio`, `stop_audio` and `shutdown_audio` waited on the audio thread with the GIL held. Under a workload that saturates the VM this froze the whole interpreter rather than merely being slow. Measured with a spork storm (~30,000 sporks/sec, 22,406 shreds resident and not draining): `stop_audio()` takes 45.5s, because the shreduler's sorted insert is linear in the pending set and the audio callback grows correspondingly expensive. That part is the VM being overwhelmed by a pathological workload, not a defect -- but holding the GIL across the wait turned it into a hang that could not be observed, interrupted or diagnosed from inside Python. All three now carry `nb::call_guard<nb::gil_scoped_release>`; nothing in them touches Python state. The wait can still be long, but other threads keep running and a supervisor can act.

- **`clear` failed in a session with no audio running** (`services/shreds.py`): `clear_vm()` posts a `CK_MSG_CLEARVM` message that the VM only collects while it is being driven -- during real-time audio, or inside `run()`. Offline, the message was never collected and the REPL reported a bare "Failed to clear VM" for what is an ordinary offline session. `ShredService.clear_vm()` now falls back to `remove_all_shreds()`, which is a direct call, and logs that it did. `tests/test_repl_stdin.py::test_clear_command` is no longer skipped.

- **Web API reported failures as HTTP 200** (`src/_web.cpp`, `web/__init__.py`): every API response was replied with a hardcoded 200, so a client checking status codes treated `{"error": ...}` as success. The Python handler now returns `(status, body)` and the C++ layer uses it. Related fixes in the same path: a non-numeric shred id in `/api/shred/<id>` raised an uncaught `ValueError` and surfaced as 500, and is now a 400 naming the offending value; unknown endpoints are 404 rather than 200; a missing API handler is 503; and error text is JSON-escaped in C++ instead of being concatenated into a string literal, where a quote or backslash in an exception message produced a document the browser could not parse.

- **A second web server displaced the first** (`src/_web.cpp`): the mongoose event handler dispatched through a single process-wide `g_server` pointer, so constructing a second `WebServer` took over the first's connections, and stopping either cleared the pointer for both. The listening connection now carries `this` as `fn_data`, which mongoose copies onto every accepted connection, and the global is gone. Covered by a test that runs two servers with different tokens and checks each rejects the other's.

- **cibuildwheel built cp39 wheels the package rejects** (`pyproject.toml`): the build list was `cp39-* ... cp313-*` while `requires-python` is `>=3.10`, so a cp39 wheel would be built and then refused at install time. Narrowed to `cp310-*` through `cp313-*`.

- **`make` produced archives with a stale version** (`Makefile`): `VERSION` was restated as `0.1.9` while the package was at `0.2.1`, and it feeds `DIST_NAME`. It is now read from `src/numchuck/_version.py`.

- **Unbounded tap allocation** (`src/_numchuck.cpp`): `add_tap` checked that `capacity_frames` was positive but had no upper bound, and allocates ring plus staging, so `add_tap("x", 8, 2**30)` asked for roughly 64 GB. Capped at `CK_TAP_MAX_CAPACITY` (2^22 frames), which raises instead of hanging or being OOM-killed.

### Changed

- **The web IDE runs the same command executor as the TUI** (`web/__init__.py`): the browser REPL carried its own if/elif dispatcher over the same parsed `Command` objects as `tui.commands.CommandExecutor`, and called the `Chuck` wrapper directly instead of going through the services layer that exists for exactly this. The two had drifted: `shell`, `watch`, `record`, `midi`, `osc` and `recordings` all parsed cleanly in the browser and then fell through to "Unknown command". `WebChuckServer` now builds a `ChuckSession` and a `CommandExecutor` over shared `ShredService` and `GlobalsService` instances, capturing executor output per-thread (`threading.local`) so a command can return what it printed. The module lost roughly 150 statements and the REST endpoints moved onto the same services, so the API and the REPL act on one session rather than two.

  The one deliberate difference is now explicit rather than accidental. `_DENIED_COMMANDS` names the commands the browser must not reach and why: those that start a process on the server host (`shell`, `edit_shred`, `open_editor`) and those that only terminate at a terminal (`watch`, an infinite loop broken by `KeyboardInterrupt`, which would have pinned mongoose's single-threaded event loop forever). A test derives that hazard set from the executor's own source and fails if anything new is missing from the list.

- **Shred listing reconciles with the VM only while the VM is running** (`web/__init__.py`): a spork is a queued message, so with no audio running the VM's shred-id list stays empty. Syncing the session against it unconditionally discarded every shred the session legitimately knew about, making `/api/status` disagree with the REPL's own listing. `sync_shreds()` is now called only when audio is running, which is when the VM's list is meaningful.

- **Four latent CI defects, exposed by turning CI back on** (`.github/workflows/ci.yml`, `pyproject.toml`): re-enabling the workflows surfaced problems that had been invisible while nothing ran.

  *Missing link dependency.* Every Linux job died at `cannot find -lsndfile`. Only the cibuildwheel path installed `libsndfile1-dev`; the five jobs in `ci.yml` did not. `wheels.yml` already had it, which is why wheel builds worked and tests never had.

  *A step that failed whenever the tests passed.* "Verify clean exit" assigned `exit_code` only on failure, then compared the unset variable against `"0"` -- so a successful run compared `""` against `"0"`, took the failure branch, and printed `Tests failed with exit code ` with nothing after it. All four macOS jobs failed this way while reporting 1134 passed. The step also re-ran the entire suite, which the preceding step already does: a `run:` step fails on any non-zero exit, including a crash during interpreter teardown, which is what it was guarding. Removed rather than repaired.

  *Lint rules that only existed on the runner.* The lint job passed `--select E,F,W,I` on the command line while `make lint` ran bare `ruff check`, which uses ruff's smaller default set. Import sorting was therefore enforced only in CI, where 26 violations appeared that no local command would report. The rules now live in `[tool.ruff.lint]` in `pyproject.toml` and both invocations inherit them; a `make lint-check` target runs exactly what CI runs. The 26 violations are fixed.

  *An audio device the runners cannot provide.* The `realtime` job loaded `snd-dummy`, which the Azure runner images have no kernel modules for. It now tries `snd-dummy`, falls back to a PulseAudio null sink (no kernel support needed), and reports which route worked. If neither is available it emits a warning annotation and skips the test step rather than failing the build on a runner limitation -- loud about not having tested rather than quietly appearing to.

- **CI runs again, and can fail** (`.github/workflows/`): all three workflows were `workflow_dispatch`-only, with the real triggers commented out, so nothing ran on push, pull request or tag. Restored `push`/`pull_request` on `ci.yml` and the `v*` tag trigger on `wheels.yml`. The lint job had `continue-on-error: true` on both its steps and so could not fail a run; removed. `mypy` was installed in the lint job and never invoked; it now runs `--strict` in a dedicated `typecheck` job that builds the extension first, which it needs. `submodules: recursive` was dropped from all three workflows -- `thirdparty/` is vendored and there is no `.gitmodules`, so the setting was inert and implied otherwise.

- **Documentation corrected against the tree** (`docs/architecture.md`, `CLAUDE.md`, `README.md`): the architecture file structure predated `services/`, `web/`, `midi.py`, `osc.py`, `recorder.py`, `render.py`, `watcher.py` and `config.py`, and pointed at `tui/chuck_lexer.py` and `tui/paths.py`, which have moved to `lang/lexer.py` and the package root. Its security section now describes the web trust model, the local-directory opt-in and the OSC default rather than a generic "no sandboxing" note. `CLAUDE.md` and `docs/architecture.md` described `thirdparty/` as git submodules; it is vendored. The README documents the web IDE's trust model beside the commands that launch it, and the user-directory section reflects that the local directory is opt-in.

### Added

- **Documentation moved from Sphinx to MkDocs, and wired to a build** (`mkdocs.yml`, `docs/`, `Makefile`, `.github/workflows/ci.yml`): the Sphinx tree under `docs/api/` had no build wiring at all -- no `docs` target, no CI job, no Read the Docs config -- so nothing had ever checked whether it built, and it had drifted badly. It documented `numchuck.ChucK`, `numchuck.PARAM_SAMPLE_RATE`, `numchuck.start_audio()` and friends, none of which exist at those paths: the low-level class and the constants live on `numchuck._numchuck`, `start_audio` takes the instance as its first argument, and the high-level `Chuck` that `__init__.py` recommends was barely covered. Every autosummary entry in `index.rst` named a missing attribute.

  Now MkDocs with the Material theme and `mkdocstrings`, which introspects both the pure-Python package and the compiled extension for docstrings. `make docs` builds, `make docs-serve` previews, `make docs-deploy` publishes, `make qa` includes the build, and a CI job runs it. Everything runs with `--strict`, so a broken cross-reference or a page missing from the nav fails rather than shipping a dead link -- which immediately caught a stale source link in `numchuck_home.md` and a symbol documented on two pages.

  The prose was rewritten against the real API rather than transliterated, and every example was executed against the build before being committed. That turned up the array-shape claim (`run()` returns flat interleaved samples, not `(frames, channels)`) and the segfault recorded under Fixed. The existing developer notes in `docs/` -- architecture, chugins, the fix write-ups -- join the same site under a Development section instead of being markdown nobody rendered. `docs/numchuck_home.md` was corrected too: it documented a `numchuck.cli.paths` module that does not exist (it is `numchuck.paths`), and described `config.toml` as a planned feature.

- **`thirdparty/VERSIONS.md`**: vendoring left no record of where each tree came from. This file names the upstream, the version recoverable from the source, and the local patches, and flags what cannot be recovered -- the upstream commits predate the file, so the ref column is to be filled in on the next `scripts/update.sh` run, which prints the SHA of each clone it makes. It also records two things worth attention: mongoose is pinned at 7.9 and is the only vendored component that parses untrusted input from a socket, and ChucK is a `-dev` snapshot rather than a release.

- **Real-time tests run in CI** (`.github/workflows/ci.yml`): the tap seqlock is the most intricate code in the project and its only regression test is marked `realtime`, which every CI job filtered out -- so it ran nowhere but a developer's machine. A `realtime` job loads `snd-dummy` on the Ubuntu runner and runs `pytest -m realtime` against it. The job asserts the device exists before running, so the tests cannot skip themselves into a green run that checked nothing.

- **`AudioService.sync_state()`** (`services/audio.py`): the service tracked a private `_running` flag, but audio can be started or stopped without going through it -- the REPL command executor calls `start_audio()`/`stop_audio()` directly -- so `is_running` went stale for any front-end mixing the two paths, and `stop()` would short-circuit on it. `sync_state()` reconciles the flag with `is_audio_running()` and returns the result.

- **Web security and REPL test suites** (`tests/test_web_security.py`, `tests/test_web_repl.py`): 58 tests covering bind address and loopback classification, token issuance and enforcement, the Origin/Host check, API status codes, JSON-validity of error bodies, teardown with requests in flight, two servers coexisting, the deny-list's completeness against the executor, and the commands that used to fall through to "Unknown command". Coverage of `web/__init__.py` went from 20% to 60%, over a module that also shrank by a quarter.

### Removed

- **The Sphinx documentation tree** (`docs/api/conf.py`, `docs/api/requirements.txt`, `docs/api/*.rst`): replaced by the MkDocs site described under Added. Nothing referenced the removed files, and no build had ever consumed them.

- **`paths.get_themes_dir()` and `paths.get_keybindings_dir()`**: neither had a caller outside `tests/test_paths.py`. Themes and keybindings are configured through `config.toml`, not by scanning a directory, so these were dead API whose passing tests implied otherwise. The directories are still created by `ensure_numchuck_directories()`, which now works from a single `NUMCHUCK_SUBDIRS` declaration rather than restating the layout. `config.get_config_path()` was a second, disagreeing definition of the config location and now delegates to `paths.get_config_file()`.

## [0.2.1]

### Added

- **Global UGen sample tap** (`src/_numchuck.cpp`, `api.py`): `ChucK.get_ugen_samples(name, num_frames, num_channels=1)` and `Chuck.ugen_samples(...)` read the most recent samples from a named `global UGen`, which taps audio mid-graph rather than the summed dac output that `run()` returns. Returns a float32 array, 1-D for mono and channel-major `(channels, frames)` otherwise, matching ChucK's non-interleaved multichannel layout. The ChucK side must enable buffering first (`1 => tap.buffered;`), otherwise ChucK fills the buffer with zeros.

- **Race-free tap capture during real-time audio** (`src/_numchuck.cpp`, `api.py`): `add_tap(name, num_channels, capacity_frames)`, `remove_tap(name)` and `list_taps()`, with `Chuck.add_tap()` / `remove_tap()` / `taps`. Reading a UGen buffer from Python while the audio thread writes it is a data race -- `Chuck_UGen` keeps an 8192-sample `AccumBuffer` whose write offset is a plain integer and whose `get_most_recent()` memcpy's with no synchronization. Measured on a pure sine: 831 of 274,240 reads of the full ring came back spliced (0.3%), with discontinuities up to 9x the waveform's own maximum sample-to-sample step; smaller reads had ring headroom and showed none. A registered tap is instead sampled on the audio thread immediately after `chuck->run()` returns, when nothing else is writing, and appended to a per-tap ring published under a seqlock, so the audio thread never blocks and a colliding reader retries rather than returning spliced data. The same measurement through a tap: zero torn reads in 1.2 million. Taps also accumulate history across callbacks, so reads are not limited to one audio block. While real-time audio is running, reading an unregistered UGen now raises with a message pointing at `add_tap()` instead of silently returning possibly-torn data; offline reads are unchanged, since the VM only advances inside `run()`, which holds the GIL.

- **Abort the running shred** (`src/_numchuck.cpp`, `api.py`): `ChucK.abort_current_shred()` and `Chuck.abort_shred()` flag the shred currently executing in the VM. This is the only way to break out of a shred stuck in a loop that never advances time, which `remove_shred` cannot reach. The VM only has a current shred while inside a compute cycle, so this applies during real-time audio, called from another thread; it returns `False` when there is nothing to abort.

- **Shred lifecycle watcher** (`src/_numchuck.cpp`, `api.py`, `__init__.py`): `ChucK.subscribe_shred_watcher(callback, options)` / `remove_shred_watcher()` and `Chuck.on_shred(callback)` deliver `(code, shred_id, name)` as shreds are sporked, removed, suspended or activated, replacing the need to poll `get_all_shred_ids()`. Subscription flags `SHRED_WATCH_SPORK`, `_REMOVE`, `_SUSPEND`, `_ACTIVATE`, `_ALL` and `_NONE` are exported from the package. One watcher per instance; it is unsubscribed on shutdown so no notification can arrive after the Python callable is dropped.

- **Indexed and associative global array getters** (`src/_numchuck.cpp`, `api.py`): `get_global_int_array_value`, `get_global_float_array_value`, `get_global_associative_int_array_value` and `get_global_associative_float_array_value` complete the array API, whose setters already existed -- values written by key from Python could not previously be read back, since an associative array has no whole-array fetch. The high-level `Chuck` class gained a global-array section covering whole arrays, elements by index and entries by key (`set_int_array`/`get_int_array`, `set_int_array_value`/`get_int_array_value`, `set_assoc_int`/`get_assoc_int`, and float equivalents).

- **Runtime adaptive block size** (`src/_numchuck.cpp`, `api.py`): `ChucK.set_adaptive(max_block_size)` / `get_adaptive()` and `Chuck.set_adaptive()` / `Chuck.adaptive` read and change the shreduler's adaptive block processing on a running VM. Guarded on both sides: UGens allocate their vectorized buffers when they are created (the dac, adc and bunghole during VM init), so enabling adaptive mode on a VM that started non-adaptive would run the vectorized code path over buffers that were never allocated -- a segfault -- and raising the size past what init allocated overruns them. The binding raises `RuntimeError` and `ValueError` respectively instead.

- **Richer shred metadata** (`src/_numchuck.cpp`): `get_shred_info` now also reports `is_blocked` (waiting on an event), `wake_time`, `start` and the shred's `args`.

### Fixed

- **`vm_adaptive=True` silently did nothing** (`api.py`, `constants.py`): `PARAM_VM_ADAPTIVE` is a maximum block size, not a flag, and ChucK treats any value `<= 1` as off -- so passing `True` set it to 1 and left adaptive mode disabled. `Chuck(vm_adaptive=...)` now accepts a block size directly, with `True` selecting `DEFAULT_ADAPTIVE_BLOCK_SIZE` (512), and the `vm_adaptive` property reports whether the size actually enables the mode.

- **A new ChucK instance inherited a destroyed one's taps** (`src/_numchuck.cpp`): Tap slots are keyed by the instance pointer, and the allocator hands a destroyed instance's address straight to the next one. An instance released by the garbage collector never runs the shutdown path that deactivates its slots, so its registrations outlived it and were adopted by whichever instance landed on that address -- measured at 18 of 20 attempts. `list_taps()` reported a tap the caller never registered, and during real-time audio `get_ugen_samples()` would have served that stale ring instead of refusing the read. Construction now releases everything keyed to the address it claims, and `init()` does the same for the shred watcher, which is keyed by the VM pointer and equally reusable. The tap slot's owner became atomic, since it is now cleared while the audio thread may be scanning slots. Caught by the wheel-build CI on macOS x86_64 and Linux, where the test filter changed the allocation pattern enough to reuse an address and a tap leaked from one test surfaced as a stale name several tests later; it did not reproduce on an unfiltered local run. The pointer-keyed chout/cherr maps are cleared by the same path; they were stale but unreachable, because their C++ hook has to be installed on each instance separately. Regression test asserts no instance inherits a tap across 20 create/destroy cycles, without depending on test ordering.

## [0.2.0]

### Changed

- **Upgraded ChucK core to 1.5.5.9-dev (chai)** (`thirdparty/chuck/`): Updated the vendored ChucK to the current development build. Required one binding-level adjustment, noted under Fixed below.

- **Pinned PdPatch's libpd dependency to a release tag** (`thirdparty/chugins/PdPatch/CMakeLists.txt`): The `FetchContent_Declare` for libpd now pins `GIT_TAG 0.16.0` (with `GIT_SHALLOW TRUE`) instead of tracking the moving `master` branch. libpd 0.16.0 bundles pure-data 0.56-3 via its pinned submodule. This makes the build reproducible and fixes a configure-time failure where `master` advancing upstream left the cached libpd checkout dirty and blocked the FetchContent git update step.

### Fixed

- **Wheels rejected by PyPI's RECORD check: directory entries in the archive** (`scripts/repair_wheel.py`, `scripts/check_wheel_record.py`): Built wheels contained ZIP directory entries (`numchuck/`, `numchuck/tui/`, ...) that were also listed in RECORD with the empty-content hash. They pass a naive hash comparison (and did pass the existing validators, `twine check`, and `check-wheel-contents`), but PyPI's stricter parser rejects them as "file contents do not match RECORD". `repair_wheel.py` now strips directory entries while repacking so wheels contain only files, and both `repair_wheel.py` and `check_wheel_record.py` now hard-fail on any directory entry in the ZIP or RECORD -- closing the validation gap that let this reach PyPI. (The directory entries originate from `scikit-build-core`; the repair-layer strip makes the output canonical regardless of build-backend version. Already-uploaded files can remain as-is per PyPI; the fix applies to future uploads.)

- **Windows access violation on teardown, regressed by the ChucK update** (`thirdparty/chuck/core/chuck.cpp`, `scripts/update.sh`, `scripts/patches/`): The ChucK core update overwrote vendored source and dropped the numchuck local patch that adds a 50ms post-stop delay in `ChucK::shutdown()` for Windows (WASAPI/DirectSound threads need time to terminate before memory is freed; see `docs/windows_fix.md`). Without it, CI crashed with `0xC0000005` (exit 3221225477) during garbage-collection of `Chuck` instances between tests. Restored the delay, and added `scripts/patches/0001-windows-shutdown-delay.patch` plus an `apply_chuck_patches` step in `update.sh` that re-applies local chuck patches after every update and hard-fails if one no longer applies -- so this cannot silently regress again.

- **Build break after ChucK core update: `ChucK::shutdown()` is now protected** (`src/_numchuck.cpp`): The update reverted numchuck's local patch that had made `shutdown()` public (upstream keeps it protected; it is invoked by `~ChucK()`). Rather than re-patch the header, the binding's `shutdown` method no longer calls it directly and instead only clears the Python-side chout/cherr and instance callbacks. VM teardown happens when the high-level `Chuck.close()` drops its sole reference to the instance, triggering the destructor -- preserving the prior teardown order (callbacks cleared before VM shutdown), and the restored 50ms delay still runs via the destructor on both the explicit-close and garbage-collection paths.

## [0.1.11]

### Added

- **OTF shred tracking** (`session.py`, `common.py`, `repl.py`, `editor.py`): Shreds added or removed via on-the-fly programming (`chuck --add`, `chuck --remove`) are now automatically tracked in the REPL and editor. A new `sync_shreds()` method on `ChuckSession` diffs `session.shreds` against `chuck.get_all_shred_ids()` and reconciles: externally-added shreds appear in the topbar, `?`/shreds table, and status bar count; finished or externally-removed shreds are pruned. Sync runs on each render tick (via the bottom toolbar callback in the REPL, status bar callback in the editor), guarded by `_otf_enable` so there is zero cost when OTF is off. OTF-discovered shreds are tagged with `shred_type="otf"`.

- **OTF CLI flags** (`cli/main.py`, `tui/tui.py`, `tui/repl.py`, `tui/editor.py`, `tui/common.py`): Added `--otf` and `--otf-port` flags to the `repl` and `edit` subcommands. `--otf` enables the ChucK OTF listener (default port 8888), allowing external `chuck` commands to add/remove shreds. The OTF port is shown in the REPL status bar when enabled.

- **REPL real-time stereo level meters** (`repl.py`, `waveform.py`): The `wave` command now displays live L/R peak meters below the shreds panel. Uses a background daemon thread polling `get_audio_meters()` at 100ms intervals with `Application(refresh_interval=0.1)` for redraws. Meters appear/disappear via `ConditionalContainer` tied to `session.show_waveform`. Styled green-on-dark-green (`class:waveform-area`).

- **REPL word aliases for symbol commands** (`parser.py`, `lang/constants.py`): Every terse symbol command now has a readable word equivalent. New aliases: `shreds` (`?`), `shred <id>` (`? <id>`), `globals` (`?g`), `audio` (`?a`), `start` (`>`), `stop` (`||`), `shutdown` (`X`), `compile <file>` (`: <file>`), `exec "code"` (`! "code"`), `shell <cmd>` (`$ <cmd>`), `snippet <name>` (`@<name>`), `get <var>` (`<var>?`), `set <var> <val>` (`<var>::<val>`), `signal <ev>` (`<ev>!`), `broadcast <ev>` (`<ev>!!`). All word aliases are tab-completable.

- **REPL command cheatsheet** (`docs/repl-commands.md`): Standalone reference documenting every REPL command organized by category, showing both symbol and word forms.

- **Wheel RECORD Validation** (`scripts/check_wheel_record.py`, `scripts/repair_wheel.py`):
  - New standalone script validates wheel RECORD files against actual ZIP contents -- checks for smuggled files, dangling entries, hash mismatches, and size mismatches
  - Addresses [wheel archive confusion attacks](https://blog.pypi.org/posts/2025-08-07-wheel-archive-confusion-attacks/)
  - Integrated into `repair_wheel.py` as a post-repair validation step for both chugin and non-chugin wheels
  - Added RECORD validation steps to CI wheels workflow (per-platform and combined artifact stages)
  - `make check` now runs RECORD validation alongside `twine check`

- **CLAP, PdPatch, and VST3 Chugins** (`thirdparty/chugins/{CLAP,PdPatch,VST3}/`):
  - Added three new chugins from [my-chugins](https://github.com/shakfu/my-chugins): CLAP (host CLAP plugins), PdPatch (embed Pure Data patches), and VST3 (host VST3 plugins)
  - All three are enabled by default via `option(CM_CLAP/CM_PDPATCH/CM_VST3 ... ON)` and bundled in release wheels
  - External dependencies (clap SDK 1.2.6, libpd, VST3 SDK v3.8.0) fetched automatically via CMake `FetchContent`
  - Can be individually disabled with `-DCM_CLAP=OFF`, `-DCM_PDPATCH=OFF`, or `-DCM_VST3=OFF`
  - macOS and Linux only -- all three depend on POSIX APIs (`dlfcn.h`, `dirent.h`, pthreads) not available on Windows
  - Fixed VST3 SDK option names (`SMTG_ENABLE_VST3_PLUGIN_EXAMPLES`/`SMTG_ENABLE_VST3_HOSTING_EXAMPLES`) to correctly disable SDK samples that require `gtk+-3.0` on Linux
  - The numchuck package now includes:
    - AbletonLink.chug
    - ABSaturator.chug
    - AmbPan.chug
    - AudioUnit.chug
    - Binaural.chug
    - Bitcrusher.chug
    - CLAP.chug
    - ConvRev.chug
    - Elliptic.chug
    - ExpDelay.chug
    - ExpEnv.chug
    - FIR.chug
    - FoldbackSaturator.chug
    - GVerb.chug
    - KasFilter.chug
    - Ladspa.chug
    - Line.chug
    - MagicSine.chug
    - Mesh2D.chug
    - MIAP.chug
    - Multicomb.chug
    - NHHall.chug
    - Overdrive.chug
    - PanN.chug
    - Patch.chug
    - PdPatch.chug
    - Perlin.chug
    - PitchTrack.chug
    - PowerADSR.chug
    - Random.chug
    - Range.chug
    - RegEx.chug
    - Sigmund.chug
    - Spectacle.chug
    - VST3.chug
    - Wavetable.chug
    - WinFuncEnv.chug
    - WPDiodeLadder.chug
    - WPKorg35.chug
    - XML.chug

### Fixed

- **Wheels workflow collect job** (`.github/workflows/wheels.yml`):
  - Reordered `collect` job steps to run `checkout` before artifact downloads -- `actions/checkout@v4` cleans the working directory by default, which was wiping the downloaded `dist/` directory

- **FetchContent install leaking into wheels** (`thirdparty/chugins/{CLAP,PdPatch}/CMakeLists.txt`):
  - Added `EXCLUDE_FROM_ALL` to `FetchContent_Declare` for CLAP and PdPatch to prevent their SDK `install()` rules from polluting the wheel with headers, pkgconfig, and cmake config files (reduced wheel from 186 to 100 files)

- **REPL ghost line on shred removal** (`common.py`): Fixed terminal rendering corruption (ghost line at bottom of screen) when removing shreds while level meters were visible. Root cause: ChucK's VM writes `[chuck]: (VM) removing shred: ...` directly to stdout via `CK_FPRINTF_STDOUT`, bypassing prompt_toolkit's full-screen renderer. Fix: `setup_output_capture()` now also sets the global/static `ChucK.set_stdout_callback()` and `ChucK.set_stderr_callback()` to route all VM system messages through the TUI log system. See `docs/architecture.md` for the two-tier callback architecture.

- **REPL exception handling** (`repl.py`): `_submit_input` (TUI) and `process_line` (stdin) now catch exceptions from `executor.execute()` and `spork_code()`, displaying graceful error messages instead of crashing with tracebacks.

- **REPL shutdown crash** (`repl.py`): Fixed malloc double-free / segfault on exit. Removed static `set_stdout_callback`/`set_stderr_callback` (which outlived the Python objects they referenced) in favor of instance-level callbacks cleaned up by `chuck.shutdown()`. Reordered cleanup to break all reference cycles before destroying C++ objects.

- **nanobind ref leak on shutdown** (`common.py`): Fixed "leaked 1 instances" / "leaked 1 types" nanobind warnings on exit. Root cause: `setup_output_capture()` registers a `log_callback` closure (capturing `self`) as static class-level callbacks via `ChucK.set_stdout_callback()` / `ChucK.set_stderr_callback()`. These outlived the instance and pinned the entire `ChuckApplication -> ChucK` object graph, preventing C++ destructor from running. Fix: `cleanup()` now clears static callbacks to `None` before breaking instance references.

- **Shell command execution** (`commands.py`): `$ <cmd>` now captures stdout/stderr (routed through `_log()`), enforces a 30-second timeout, reports nonzero exit codes, and catches `TimeoutExpired`/`OSError` instead of running unsanitized with no output capture or error handling.

- **ConvRev segfault on ARM64 macOS CI** (`test_examples.py`): Fixed segfault in `test_chugin_convrev_example` on macos-14 (ARM64). Root cause: `_check_chugin_available()` created up to 2 ChucK instances without calling `shutdown()`, leaving ConvRev's background `std::thread` active. When the test then created a new instance, concurrent ConvRev destructor/thread cleanup races caused a segfault (ARM64's stricter memory ordering exposed this). Fix: all ChucK instances in `test_examples.py` now call `remove_all_shreds()` + `shutdown()` before going out of scope.

- **Windows CI test failures** (`test_waveform.py`): Fixed 3 `TestREPLMeterInfrastructure` tests failing on Windows CI with `NoConsoleScreenBufferError`. These tests instantiate `ChuckREPL()` which creates a `prompt_toolkit.Application` requiring a real TTY. Fix: skip the test class when stdout is not a TTY.

### Changed

- **REPL help panel** (`repl.py`): F1 help text now shows `word / symbol` forms side by side for all commands that have both.

- **REPL inline transcript** (`repl.py`): Replaced split input/output layout with a single-buffer Python/Jupyter-style transcript. Input and output are interleaved in one scrollable area -- commands echo as `[=>] ...`, output is indented, errors show inline with `[!]` prefix. Removed separate log window (F3 toggle), error bar, and transcript TextArea. Input prompt sits at the bottom of the transcript buffer.

## [0.1.10]

### Added

- **Bundled Chugins in Wheels** (`scripts/cmake/fn_add_chugin.cmake`, `pyproject.toml`, `src/numchuck/api.py`):
  - Pre-built chugins (~37 `.chug` files) are now included in distributed wheels
  - `NUMCHUCK_INSTALL_CHUGINS` CMake option gates installation (ON for wheel builds, OFF for local dev)
  - `cmake.args = ["-DNUMCHUCK_INSTALL_CHUGINS=ON"]` in `pyproject.toml` enables bundling during `pip install` / `uv build`
  - Bundled chugins directory (`<package>/chugins/`) automatically added to ChucK search path in `Chuck.__init__`
  - Users no longer need to build from source to use chugins

- **`numchuck info` lists bundled chugins** (`src/numchuck/cli/main.py`):
  - Shows count and names of all bundled `.chug` files from the installed package
  - Displays "none" for editable/dev installs where chugins are in `examples/chugins/` instead

- **Cross-Platform Wheel Repair for Chugins** (`scripts/repair_wheel.py`):
  - Wheel repair tools (delocate, auditwheel, delvewheel) skip `.chug` files since they only scan platform-standard extensions
  - New repair script temporarily renames `.chug` to the native extension (`.dylib`/`.so`/`.dll`), runs the repair tool, then renames back
  - Ensures chugin shared library dependencies are properly bundled if any chugin gains external (non-system) dependencies
  - Uses only stdlib (`zipfile`, `hashlib`, `csv`) -- no dependency on the `wheel` CLI package
  - RECORD file correctly regenerated after rename operations
  - Platform-specific handling:
    - macOS: `.chug` -> `.dylib`, delocate-wheel with `--require-archs`
    - Linux: `.chug` -> `.so`, auditwheel repair
    - Windows: `.chug` -> `.dll`, delvewheel with `--analyze-existing --no-mangle`

- **README: Bundled chugins documentation** (`README.md`):
  - Categorized table of all 37 bundled chugins (38 on macOS with AudioUnit)
  - Updated "Using Chugins" section to show automatic discovery (no manual path setup)
  - Plugin Support overview links to the bundled chugins table

### Changed

- **CI: Chugin tests enabled in wheel builds** (`.github/workflows/wheels.yml`):
  - Removed `and not chugin` from `CIBW_TEST_COMMAND` filter
  - All three platforms (Linux, macOS, Windows) now use the custom repair script
  - Windows builds install delvewheel via `CIBW_BEFORE_BUILD_WINDOWS`

- **Chugin test helpers updated** (`tests/test_examples.py`):
  - New `_get_chugins_dir()` helper checks bundled package directory first, falls back to `examples/chugins/` for dev builds
  - All chugin tests (`test_chugin_loading`, `test_chugin_bitcrusher_strict`, `test_chugin_gverb_strict`, `test_chugin_convrev_example`) use the unified helper

### Fixed

- **TUI tests skipped on Windows** (`tests/conftest.py`):
  - Added `pytest_collection_modifyitems` hook to skip `@pytest.mark.tui` tests on Windows
  - prompt_toolkit raises `NoConsoleScreenBufferError` on Windows in non-console environments
  - 42 TUI tests now skip gracefully on Windows instead of failing

- **WAV file rendering tests** (`tests/test_wavfile.py`):
  - Fixed `test_render_sine_to_wav` run duration: `chuck.run(44100)` changed to `chuck.run(44100 * 4)` to match 4-second ChucK code duration
  - Added `del chuck` before temp directory cleanup in all tests to release file handles
  - Fixes `PermissionError` on Windows where files can't be deleted while open

- **Async awaitable race condition** (`src/numchuck/api.py`):
  - `get_int_awaitable`, `get_float_awaitable`, `get_string_awaitable` had a race between `run_in_executor` completion and `call_soon_threadsafe` callback delivery
  - Added `await asyncio.sleep(0)` after `run_in_executor` to yield to the event loop and process pending callbacks before checking `future.done()`
  - Fixes intermittent "callback not invoked" failures on slower platforms (macOS x86_64 under Rosetta)

## [0.1.9]

### Added

- **Chugin Directory Search** (`src/numchuck/api.py`, `src/numchuck/tui/common.py`):
  - Automatic discovery of chugins via `PARAM_IMPORT_PATH_SYSTEM` (auto-loads .chug files)
  - Default search paths:
    - `~/.numchuck/chugins` - Always included (global user chugins)
    - `./.numchuck/chugins` - Included if exists (project-local chugins)
  - `user_chugins` parameter accepts both directories and explicit `.chug` files

- **Import Path Properties** (`src/numchuck/api.py`):
  - `chuck.import_path_system` - System chugin/import search directories
  - `chuck.import_path_user` - User import search paths
  - `chuck.import_path_packages` - Package import search paths

- **ChucK Command Alignment** (`src/numchuck/tui/parser.py`, `src/numchuck/tui/commands.py`):
  - `abort.shred <id>` / `abort <id>` - ChucK-native shred abort commands
  - `exit` / `quit` - Exit the REPL
  - `= <id> file.ck` / `= <id> "code"` - ChucK-style replace shred shortcuts
  - `^` - ChucK-style status shortcut

- **Web IDE** (`src/_web.cpp`, `src/numchuck/web/`):
  - Browser-based ChucK IDE similar to WebChucK
  - Mongoose web server serving static files from package directory
  - REST API for ChucK control: compile, remove shred, audio start/stop
  - WebSocket for real-time console output and status updates
  - HTML/CSS/JS frontend in `src/numchuck/web/static/`
  - CLI command: `numchuck web [--port 8080] [files...]`
  - CMake option: `-DNUMCHUCK_ENABLE_WEB=ON` (enabled by default)
  - **Enhanced UI Features**:
    - Multi-file tabs with local storage persistence
    - Examples dropdown with built-in ChucK examples
    - Globals panel with auto-discovery and interactive sliders for int/float variables
    - Shred management: replace shred, preview code, elapsed time display
    - Theme toggle (dark/light mode) with system preference detection
    - Open file from disk (Ctrl+O) and download/save-as (Ctrl+Shift+S)
    - Keyboard shortcuts: Ctrl+Enter (spork), Ctrl+S (save), Ctrl+N (new tab), Ctrl+O (open), Ctrl+Shift+S (download)
  - **Real-time Audio Metering**:
    - RMS and peak level meters for left/right channels
    - Calculated in C++ audio callback for accuracy
    - Streamed via WebSocket every 100ms when audio running
    - Visual meter bars in browser UI
    - New `get_audio_meters()` function in Python API
  - **WebSocket Globals Sync**:
    - Push-based globals updates (every 500ms when changed)
    - Reduced polling to 10s fallback
    - Real-time slider sync in browser UI
  - **Bundled Static Assets** (offline support):
    - CodeMirror 5.65.16 editor bundled locally (`css/`, `js/`)
    - xterm.js 5.3.0 terminal emulator for REPL
    - No external CDN dependencies required
    - Works completely offline
  - **Interactive Web REPL**:
    - Full terminal emulator using xterm.js
    - Toggle between Editor and REPL views
    - Full command parity with TUI REPL (all ChucK commands supported)
    - Supports all REPL commands: +, -, =, status, globals, events, etc.
    - Command history with up/down arrows
    - Cut/copy/paste support (Ctrl+X/C/V or Cmd+X/C/V)
    - Right-click to select word
    - Ctrl+C to cancel (when no selection), Ctrl+L to clear
    - ChucK code can be entered directly
    - Clicking files in sidebar switches to Editor view
  - **New REST API Endpoints**:
    - `GET /api/globals` - List all global variables with types
    - `POST /api/shred/:id/replace` - Replace running shred with new code
    - `GET /api/shred/:id/code` - Get shred source code

- **Audio Metering API** (`src/_numchuck.cpp`, `src/numchuck/_numchuck.pyi`):
  - `get_audio_meters()` - Returns dict with `rms_left`, `rms_right`, `peak_left`, `peak_right`
  - Thread-safe atomic floats updated in real-time audio callback
  - `AudioMeters` TypedDict for type checking

- **Type Stubs for Web Module** (`src/numchuck/_web.pyi`):
  - Complete type annotations for `WebServer` class
  - Properties: `port`, `static_dir`, `is_running`, `client_count`
  - Methods: `set_api_handler`, `broadcast`, `start`, `stop`

- **Audio Stream Iteration API** (`src/numchuck/api.py`):
  - `chuck.stream(frames_per_chunk, max_chunks, reuse)` generator method
  - Iterator-based audio processing: `for audio in chuck.stream(512): process(audio)`
  - Supports infinite iteration with early break, or bounded with `max_chunks`
  - Zero-allocation mode with `reuse=True` (default)
  - 8 new tests for stream iteration

- **UGen Parameter Autocomplete** (`src/numchuck/tui/completer.py`):
  - Tab completion for UGen parameters after `.`: `.freq`, `.gain`, `.phase`, etc.
  - Context-aware: detects UGen type from variable declarations
  - `UGEN_PARAMS` mapping with parameters for 40+ UGens (oscillators, filters, envelopes, delays, reverbs, buffers, STK instruments)
  - 6 new tests for parameter completion

- **Offline Audio Rendering API** (`src/numchuck/render.py`):
  - `render(code, duration, sample_rate, channels, dtype)` - Render ChucK code to numpy array
  - `render_file(files, duration, sample_rate, channels, dtype)` - Render ChucK files to numpy array
  - `to_wav(output, code, files, duration, ...)` - Export ChucK code/files to WAV file
  - `RenderError` exception for rendering failures
  - Supports both `np.float32` and `np.int16` output dtypes
  - Chunked rendering to avoid memory issues for long durations

- **User Directory Template** (`_numchuck/`):
  - Template for `.numchuck` user configuration directory
  - Search order: `./.numchuck` (local) then `~/.numchuck` (global)
  - Local configuration takes precedence over global
  - Subdirectories with examples:
    - `snippets/` - Code snippets (sine, fm, drum, noise, delay)
    - `examples/` - Example ChucK files (hello, arpeggio, lfo)
    - `themes/` - Color themes (dark.toml, light.toml)
    - `keybindings/` - Key binding configurations (default.toml)
    - `chugins/` - User chugins with README
  - Copy to home: `cp -r _numchuck ~/.numchuck`

- **Snippet Support** with local/global precedence:
  - Snippets stored in `.numchuck/snippets/` directory
  - Local snippets (`./.numchuck/snippets/`) take precedence over global (`~/.numchuck/snippets/`)
  - CLI commands: `numchuck snippets list`, `snippets show <name>`, `snippets path`
  - REPL command: `@<name>` to load a snippet with tab completion

- **File Watch Mode** (`src/numchuck/watcher.py`):
  - `FileWatcher` class for auto-reloading ChucK files on modification
  - Debouncing to prevent rapid reloads during saves
  - Callbacks for reload and error events
  - CLI command: `numchuck watch file1.ck file2.ck`
  - REPL commands: `watch <file>`, `unwatch <file>`, `watching`

- **Theme Support** (`src/numchuck/tui/themes.py`):
  - Built-in themes: `dark`, `light`, `solarized`
  - `ThemeConfig` and `ThemeColors` dataclasses in config
  - `create_style(theme_config)` generates prompt_toolkit Style
  - Configurable via `~/.numchuck/config.toml`

- **Configurable Key Bindings** (`src/numchuck/config.py`):
  - `KeybindingsConfig` dataclass with all key bindings
  - `create_keybinding(kb, key, handler)` with safe validation
  - Customizable via `~/.numchuck/config.toml`

- **Waveform Display** (`src/numchuck/tui/waveform.py`):
  - `samples_to_waveform()` - Convert audio samples to Unicode/ASCII waveform
  - `WaveformBuffer` - Circular buffer for real-time waveform display
  - `format_waveform_bar()`, `format_stereo_meters()` - Level meter formatting
  - `calculate_rms()`, `calculate_peak()` - Audio level calculations
  - `db_to_linear()`, `linear_to_db()` - Decibel conversions
  - REPL commands: `wave`, `wave on`, `wave off` (toggle with F4)

- **Session Recording/Playback** (`src/numchuck/recording.py`):
  - `SessionRecorder` - Record REPL sessions with timestamps
  - `SessionPlayer` - Playback recorded sessions with speed control
  - `RecordedAction`, `RecordedSession` dataclasses
  - JSON-based session storage in `~/.numchuck/recordings/`
  - REPL commands: `record start`, `record stop`, `record save <name>`, `play <name>`

- **MIDI Learn Support** (`src/numchuck/midi.py`):
  - `MIDIMapping` - Map MIDI CC to ChucK global variables with min/max scaling
  - `MIDIMappings` - Collection of MIDI mappings
  - `MIDILearnState` - State machine for MIDI learn mode
  - `generate_midi_listener_code()` - Generate ChucK code for MIDI control
  - `generate_midi_monitor_code()` - Generate MIDI monitor code
  - REPL commands: `midi learn <var> <cc> [channel] [min max]`, `midi list`, `midi start`, `midi stop`

- **OSC Integration** (`src/numchuck/osc.py`):
  - `OSCServer` - UDP server for receiving OSC messages
  - `OSCClient` - UDP client for sending OSC messages
  - `OSCController` - Map OSC addresses to REPL actions
  - `generate_osc_listener_code()` - Generate ChucK code using native liblo
  - `generate_osc_sender_code()` - Generate ChucK OSC sender code
  - OSC address patterns: `/numchuck/set/<var>`, `/numchuck/event/<name>`, `/numchuck/spork`
  - REPL commands: `osc start [port]`, `osc stop`, `osc status`

- **Context Manager Support** (`src/numchuck/api.py`):
  - `Chuck` class now supports `with` statement for automatic cleanup
  - `__enter__` and `__exit__` methods ensure `close()` is called on exit
  - Example: `with Chuck() as ck: ck.compile("SinOsc s => dac;")`
  - 4 new tests for context manager behavior

- **Async/Await API** (`src/numchuck/api.py`):
  - `get_int_awaitable(name, run_frames=256) -> int` - Async get global int
  - `get_float_awaitable(name, run_frames=256) -> float` - Async get global float
  - `get_string_awaitable(name, run_frames=256) -> str` - Async get global string
  - Uses asyncio with executor for non-blocking VM execution
  - 4 new async tests

- **Typed Global Variable Proxies** (`src/numchuck/api.py`):
  - `GlobalInt`, `GlobalFloat`, `GlobalString` classes for property-based access
  - Factory methods: `chuck.global_int("name")`, `chuck.global_float("name")`, `chuck.global_string("name")`
  - Property access: `tempo.value = 120` instead of `chuck.set_int("tempo", 120)`
  - Methods: `get()`, `set(value)`, `get_async()` (awaitable)
  - 5 new proxy tests

- **Shred Handle Objects** (`src/numchuck/api.py`):
  - `Shred` class wrapping shred IDs with methods for control
  - Factory methods: `chuck.spork(code, args="")`, `chuck.spork_file(path, args="")`
  - Methods: `remove()`, `replace(code, args="")`, `info` property
  - Properties: `id`, `is_running`
  - Equality comparison with int shred IDs
  - 9 new shred tests

- **Configuration File Support** (`src/numchuck/config.py`):
  - Support for `~/.numchuck/config.toml` user configuration
  - Dataclasses: `Config`, `AudioConfig`, `REPLConfig`, `EditorConfig`, `PathsConfig`, `ChuckConfig`
  - Functions: `load_config()`, `save_config()`, `get_config()`, `reload_config()`
  - Automatic defaults for missing values
  - 7 new config tests

- **PEP 561 Type Checker Support**:
  - Added `py.typed` marker file (`src/numchuck/py.typed`)
  - Added "Typing :: Typed" classifier to pyproject.toml

- **TUI Refactoring**:
  - Extracted `ChuckCompleter` to standalone class (`src/numchuck/tui/completer.py`)
  - Enhanced `ChuckApplication` base class with audio lifecycle management
  - Added `setup()`, `start_audio_playback()`, `stop_audio_playback()` methods
  - Unified output capture with `setup_output_capture()` and `set_log_callback()`
  - 12 new completer tests

- **TUI Logging Module** (`src/numchuck/tui/logging.py`):
  - Centralized logging for TUI components
  - `LogLevel` enum (DEBUG, INFO, WARNING, ERROR)
  - `TUILogger` class with callbacks, stream output, timestamps
  - Message storage with level filtering via `get_messages(level=...)`
  - Global logger functions: `get_logger()`, `set_logger()`, `debug()`, `info()`, `warning()`, `error()`
  - 15 new logging tests

- **Service Layer Architecture** (`src/numchuck/services/`):
  - New `services` package providing business logic separation from UI
  - `AudioService` - Audio lifecycle management (start/stop/restart/shutdown)
  - `ShredService` - Shred compilation, replacement, and removal with structured results
  - `GlobalsService` - Global variable get/set operations and event signaling
  - `FileService` - Snippet loading and project file operations
  - Services are stateless with dependency injection via constructor
  - Returns structured dataclasses (`ShredResult`, `GlobalInfo`, `SnippetInfo`) instead of formatted strings
  - Used by both CLI and TUI for shared business logic
  - 89 new service tests with 84% coverage

- **TUI Widget Factories** (`src/numchuck/tui/widgets.py`):
  - `create_help_window()` - Conditional help display
  - `create_shreds_table()` - Dynamic shreds table
  - `create_log_window()` - Scrollable log display
  - `create_status_bar()` - Status bar with dynamic content
  - `create_message_area()` - Text area for messages

- **AudioService Class** (`src/numchuck/services/audio.py`):
  - RAII-style audio lifecycle management
  - Methods: `start()`, `stop()`, `restart()`, `shutdown()`
  - Property: `is_running`
  - Optional callbacks: `set_callbacks(on_start=..., on_stop=...)`
  - Logger integration for consistent error reporting
  - Used by CLI (`executor.py`, `watcher.py`) and TUI (`common.py`)
  - 8 new AudioService tests

- **TUI Type Hints Completion**:
  - `common.py` - Full annotations for AudioManager and ChuckApplication
  - `commands.py` - All 20+ command methods annotated with return types
  - `session.py` - ChuckSession fully typed with logger integration
  - `repl.py` - Key methods typed (run, setup, process_input, cleanup)
  - `completer.py` - ChuckCompleter with TYPE_CHECKING imports
  - `editor.py` - EditorTab and ChuckEditor classes fully typed

- **TUI Error Handling Standardization**:
  - Command methods return error strings instead of raising exceptions
  - Logger integration for warnings and debug output
  - Specific exception types instead of broad `Exception` catches

- **REPL Stdin Mode** (`src/numchuck/tui/repl.py`, `src/numchuck/tui/tui.py`):
  - Non-interactive REPL mode for piped input and scripting
  - Automatic detection: uses stdin mode when input is not a TTY
  - New `ChuckREPLStdin` class for processing commands from stdin
  - Comment support: lines starting with `#` are ignored
  - Exit commands: `quit`, `exit`, or `q` to stop processing
  - Usage examples:
    - `echo '+ test.ck' | numchuck repl` - Pipe commands
    - `numchuck repl < commands.txt` - Redirect input
    - `cat script.txt | numchuck repl` - Script execution
  - New `--stdin` CLI flag to force stdin mode even in interactive terminals
  - 63 new tests for stdin REPL mode (`tests/test_repl_stdin.py`)

### Changed

- **CommandExecutor Refactoring** (`src/numchuck/tui/commands.py`):
  - Now uses `ShredService`, `GlobalsService`, and `FileService` for all operations
  - Added `shred_service`, `globals_service`, and `file_service` properties with proper None handling
  - Snippet loading (`@name`) now uses `FileService` instead of direct path functions
  - Simplified command methods to delegate to services
  - `_cmd_list_shreds` now uses session data instead of VM query (works without audio running)

- **ChuckApplication Service Integration** (`src/numchuck/tui/common.py`):
  - Added `shred_service`, `globals_service`, and `file_service` lazily-created properties
  - Services are cached after first access for reuse
  - UI factory methods now delegate to `tui/widgets.py` module
  - `chuck` and `session` are now properties that raise `RuntimeError` if accessed after cleanup
  - Cleanup method properly handles None state and circular reference breaking
  - Fixed `close()` to `shutdown()` for ChucK instance cleanup

- **Editor Refactoring** (`src/numchuck/tui/editor.py`):
  - F5/Ctrl-R (spork) now uses `ShredService.spork_code()` instead of direct ChucK calls
  - F6 (replace) now uses `ShredService.replace_shred()` instead of direct ChucK calls
  - Session tracking handled automatically by ShredService
  - Simplified error handling with structured `ShredResult` returns

- **REPL Refactoring** (`src/numchuck/tui/repl.py`):
  - Direct code compilation now uses `ShredService.spork_code()` instead of direct ChucK calls
  - Consistent with CommandExecutor's service-based approach

- **API Refactoring** - Moved general-purpose modules from `tui/` to top level for library use:
  - `numchuck.render` - Offline rendering API (new, from `cli/export.py`)
  - `numchuck.osc` - OSC server/client (from `tui/osc_server.py`)
  - `numchuck.midi` - MIDI mappings (from `tui/midi.py`)
  - `numchuck.watcher` - File watcher (from `tui/watcher.py`)
  - `numchuck.recorder` - Session recording (from `tui/recording.py`)
  - `numchuck.paths` - Path utilities (from `tui/paths.py`)

- **New `numchuck.lang` Subpackage** - ChucK language support:
  - `numchuck.lang.constants` - Keywords, types, UGens, operators (from `chuck_lang.py`)
  - `numchuck.lang.lexer` - Pygments lexer for syntax highlighting (from `lexer.py`)
  - Convenience imports: `from numchuck.lang import ChuckLexer, KEYWORDS, UGENS`

- **Package Exports** (`src/numchuck/__init__.py`):
  - Core: `Chuck`, `Shred`, `GlobalInt`, `GlobalFloat`, `GlobalString`
  - Rendering: `render`, `render_file`, `to_wav`, `RenderError`
  - Config: `Config`, `load_config`, `get_config`, `save_config`
  - Specialized modules require explicit imports:
    - `from numchuck.osc import OSCServer, OSCClient, ...`
    - `from numchuck.midi import MIDIMapping, MIDIMappings, ...`
    - `from numchuck.watcher import FileWatcher, ...`
    - `from numchuck.recorder import SessionRecorder, ...`
    - `from numchuck.lang import ChuckLexer, KEYWORDS, ...`

- **Python Version Support**:
  - Dropped Python 3.8 and 3.9 support (3.9 EOL October 2025, union type syntax requires 3.10+)
  - Now requires Python 3.10+
  - Added Python 3.13 classifier

- **Test Count**: 963 tests (up from 603)

- **CLI Test Suite** (`tests/test_executor.py`, `tests/test_watcher_cli.py`):
  - Added 28 new tests for CLI executor and watcher modules
  - Mock-based testing for `execute_files()` and `watch_files()` functions
  - Tests cover: file validation, compilation, audio start/stop, signal handling, cleanup
  - Refactored `executor.py` to use high-level API for better testability

### Removed

- **Chump Package Manager Integration**:
  - Removed `_chump.cpp`, `_chump.py`, `packages.py`, `cli/packages.py`
  - Removed `numchuck pkg` CLI commands
  - Removed chump documentation from README.md and CHANGELOG.md
- **`tui` CLI subcommand** - Use `numchuck repl` instead (the `tui` alias is no longer supported)
- **`AudioManager` backward compatibility alias** - Use `AudioService` directly from `numchuck.services`

### Fixed

- **Linux Build Failure** (`src/_web.cpp`):
  - Added missing `#include <algorithm>` for `std::remove`
  - GCC 14 was resolving `std::remove` to C's `remove(const char*)` from `<cstdio>`

- **Windows Build Failure** (`src/_numchuck.cpp`):
  - Added `#define NOMINMAX` to prevent Windows `min`/`max` macros from conflicting with `std::min`/`std::max`
  - Fixes C2589 "illegal token" errors in audio metering code

- **Web IDE Server Crash on Page Load** (`src/_numchuck.cpp`):
  - Fixed segfault (exit code 139) when browser connects to Web IDE
  - Root cause: `get_all_globals()` called `self.globals()->get_all_global_variables()` without null check
  - When no globals are defined, `self.globals()` returns nullptr
  - Browser's JavaScript polls `/api/globals` every 2 seconds, triggering crash on page load
  - Added null pointer check to return empty list when globals manager is unavailable

- **Web IDE Audio Status Incorrect** (`src/_numchuck.cpp`, `src/numchuck/web/__init__.py`):
  - Fixed audio toggle showing "Running" when audio was actually stopped
  - Root cause: `_is_audio_running()` checked `audio_info()["sample_rate"] > 0` which is always true
  - ChucK always has a sample rate configured regardless of audio running state
  - Added new `is_audio_running()` C++ function that checks actual audio context state
  - Updated Python wrapper to use new function for accurate status

- **Windows File Compilation** (`src/_numchuck.cpp`):
  - Normalize Windows backslash paths to forward slashes before passing to ChucK
  - Fixes "Failed to compile" errors on Windows CI with temp file paths

- **CI Test Stability**:
  - Added `@pytest.mark.realtime` to `test_audio_commands` to skip on CI without audio devices
  - Fixes ALSA errors on Linux CI runners

- **macOS Script Compatibility** (`scripts/remove_chump.sh`):
  - Replaced BSD-incompatible sed commands with Python for cross-platform file modifications

- **Type Safety Improvements** (full `mypy --strict` compliance):
  - `api.py`: Added `_chuck` property with proper None handling after `close()`
  - `common.py`: `chuck` and `session` properties raise `RuntimeError` if accessed after cleanup
  - `commands.py`: `shred_service` and `globals_service` properties with None checks
  - `globals.py`: Fixed variable reuse in `get_global()` method, explicit array type annotations
  - `completer.py`: Renamed shadowed `match` variable, added explicit `return None`

- **Nanobind memory leak warnings on REPL exit**:
  - `ChuckCompleter` was holding references to `chuck` and `session` that weren't cleaned up
  - Added proper cleanup of completer references before ChucK instance is closed
  - Added `gc.collect()` calls to ensure C++ objects are released before interpreter shutdown
  - REPL now exits cleanly without "leaked instances/types/functions" warnings

- **REPL cleanup method idempotency** (`src/numchuck/tui/repl.py`):
  - `ChuckREPL.cleanup()` can now be safely called multiple times
  - Added `is not None` checks before accessing completer, executor, and app_state
  - Prevents `AttributeError` when cleanup is called on already-cleaned instance

- **Segfault on test suite exit** (`src/numchuck/tui/repl.py`):
  - Removed problematic static callback clearing from `ChuckREPL.cleanup()`
  - Setting `set_stdout_callback`/`set_stderr_callback` to lambdas during cleanup caused segfault at interpreter shutdown
  - Tests now use `app_state.setup()` instead of `repl.setup()` to avoid setting static callbacks

- **Full `mypy --strict` compliance** (150 type errors fixed across 17 files):
  - `parser.py`: Added type annotations to all 50+ command handler methods, `Command.args` typed as `dict[str, Any]`
  - `midi.py`: Fixed `dict` type parameters, added `Iterator` return type for `__iter__`
  - `recorder.py`: Fixed `dict` type parameters, added explicit casts in `from_dict` methods
  - `waveform.py`: Fixed `deque` type parameter
  - `render.py`: Fixed `NDArray` type parameters for return types
  - `api.py`: Added `TracebackType` for `__exit__`, typed `shred_info` return as `dict[str, Any]`
  - `packages.py`: Fixed `_from_info` parameter type
  - `cli/packages.py`: Added `_get_manager` return type annotation
  - `cli/snippets.py`: Fixed `get_snippet_info` return type
  - `session.py`: Added `_file_watcher` attribute, fixed `get_shred_name` return type
  - `common.py`: Added type parameters to `generate_shreds_table`
  - `commands.py`: Fixed `_get_or_create_watcher` return type, removed unnecessary `hasattr` check
  - `executor.py`: Added return type and `FrameType` parameter type to `signal_handler`
  - `repl.py`: Added type annotations to all inner functions (15+ nested handlers), removed unused type ignores
  - `editor.py`: Added type annotations to all 10 key binding handlers
  - `cli/main.py`: Added return type annotations to all 12 command functions

## [0.1.8]

### Fixed

- **Missing pygments dependency**. This is now added.

## [0.1.7]

### Added

- **Pip Install Test Workflow** (`.github/workflows/pip-test.yml`):
  - Installs numchuck from PyPI and runs full test suite
  - Verifies installed package comes from site-packages (not local src/)
  - Tests on Linux and macOS with Python 3.9-3.12

- **WAV File Rendering Tests** (`tests/test_wavfile.py`):
  - `test_render_sine_to_wav` - mono recording with `WvOut`
  - `test_render_stereo_to_wav` - stereo recording with `WvOut2`
  - `test_me_dir_path` - tests `me.dir()` path construction

### Fixed

- **Duplicate macOS wheel builds** (`.github/workflows/wheels.yml`):
  - Removed redundant `macos-15` runner (same ARM64 arch as `macos-14`)
  - Added `CIBW_ARCHS_MACOS: "x86_64 arm64"` for cross-compilation
  - Now builds both Intel and Apple Silicon wheels from single runner

- **Windows access violation during VM cleanup** (upstream fix in `thirdparty/chuck`):
  - Added 50ms delay after VM stop on Windows in `ChucK::shutdown()` (`chuck.cpp`)
  - Allows WASAPI/DirectSound audio threads to fully terminate before cleanup
  - Made `ChucK::shutdown()` public in `chuck.h` for explicit cleanup from bindings
  - Python API: `Chuck.close()` method for explicit shutdown

### Changed

- **Updated platform testing in wheels.yml**:
  - Re-enabled tests on `macosx_arm64` and Windows
  - `manylinux_aarch64` skipped (cross-compiled, no native runner)
  - `wavfile` tests skipped in CI (WvOut timing issues)
  - `chugin` tests skipped in CI (not bundled in wheel)

### Removed

- **install-test.yml** - consolidated into pip-test.yml
- **render-test.yml** - functionality covered by test_wavfile.py

## [0.1.6]

- version bump due to corrupted wheel: `numchuck-0.1.5-cp310-cp310-macosx_11_0_arm64.whl`

## [0.1.5]

### Added

- **Thread Safety Documentation**:
  - Added prominent warning block in `docs/architecture.md` listing unsafe operations during real-time audio playback
  - Documented safe operations (global variable access, event signaling, read-only queries)
  - Added recommended patterns for stopping audio before modifications
  - Added Thread Safety section to `src/numchuck/api.py` module docstring
  - Added Warning sections to `compile()`, `compile_file()`, `remove_shred()`, and `clear()` method docstrings

- **Comprehensive Code Review** (`CODE_REVIEW.md`):
  - Architecture analysis and code quality assessment
  - Identified issues with recommendations
  - Code quality metrics and ratings

- **Install Test Workflow** (`.github/workflows/install-test.yml`):
  - Tests `pip install numchuck` from PyPI on all platforms
  - Verifies extension imports correctly on Linux, macOS, and Windows
  - Tests Python 3.9-3.12 in virtualenv environments

- **TUI Component Tests**:
  - `tests/test_command_parser.py` - 44 tests for REPL command parsing
    - Shred management commands (add, remove, replace)
    - Status and info commands
    - Global variable get/set
    - Event signaling
    - Audio and VM control
    - File operations and snippets
  - `tests/test_tui_common.py` - 15 tests for shared TUI utilities
    - `format_elapsed_time()` edge cases
    - `format_shred_name()` path handling and truncation
    - `generate_shreds_table()` with mock ChucK

- **Expanded test_api.py Coverage**:
  - Added `TestEventCallbacks` class with 5 tests for event signaling and callbacks
  - Added `TestAdvanceMethod` class with 2 tests for advance() behavior
  - Added `TestBufferReuseModes` class with 4 tests for buffer management modes
  - Total test count increased from 143 to 213

### Fixed

- **Broken `numchuck run` command** (`cli/executor.py`):
  - Fixed call to non-existent `ChucK.create()` method
  - Now uses proper initialization sequence: `ChucK()` + `set_param()` + `init()`

- **Hardcoded version strings** (`cli/main.py`):
  - `cmd_version()` and `cmd_info()` now import `__version__` from `_version.py`
  - Previously hardcoded "0.1.1" instead of current version

- **Per-instance callback storage** (`src/_numchuck.cpp`):
  - `set_chout_callback()` and `set_cherr_callback()` now use per-instance storage
  - Previously used static variables shared across all ChucK instances
  - Added thread-local `g_current_chuck` to track active instance during calls
  - Added `ChuckContextGuard` RAII wrapper for compile/run methods
  - Multiple ChucK instances can now have independent output callbacks

- **Memory leak in `replace_shred`** (`src/_numchuck.cpp`):
  - Used `std::unique_ptr` for exception safety during `Chuck_Msg` construction
  - Previously, if argument parsing threw, both `msg` and `msg->args` would leak

- **Improved error propagation for sync getters** (`src/numchuck/api.py`):
  - `get_int()`, `get_float()`, `get_string()` now provide specific error messages
  - Error message explains that callback wasn't invoked and suggests increasing `run_frames`
  - Previously raised generic "Failed to get global X" without actionable guidance

- **Inconsistent error handling in REPL cleanup** (`src/numchuck/tui/repl.py`):
  - Now catches `RuntimeError` specifically for ChucK operations
  - Catches `(RuntimeError, OSError)` for audio operations
  - Previously broad `Exception` catch masked specific errors

- **Flaky test patterns** (multiple test files):
  - `test_global_events.py`: Replaced `try/except pass` with explicit outcome tracking
  - `test_realtime_audio.py`: Fixed bare `except:` to catch specific exceptions with assertions
  - `test_error_handling.py`: dtype tests now explicitly document both valid outcomes

### Changed

- **Documented thread safety in editor** (`src/numchuck/tui/editor.py`):
  - Added docstring explaining prompt_toolkit's single-threaded model
  - Clarifies that `current_tab_index` access is safe (no race condition)

- **Consolidated shreds table rendering** (`tui/common.py`, `tui/repl.py`):
  - Created shared utility functions: `format_elapsed_time()`, `format_shred_name()`, `generate_shreds_table()`
  - Eliminated ~60 lines of duplicated code between REPL and editor
  - Fixed bug in `common.py` using wrong method (`get_param()` instead of `get_param_int()`)
  - Unified time formatting: seconds, minutes+seconds, or hours+minutes

- **Moved imports to module level** in TUI components for better performance:
  - `tui/parser.py`: `ast`
  - `tui/commands.py`: `os`, `sys`, `tempfile`, `time`, `pathlib.Path`, snippet utilities
  - `tui/common.py`: `ChucK`, `ChuckSession`
  - `tui/session.py`: `Project`, `get_projects_dir`

## [0.1.4]

- **Project Renamed**: `numchuck` -> `numchuck`
  - Package import: `from numchuck import Chuck`
  - CLI: `numchuck edit`, `numchuck repl`, `numchuck run`
  - Config directory: `~/.numchuck/`
  - All internal references updated

## [0.1.2]

**Summary:** This release introduces a high-level Pythonic API, cross-platform wheel building, and build system enhancements. The new `Chuck` class provides properties and simplified methods while the low-level API remains available for fine-grained control.

**Key Highlights:**

- New high-level `Chuck` class with Pythonic properties and methods
- Cross-platform wheel building via cibuildwheel (Linux, macOS, Windows)
- Full Linux support with ALSA audio backend
- Multiple `run()` variants for different use cases (zero-allocation real-time loops)
- Full `mypy` type checking support with proper stubs
- Dynamic chugins now output to `examples/chugins/` (not bundled in wheel)
- Improved build system with `scikit-build-core` and `uv`

### Added

- **Cross-Platform Wheel Building** (`.github/workflows/wheels.yml`):
  - cibuildwheel v3.3.0 for automated wheel building
  - Platforms: Linux (manylinux), macOS (ARM64), Windows (x64)
  - Python versions: 3.9, 3.10, 3.11, 3.12, 3.13
  - Source distribution (sdist) building
  - Artifact collection job aggregates all wheels
  - PyPI publishing on tag push (trusted publisher)

- **Consolidated Run API** (`numchuck.api.Chuck`):
  - `run(num_frames, *, output=None, input=None, reuse=False)` - Unified audio processing
    - No args: allocates new buffer each call (prototyping, offline)
    - `output=buf`: uses provided buffer (zero allocation)
    - `output=buf, input=buf`: effect mode with both buffers
    - `reuse=True`: uses internal buffer (zero GC without manual management)
  - `advance(num_frames)` - Advance VM time without returning audio (callbacks/events)
  - Clean two-method API replaces previous five methods
  - Comprehensive tests for all usage patterns

- **Linux Build Support**:
  - Parser generation with bison/flex on Linux
  - ALSA audio backend (`__LINUX_ALSA__`, `__PLATFORM_LINUX__`)
  - Link libraries: `-ldl`, `-lpthread`, `-lm`, `-lasound`, `-lsndfile`
  - Position-independent code (`-fPIC`) for shared library linking

- **High-Level Python API** (`numchuck.api.Chuck`):
  - Pythonic wrapper class with properties instead of get/set methods
  - Properties: `sample_rate`, `version`, `chugin_enable`, `working_directory`, etc.
  - Simplified methods: `compile()`, `run()`, `set_int()`, `get_int()`, etc.
  - Synchronous global variable getters (handles async callbacks internally)
  - Constructor with all parameters as kwargs with sensible defaults
  - Access low-level API via `chuck.raw` property
  - Exported directly from `numchuck` package: `from numchuck import Chuck`

- **Type Stub Improvements** (`_numchuck.pyi`):
  - Added 8 missing PARAM_* constants (TTY_COLOR, TTY_WIDTH_HINT, COMPILER_HIGHLIGHT_ON_ERROR, etc.)
  - Renamed from `__init__.pyi` to `_numchuck.pyi` to match module
  - Added `py.typed` marker for PEP 561 compliance

- **Developer Dependencies**:
  - Added `types-Pygments>=2.18.0` for mypy compatibility

- **Strict Chugin Tests** (`tests/test_examples.py`):
  - `test_chugin_bitcrusher_strict` - Verifies Bitcrusher chugin loads and produces audio
  - `test_chugin_gverb_strict` - Verifies GVerb chugin loads and processes reverb
  - `test_chugin_convrev_example` - Tests loading `examples/convrev/ConvRev.ck` with IR file
  - Uses `PARAM_IMPORT_PATH_SYSTEM` to set chugin search path (matching chuck-max)
  - Uses `@import "<chugin-name>";` syntax to load chugins
  - Tests skip gracefully if chugins not built

### Changed

- **Package Exports**:
  - `numchuck` now exports only the high-level `Chuck` class
  - Low-level API available via `from numchuck._numchuck import ChucK`
  - Internal modules import from `_numchuck` directly

- **Chugin Build System** (`scripts/cmake/fn_add_chugin.cmake`):
  - Dynamic chugins now output to `examples/chugins/` directory
  - Removed wheel installation of `.chug` files
  - Chugins managed externally
  - Codesigning moved from install-time to post-build command

- **API Method Signatures** (`api.py`):
  - `remove_shred()` returns `None` (not `bool`)
  - `replace_shred()` returns `int` (new shred ID, 0 on failure)
  - `signal_event()` and `broadcast_event()` return `None`
  - `on_event()` returns `int` callback ID, added `stop_listening_for_event()`

### Changed

- **macOS Deployment Target**:
  - Updated from 10.14/10.15 to 11.0 (required for ARM64 Macs)
  - Applied consistently in CMakeLists.txt, pyproject.toml, and wheels.yml

- **cibuildwheel Configuration**:
  - Removed `pp*` from skip selector (PyPy not enabled, was causing warnings)
  - Test skip includes Windows (access violation in tests)
  - Before-build command uses correct shell operator precedence

### Fixed

- **Windows Build** (LNK1149 linking error):
  - Fixed `chuck_lib` output naming conflict with `chuck` executable
  - Renamed library output to `chuckcore.lib` on Windows
  - Both targets can now coexist without import library collision

- **GCC 14+ Compatibility** (manylinux builds):
  - Fixed `invalid conversion from 'void*' to '__timezone_ptr_t'` error
  - Added `-fpermissive` flag for GCC 14+ in ChucK core compilation
  - Allows implicit void* conversions in legacy C code

- **Linux Shared Library Linking** (relocation error):
  - Added `-fPIC` to chuck_lib on Linux
  - Required for linking static library into Python extension (.so)
  - Fixes `R_X86_64_32S` relocation error on x86_64

- **Type Checking** (`make typecheck` now passes):
  - Fixed `set_param` vs `set_param_string` for working_directory
  - Fixed `compile_code` return type handling in executor.py
  - Added type annotation for `shred_versions` dict in project.py
  - Fixed variable shadowing (`f` -> `fh`) in executor.py

- **Linting** (`make lint` passes):
  - Removed unused variables (`version_parser`, `info_parser`, `count`)
  - Changed bare `except:` to `except Exception:`

---

## [0.1.1]

**Summary:** This release focuses on critical bug fixes, comprehensive documentation, developer experience improvements, and productivity enhancements. All critical and high-priority issues identified in the code review have been resolved, along with low-priority code quality improvements.

**Key Highlights:**

- Fixed segmentation fault on test exit (exit code 139 -> 0)
- Standardized error handling with comprehensive documentation
- Documented event listener cleanup to prevent memory leaks
- Renamed `exec` -> `run` CLI subcommand for consistency
- Updated build system to use `uv` throughout
- Increased test coverage (96 -> 114 tests, all passing)
- Added 15 integration tests for end-to-end workflows
- Fixed all 15 remaining bare except clauses in TUI code
- Added shell completion support (bash and zsh)
- Added performance benchmarks for regression detection
- Single version source following Python best practices
- CI/CD pipeline with multi-platform testing
- Type stubs for IDE autocomplete and type checking
- Sphinx documentation structure ready to deploy

### Added

- **Comprehensive Error Handling Documentation** (`docs/error_handling.md`):
  - Complete guide to exception-based error handling in numchuck
  - Examples for all API patterns (initialization, compilation, events, etc.)
  - Best practices for error handling and resource cleanup
  - Input validation rules and error message formats
  - Debugging tips and common patterns
  - ~400 lines of detailed documentation

- **Event Listener Cleanup Tests** (`tests/test_global_events.py`):
  - `test_listen_for_event()` - Verifies listener registration and callback invocation
  - `test_stop_listening_for_event()` - Verifies cleanup prevents memory leaks
  - `test_multiple_event_listeners()` - Verifies cleanup API functionality
  - Total event tests increased from 3 to 6
  - Documents proper usage of `stop_listening_for_global_event()` API

### Fixed

- **Segmentation Fault on Test Exit** (Critical):
  - Fixed exit code 139 (SIGSEGV) that occurred after all tests passed
  - Root cause: Global callback map held Python objects that outlived interpreter
  - Solution: Added `atexit` cleanup to destroy Python objects before shutdown
  - Implemented `_cleanup_callbacks()` function registered with Python's `atexit`
  - All tests now exit cleanly with exit code 0
  - See `SEGFAULT_FIX.md` for detailed technical analysis

- **Error Handling Consistency** (Critical):
  - Standardized all error handling to use exceptions consistently
  - `ValueError` for invalid input parameters (empty strings, zero/negative values)
  - `RuntimeError` for operational failures (not initialized, operation failed)
  - Compilation errors return `(False, [])` tuple (syntax errors are expected)
  - Added comprehensive module docstring documenting error strategy
  - See `docs/ERROR_HANDLING.md` for complete guide

- **Event Listener Memory Leak Documentation** (Critical):
  - Documented that `listen_for_global_event()` returns listener ID for cleanup
  - Added examples showing proper use of `stop_listening_for_global_event()`
  - Memory leak prevention pattern now clearly documented and tested
  - No API changes needed (cleanup already existed but was undocumented)

- **CLI Subcommand Renamed**: `exec` -> `run`:
  - `numchuck run` replaces `numchuck exec` for consistency with common CLI conventions
  - Updated all documentation (README, CLAUDE.md, CHANGELOG.md, architecture.md)
  - Updated tests and Makefile
  - Backward compatibility can be added if needed

- **Build System Updates**:
  - Makefile now uses `uv` for all Python operations
  - `make install` -> `uv sync --reinstall-package numchuck`
  - `make test` -> `uv run pytest` (uses pyproject.toml config)
  - `make repl` -> `uv run python -m numchuck repl`
  - pytest configuration in pyproject.toml to skip thirdparty/

- **Module Documentation**:
  - Added comprehensive docstring to `src/numchuck/__init__.py`
  - Documents exception types and when they're raised
  - Includes usage examples
  - Clear error handling contract

- **Bare Except Clauses** (Code Quality):
  - Fixed all 15 remaining bare except clauses in TUI code
  - Replaced with specific exception types: RuntimeError, AttributeError, ValueError, etc.
  - Improved error handling in completion handlers
  - Better error handling in UI display code (shred tables, status bars)
  - Prevents masking of critical exceptions (KeyboardInterrupt, SystemExit)

- **Type Stubs** (`src/numchuck/__init__.pyi`):
  - Complete type annotations for all public APIs
  - ChucK class with all methods typed
  - Module-level functions with signatures
  - All constants declared with types
  - Enables IDE autocomplete and type checking with mypy
  - ~200 lines of comprehensive type hints

- **CI/CD Pipeline** (`.github/workflows/ci.yml`):
  - Multi-platform testing (Ubuntu, macOS, Windows)
  - Python 3.9-3.13 support matrix
  - Automated build and test on push/PR
  - Lint job with ruff and mypy
  - Wheel building with cibuildwheel
  - Coverage reporting with codecov
  - Exit code verification for clean test runs

- **API Documentation Structure** (`docs/api/`):
  - Sphinx configuration with autodoc and napoleon
  - RTD theme setup
  - Complete ChucK class reference
  - Quick start guide and examples
  - Build requirements and instructions
  - Intersphinx mapping to Python/NumPy docs

- **Version Management** (`src/numchuck/_version.py`):
  - Single source for version number
  - Imported by `__init__.py` for `__version__` and `__version_info__`
  - Eliminates version duplication across the codebase
  - Follows Python packaging best practices

- **Shell Completion Support** (`completions/`):
  - Bash completion script (`numchuck-completion.bash`)
  - Zsh completion script (`numchuck-completion.zsh`)
  - Complete all subcommands: edit, repl, run, version, info
  - Complete command-line options for each subcommand
  - Complete `.ck` file paths automatically
  - Complete project names from `~/.numchuck/projects/`
  - Suggest common sample rates and channel counts
  - Installation instructions in `completions/README.md`

- **Performance Benchmarks** (`benchmarks/`):
  - `benchmark_simple.py` - Core performance measurements
  - Benchmarks code compilation speed (ops/sec)
  - Benchmarks audio rendering throughput (MB/s)
  - Benchmarks global variable access latency
  - Benchmarks event signaling performance
  - Comprehensive README with usage examples and performance targets
  - Baseline measurements for performance regression detection

- **Integration Tests** (`tests/test_integration.py`):
  - 15 comprehensive end-to-end workflow tests
  - TestLiveCodingWorkflow - Spork/replace/remove cycles
  - TestGlobalCommunication - Python-ChucK variable and event communication
  - TestAudioProcessingWorkflows - Offline rendering and real-time transitions
  - TestFileWorkflows - File compilation and multi-file scenarios
  - TestVMLifecycle - VM initialization and state management
  - TestErrorRecovery - Compilation error handling and recovery
  - TestConcurrentOperations - Rapid operations and stability testing
  - Increased test count from 99 to 114 tests

### Changed

- **Test Suite Improvements**:
  - Total tests increased from 96 to 114 (+18 tests)
  - Added 15 comprehensive integration tests
  - Added 3 event listener cleanup tests
  - All tests pass with clean exit (exit code 0)
  - pytest config excludes thirdparty/ and other non-test directories
  - Comprehensive end-to-end workflow coverage

- **Multi-Tab Editor** (`numchuck edit`):
  - Full-screen ChucK editor with syntax highlighting
  - Multi-tab support: Ctrl-T (new), Ctrl-W (close), Ctrl-N/Ctrl-P (navigate)
  - F5 or Ctrl-R to spork (compile and run current buffer)
  - F6 to replace running shred with current buffer
  - Ctrl-O to open files with interactive dialog
  - Ctrl-S to save files
  - Ctrl-A to start audio
  - Tab names show shred IDs after sporking (e.g., `bass-1.ck`)
  - Project versioning integration
  - F1/F2/F3 for help/shreds/log windows
  - Ctrl-Q for clean exit with proper resource cleanup
  - Implemented in `tui/editor.py` (~410 lines)

- **Project Versioning System** (`tui/project.py`):
  - Automatic file versioning for livecoding sessions
  - Versioning scheme: `file.ck` -> `file-1.ck` (spork) -> `file-1-1.ck` (replace)
  - Stored in `~/.numchuck/projects/<project_name>/`
  - Tracks spork and replace operations with shred IDs
  - Chronological timeline support with modification times
  - `ProjectVersion` class for parsing and generating versioned filenames
  - `Project` class for managing project directories and version history
  - Complete test coverage in `test_project_versioning.py` (10 tests)

- **Shared TUI Base Class** (`tui/common.py`):
  - `ChuckApplication` base class for editor and REPL
  - Common key bindings: F1 (help), F2 (shreds), F3 (log), Ctrl-Q (exit)
  - Reusable UI components: help window, shreds table, log window
  - Centralized ChucK instance and session management
  - Proper cleanup with circular reference breaking (no memory leaks)

- **Command-Line Execution Mode** (`numchuck run`):
  - Non-interactive file execution from command line
  - Multiple file support
  - Duration parameter: `--duration N` runs for N seconds then exits
  - Silent mode: `--silent` runs without audio (useful for testing)
  - Custom sample rate: `--srate N`
  - Custom channel count: `--channels N`
  - Signal handling for graceful shutdown (Ctrl-C)
  - Implemented in `cli/executor.py` (~120 lines)

- **Subcommand-Based CLI** (`cli/main.py`):
  - `numchuck edit [files...] [--project name] [--start-audio]` - Launch editor
  - `numchuck repl [files...] [--project name] [--start-audio]` - Launch REPL
  - `numchuck run <files...> [options]` - Execute files
  - `numchuck version` - Show version information
  - `numchuck info` - Show ChucK and numchuck info
  - `numchuck tui` - Backward compatibility alias for repl
  - Comprehensive argument parsing with help text
  - Command handlers in separate module
  - ~220 lines of clean CLI code

- **Chuck-Style REPL Commands**:
  - `add <file>` or `+ <file>` - Spork a file as new shred
  - `remove <id>` or `- <id>` - Remove shred by ID
  - `remove all` or `- all` - Remove all shreds
  - `replace <id> <file>` - Replace shred with code from file
  - `status` - Show VM status (shreds, audio, now time)
  - `time` - Show current ChucK time
  - Consistent with chuck executable command style
  - Updated parser to support word-based commands
  - Shortcut symbols still supported for compatibility

- **REPL File Loading on Startup**:
  - Load ChucK files on REPL startup: `numchuck repl file1.ck file2.ck`
  - Files are automatically sporked before entering interactive mode
  - Works with project versioning when `--project` specified
  - Implemented in `tui/repl.py` run() method

- **Test Suite Expansion**:
  - `test_project_versioning.py` - 10 tests for versioning system
  - `test_cli.py` - 10 tests for CLI argument parsing
  - **Total: 93 tests, 100% passing**
  - Comprehensive coverage of new features
  - No regressions in existing tests

- **Full-Screen REPL Application**:
  - Converted to full-screen `prompt_toolkit` Application with stable layout
  - Mouse support enabled for scrolling in log/help windows
  - No layout disruption from ChucK VM or error messages
  - Clean separation of input, output, status, and auxiliary windows

- **Topbar for Active Shreds**:
  - Minimal topbar displaying shred IDs only
  - Format: `Shreds: [1] [2] [3]  (F2: table)`
  - Symmetrical with bottom status toolbar
  - Gap between topbar and input area for clean layout
  - Topbar updates automatically when shreds are added/removed

- **Shreds Table Window**:
  - Toggle detailed shreds table with F2
  - Displays comprehensive shred information in tabular format
  - Columns: ID, Name (filename or code snippet), Time (ChucK VM time when launched)
  - Shows only filename for file shreds (not full path)
  - Time displayed relative to audio thread start (ChucK VM samples/seconds)
  - Auto-formats time: samples (< 1s), seconds, minutes, hours
  - Styled with cyan on dark blue (matching WebChucK aesthetic)
  - Updates in real-time when toggled
  - Clean, aligned table with Unicode separators

- **Help Window**:
  - Toggle help display with F1 or `help` command
  - Two-column compact layout fitting in 20 lines
  - Non-scrollable, static content
  - Displays all REPL commands and keyboard shortcuts
  - Appears above status bar without disrupting layout

- **Log Window**:
  - Toggle ChucK VM log with Ctrl+L
  - Scrollable display of last 100 VM messages
  - Captures all stdout/stderr from ChucK VM
  - Auto-scrolls to bottom for new messages
  - Mouse and keyboard scrolling support
  - Distinct styling (lighter gray) from help window

- **Edit Shred Command**:
  - Edit and replace running shreds with `edit <id>` (e.g., `edit 1`, `edit 2`)
  - Uses ChucK shred IDs consistently with remove command
  - Opens shred source in $EDITOR
  - Automatically replaces shred with modified code on save
  - Converts relative file paths to absolute paths for editing

- **Error Display Bar**:
  - Errors shown in dedicated red error bar above log/help windows
  - Appears only when there's an error (conditional display)
  - All errors routed through error bar instead of `print()` calls
  - Prevents layout disruption in full-screen mode
  - Auto-clears on next command
  - Handles unknown commands gracefully

- **ChucK Language Module** (`src/numchuck/chuck_lang.py`):
  - Single source of truth for all ChucK language elements
  - Complete sets: KEYWORDS, TYPES, OPERATORS, TIME_UNITS, UGENS, STD_CLASSES
  - 80+ UGens including oscillators, filters, reverbs, STK instruments, chugins
  - Standard library: MATH_FUNCTIONS, STD_FUNCTIONS
  - REPL_COMMANDS for command completion
  - Helper functions: `is_keyword()`, `is_type()`, `is_ugen()`, `is_builtin()`, `get_category()`
  - Comprehensive documentation of ChucK language specification

- **ChucK Code Completion in REPL**:
  - Tab completion for ChucK keywords (if, while, for, class, fun, etc.)
  - Tab completion for ChucK types (int, float, time, dur, etc.)
  - Tab completion for UGens (SinOsc, LPF, JCRev, ADSR, etc.)
  - Tab completion for standard library (Math, Std, FileIO, MidiIn, etc.)
  - Visual distinction with 'ChucK' metadata in completion menu
  - Context-aware: completes word under cursor
  - REPL commands retain first priority
  - Updates help text to document code completion

### Changed

- **REPL Architecture Refactoring**:
  - Migrated from `PromptSession` to full-screen `Application` with custom layout
  - Supports complex layouts (topbar, gap, input area, bottom toolbar)
  - Eliminated `print()` calls for state-changing commands to prevent layout disruption
  - Silent operation for audio control and shred management
  - Better control over rendering and event handling
  - Enables future enhancements (multiple panes, advanced UI features)

- **ChucK Lexer Refactoring**:
  - Now uses `chuck_lang` module as source of truth
  - Dynamically builds patterns from KEYWORDS, TYPES, UGENS, STD_CLASSES, TIME_UNITS
  - Removed hardcoded language element lists
  - Moved `dac`, `adc`, `blackhole` from keywords to UGens for correct highlighting

- **REPL Command Completion**:
  - Now uses `chuck_lang.REPL_COMMANDS` instead of hardcoded list
  - Ensures consistency across all components

- **Shreds Table Display**:
  - Updated to show parent folder + filename instead of just filename
  - Widened table from 60 to 78 characters for better readability
  - Elapsed time column shows time since shred was sporked (not raw VM samples)
  - Format: `parentfolder/file.ck` with up to 56 characters for name

### Fixed

- **Shreds Table Display Bug**:
  - Fixed shreds table showing source code instead of filenames (both REPL and editor)
  - Table now correctly displays filename from `info['name']` instead of `info['source']`
  - Extracts just filename or parent/filename from full path for cleaner display
  - Elapsed time calculated correctly from current VM time minus spork time

- **REPL Exit Crash with Audio**:
  - Fixed segmentation fault when pressing Ctrl-Q with audio running
  - Cleanup now properly calls `stop_audio()` before `shutdown_audio()`
  - Added proper error handling for each cleanup step
  - Shreds are now removed before stopping audio to prevent callback issues

- **Editor File Open Dialog**:
  - Fixed Ctrl-O crash caused by nested event loop conflict
  - Implemented proper floating dialog with `CompletionsMenu` support
  - Tab completion now works like standard shell completion (inserts common prefix first)
  - Added custom key bindings to prevent Tab from being used for focus navigation
  - Dialog properly cleans up floats list on close

- **Editor Dynamic Tab Switching**:
  - Fixed opened files not appearing after Ctrl-O
  - Layout now uses `DynamicContainer` to update editor content when switching tabs
  - New tabs are automatically focused after opening

### Technical Details

- All 93 tests pass (73 original + 20 new)
- ChucK lexer tests verify correct categorization of language elements
- Completion system preserves REPL command priority
- `chuck_lang` module provides forward compatibility for language specification updates
- Zero memory leaks with proper cleanup and circular reference breaking

## [0.1.3]

### Added

- **ChucK Pygments Lexer** (`src/numchuck/cli/chuck_lexer.py`):
  - Complete syntax highlighting for ChucK language
  - Recognizes ChucK operators (`=>`, `+=>`, `@=>`, etc.)
  - Time duration literals (`100::ms`, `1::second`, etc.)
  - 80+ built-in UGens (SinOsc, LPF, ADSR, JCRev, dac, etc.)
  - Keywords, types, standard library (Math, Std, Machine)
  - Comments, strings, numbers (int, float, hex)
  - Integrated into REPL for syntax-highlighted input
  - 16 comprehensive tests in `tests/test_chuck_lexer.py`
  - Documentation: `docs/CHUCK_LEXER.md`

- **Centralized Path Management** (`src/numchuck/cli/paths.py`):
  - `get_numchuck_home()` - Returns `~/.numchuck`
  - `get_snippets_dir()` - Returns `~/.numchuck/snippets`
  - `get_history_file()` - Returns `~/.numchuck/history`
  - `get_sessions_dir()`, `get_logs_dir()`, `get_projects_dir()`, `get_config_file()` - Future directories
  - `ensure_numchuck_directories()` - Creates directory structure
  - `list_snippets()`, `get_snippet_path()` - Snippet utilities

- **REPL Enhancements**:
  - `cls` command - Clear screen without affecting VM state
  - Colored prompt `[=>]` with orange brackets and green chuck operator
  - Screen clears on REPL startup for clean interface
  - Prompt updated to `[=>]` matching ChucK logo
  - **Smart Enter mode (enabled by default)**:
    - Enter on REPL commands (quit, help, +, -, etc.) submits immediately
    - Enter on ChucK code inserts newline (multiline editing)
    - Esc+Enter always submits code
    - Continuation prompt shows `...` for multiline input
  - **Direct ChucK code compilation** - Multiline code automatically detected and compiled
  - Auto-detection based on ChucK markers (=>, ;, {, newlines)
  - No need for special commands or mode switching

- **Documentation**:
  - `docs/numchuck_home.md` - Complete guide to `~/.numchuck/` directory structure
  - `docs/chuck_lexer.md` - ChucK lexer usage and implementation guide

### Changed

- **Directory Structure Migration**:
  - `~/.chuck_repl_history` -> `~/.numchuck/history`
  - `~/.chuck_snippets/` -> `~/.numchuck/snippets/`
  - REPL now creates full `~/.numchuck/` directory structure on startup
  - Updated all code to use new path utilities from `paths.py`
  - Updated `.gitignore` to ignore `~/.numchuck/` instead of individual files

- **REPL Improvements**:
  - REPL version display updated to show "PyChucK REPL v0.1.1"
  - Help text updated with `cls` command under "Screen:" section
  - Help text updated with "Multiline Input (Smart Enter Mode):" section
  - Tab completion includes `cls` command (removed `ml`)
  - README.md mentions ChucK syntax highlighting feature
  - **prompt-toolkit is now a required dependency** (no longer optional)
  - Simplified REPL initialization by removing readline/libedit fallback code
  - REPL mode display simplified (removed mode indicator)
  - **Multiline editing enabled by default** (no special mode needed)
  - **Smart Enter mode**: Context-aware Enter behavior
  - Added prompt continuation (`...`) for multiline input
  - Auto-detection of ChucK code (checks for `=>`, `;`, `{`, or newlines)
  - Parser suppresses "Unknown command" for ChucK code patterns
  - `smart_enter` parameter in ChuckREPL constructor (defaults to True)

- **Command-line interface**:
  - `python -m numchuck tui` now launches vanilla REPL directly
  - Added `--start-audio` flag to automatically start audio on REPL startup
  - Added `--no-smart-enter` flag to disable smart Enter mode
  - Removed `--rich`, `--simple`, `--basic` command-line flags
  - `tui.py` simplified to only launch vanilla REPL
  - Updated README.md to reflect vanilla REPL as sole interface

### Removed

- **Textual/Rich TUI implementation removed**:
  - Removed `tui_rich.py`, `tui_simple.py`, `tui_basic.py` implementations
  - Removed `tui_rich.tcss` stylesheet
  - Removed `widgets/` directory and all custom widgets
  - Removed `test_textual_minimal.py` test file
  - Removed textual-related documentation files:
    - `docs/dev/DEBUG_BLACK_SCREEN.md`
    - `docs/dev/MOUSE_FIX.md`
    - `docs/dev/RICH_TUI_IMPROVEMENTS.md`
    - `docs/dev/TUI_README.md`

- **Old Path Structure**:
  - Removed references to `~/.chuck_snippets/`
  - Removed references to `~/.chuck_repl_history`

- **Readline/libedit fallback code removed**:
  - Removed ~85 lines of readline/libedit fallback code from `repl.py`
  - Removed `use_prompt_toolkit` and `use_readline` flags
  - Removed conditional input prompt logic
  - Simplified multiline mode to only use prompt-toolkit

- **Multiline mode command removed**:
  - Removed `ml` command (multiline mode is now always enabled)
  - Removed `_multiline_mode()` method from REPL
  - Removed `_cmd_multiline()` from command executor
  - Removed multiline pattern from command parser
  - Removed `ml` from tab completion list

### Technical Details

- All 76 tests pass (60 original + 16 lexer tests)
- ChucK lexer follows Pygments best practices (RegexLexer)
- Colored prompt uses HTML formatting for prompt_toolkit
- Smart Enter mode uses `@Condition` decorator for dynamic multiline behavior
- Path management provides forward compatibility for sessions, logs, projects, config
- Migration guide included in `docs/PYCHUCK_HOME.md`
- prompt-toolkit is now a required dependency (imported directly, no fallbacks)
- Pygments is a dependency of prompt_toolkit, so no need to declare it separately

### Summary

Version 0.1.3 represents a major REPL overhaul focused on user experience:

**Key Improvements:**

1. **Smart multiline editing** - Context-aware Enter behavior eliminates mode switching
2. **ChucK syntax highlighting** - Full Pygments lexer for ChucK language
3. **Automatic code detection** - ChucK code is compiled, commands are executed
4. **Unified directory structure** - All user data in `~/.numchuck/`
5. **Required prompt-toolkit** - Simplified codebase, better UX
6. **CLI options** - `--start-audio` and `--no-smart-enter` flags

The REPL now provides a modern, intuitive interface for both quick REPL commands and multiline ChucK programming.

---

## [0.1.2]

### Added

#### Global Variable Management

- **Bidirectional Python/ChucK communication** via ChucK globals manager:
  - `set_global_int()`, `set_global_float()`, `set_global_string()` - Set primitive globals from Python
  - `get_global_int()`, `get_global_float()`, `get_global_string()` - Get primitives via async callbacks
  - `set_global_int_array()`, `set_global_float_array()` - Set entire arrays
  - `get_global_int_array()`, `get_global_float_array()` - Get arrays via callbacks
  - `set_global_int_array_value()`, `set_global_float_array_value()` - Set individual array elements by index
  - `set_global_associative_int_array_value()`, `set_global_associative_float_array_value()` - Set associative array (map) values by key
  - `get_all_globals()` - List all global variables as (type, name) tuples
  - **Use case**: Real-time parameter control, data exchange between Python and ChucK shreds

#### Global Event Signaling

- **Event-driven Python/ChucK communication**:
  - `signal_global_event()` - Wake one waiting shred on global event
  - `broadcast_global_event()` - Wake all waiting shreds on global event
  - `listen_for_global_event()` - Register Python callback for ChucK events (returns listener ID)
  - `stop_listening_for_global_event()` - Unregister callback by ID
  - **Use case**: Trigger musical events from Python, receive notifications from ChucK

#### Shred Management & Introspection

- **Advanced shred control and debugging**:
  - `remove_shred()` - Remove shred by ID
  - `get_all_shred_ids()` - List all running shreds
  - `get_ready_shred_ids()` - List ready (non-blocked) shreds
  - `get_blocked_shred_ids()` - List blocked shreds
  - `get_last_shred_id()` - Get most recently sporked shred ID
  - `get_next_shred_id()` - Query what next shred ID will be
  - `get_shred_info()` - Get detailed shred info (ID, name, running status, done status)
  - **Use case**: Live coding workflows, debugging, monitoring VM state

#### VM Control Messages

- **Fine-grained VM state management**:
  - `clear_vm()` - Remove all shreds
  - `clear_globals()` - Clear global variables without removing shreds
  - `reset_shred_id()` - Reset shred ID counter
  - `replace_shred()` - Hot-swap running shred with new code (returns new shred ID)
  - **Use case**: Live coding, iterative development, performance workflows

#### Additional Parameter Constants

- **8 new ChucK parameter constants** for advanced configuration:
  - `PARAM_OTF_PRINT_WARNINGS` - Print on-the-fly compiler warnings
  - `PARAM_IS_REALTIME_AUDIO_HINT` - Hint for real-time audio mode
  - `PARAM_COMPILER_HIGHLIGHT_ON_ERROR` - Syntax highlighting in error messages
  - `PARAM_TTY_COLOR` - Enable color output in terminal
  - `PARAM_TTY_WIDTH_HINT` - Terminal width hint for formatting
  - `PARAM_IMPORT_PATH_SYSTEM` - System import search paths
  - `PARAM_IMPORT_PATH_PACKAGES` - Package import search paths
  - `PARAM_IMPORT_PATH_USER` - User import search paths

#### Callback Management & Output Control

- **Enhanced console output handling**:
  - `set_chout_callback()` - Capture ChucK console output (chout)
  - `set_cherr_callback()` - Capture ChucK error output (cherr)
  - `set_stdout_callback()` - Capture global stdout (static)
  - `set_stderr_callback()` - Capture global stderr (static)
  - `toggle_global_color_textoutput()` - Enable/disable color output
  - `probe_chugins()` - Print info on all loaded chugins
  - **Use case**: Custom logging, GUI integration, debugging

#### Testing

- **14 new comprehensive tests** (60 total, 100% pass rate):
  - **Global variables**: 6 tests covering primitives, arrays, associative arrays
  - **Global events**: 3 tests for signal, broadcast, error handling
  - **Shred management**: 5 tests for removal, introspection, VM control
  - All tests use audio cycle processing for proper message queue handling
  - Helper function `run_audio_cycles()` for reliable async operation testing

### Changed

- **Type stub file (`_numchuck.pyi`)** updated with all new methods:
  - 30+ new method signatures with full type annotations
  - Callback types use `Callable` with proper signatures
  - Return types for introspection methods (`list[int]`, `dict[str, Any]`, etc.)
  - Complete docstrings for all new methods

### Technical Details

#### Thread-Safe Callback Architecture

- **Global callback storage** with mutex protection:
  - `g_callbacks` map stores Python callables by ID
  - `g_callback_mutex` ensures thread-safe access
  - `store_callback()`, `get_callback()`, `remove_callback()` helper functions
  - Automatic cleanup for one-shot callbacks (get operations)
  - Persistent storage for event listeners (until explicitly removed)

- **C++ callback wrappers** with GIL management:
  - `cb_get_int_wrapper()`, `cb_get_float_wrapper()`, `cb_get_string_wrapper()`
  - `cb_get_int_array_wrapper()`, `cb_get_float_array_wrapper()`
  - `cb_event_wrapper()` for persistent event listeners
  - All wrappers use `nb::gil_scoped_acquire` for Python callback invocation

#### Message Queue Integration

- **Proper ChucK VM integration**:
  - Global operations use `Chuck_Globals_Manager` message queue
  - VM operations use `Chuck_VM::queue_msg()` and `process_msg()`
  - All operations validated with `!self.vm()` and `!self.globals()` checks
  - Error handling with descriptive `RuntimeError` messages

#### Code Architecture Improvements

- Added `chuck_globals.h` and `chuck_vm.h` includes
- Added `<unordered_map>` and `<memory>` for callback storage
- Event listener IDs returned to Python for lifecycle management
- `replace_shred()` compiles code with `count=0` then sends `CK_MSG_REPLACE`

### Design Decisions

- **Asynchronous global variable gets** via callbacks (not blocking):
  - ChucK's message queue is processed during audio cycles
  - Blocking would deadlock if VM not running audio
  - Callback pattern matches ChucK's threading model
  - Consistent with Max/MSP chuck~ external architecture

- **Event listener persistence**:
  - Event callbacks stored until explicitly removed
  - Allows Python to react to ChucK events continuously
  - Listener ID returned for lifecycle control
  - `listen_forever` parameter controls one-shot vs persistent behavior

### Security

- All global variable operations validated before queue insertion
- Shred ID bounds checking in `get_shred_info()`
- VM/globals manager null pointer checks before operations
- Callback ID validation prevents accessing invalid callbacks

### Performance

- Callback lookup: O(1) via `unordered_map`
- Minimal overhead for global variable operations (message queue only)
- Event listeners don't remove callbacks on trigger (persistent)
- No memory leaks with proper callback cleanup

### Inspired By

Implementation based on analysis of `chuck_tilde.cpp` (Max/MSP external):

- Global variable management patterns (lines 1398-1497, 1631-1783)
- Event signaling architecture (lines 1506-1526, 1785-1801)
- Shred introspection methods (lines 662-710, 1255-1269)
- VM message passing (lines 884-904, 1100-1253)

---

## [0.1.1]

### Added

- Comprehensive architecture documentation in `ARCHITECTURE.md`
  - System architecture diagrams and data flow
  - Component details and responsibilities
  - Current limitations and future improvements
  - Thread safety analysis
  - Performance characteristics
  - Security considerations

- **Extensive error handling test suite** (`tests/test_error_handling.py`):
  - **30 new comprehensive tests** covering all error paths
  - **Parameter validation tests** (4 tests):
    - Empty code/file path rejection
    - Zero count validation
  - **Initialization state tests** (4 tests):
    - Compilation requires initialization
    - Audio processing requires initialization
    - Start audio requires initialization
  - **Buffer validation tests** (10 tests):
    - Negative/zero frame validation
    - Input/output buffer size mismatch detection
    - Wrong dtype handling (float64 vs float32)
    - Multidimensional array rejection
    - Zero input channels with input data
    - Large buffer stress test (10 seconds of audio)
  - **Audio system validation tests** (3 tests):
    - Zero sample rate rejection
    - Zero channels validation
    - Zero buffer size rejection
  - **Compilation error tests** (4 tests):
    - Invalid ChucK syntax (returns False, not crash)
    - Non-existent file handling
    - Undefined class detection
    - Type mismatch errors
  - **Edge cases and boundary conditions** (5 tests):
    - Multiple shred compilation (count > 1)
    - Multiple init calls handling (returns 0 when already initialized)
    - Sequential compile and remove cycles
    - Audio stop/shutdown without start (safe, no crash)
  - **Test coverage**: 45 total tests (15 original + 30 new), 100% pass rate
  - All tests validate descriptive error messages and proper exception types

- **Python example scripts** (`examples/python/` - 9 comprehensive examples):
  - **01_basic_sine.py**: Real-time sine wave playback (basic setup)
  - **02_offline_render.py**: Offline rendering to numpy arrays with frequency sweep, optional plotting/WAV export
  - **03_load_chuck_file.py**: Loading external .ck files from `examples/basic/`
  - **04_multiple_shreds.py**: Running multiple concurrent shreds, harmonic series, dynamic management
  - **05_bitcrusher_chugin.py**: Using Bitcrusher effect plugin with parameter sweeping
  - **06_reverb_chugin.py**: Using GVerb reverb plugin for spatial effects
  - **07_parameter_control.py**: ChucK VM configuration and parameter inspection
  - **08_advanced_synthesis.py**: FM synthesis with filtering, envelopes, and melodic sequences
  - **09_sequenced_shreds.py**: Time-sequenced shred playback, building composition layer by layer with rhythmic patterns
  - **README.md**: Comprehensive guide with usage patterns, troubleshooting, and learning path
  - All examples include detailed docstrings and comments
  - Progressive learning path from basic to advanced techniques
  - Demonstrates both real-time and offline processing
  - Shows chugin integration and file loading

### Changed

- **Type stub file (`_numchuck.pyi`)** completely rewritten to match actual implementation
  - Fixed incorrect method signatures (module functions vs class methods)
  - Added all parameter constants
  - Added comprehensive docstrings
  - Proper static type checking support
- **License classifier** corrected from invalid `GPL3 License` to `GNU General Public License v2 (GPLv2)`
- Added development status classifier: `Development Status :: 3 - Alpha`
- Added Python version classifiers (3.8-3.12)

### Fixed

#### Critical Fixes

- **Input validation and error handling** throughout C++ bindings:
  - Added `validate_audio_buffer()` template function for numpy array validation
  - Validates array dimensions, sizes, and types before passing to ChucK
  - `compile_code()` now validates non-empty code, count > 0, and initialization state
  - `compile_file()` now validates non-empty path, count > 0, and initialization state
  - `run()` now validates initialization, num_frames > 0, and correct buffer sizes
  - All validation errors throw descriptive Python exceptions

- **Audio callback architecture** improved for safety:
  - Replaced global `g_chuck_for_audio` pointer with `userData` parameter mechanism
  - ChucK instance passed directly to audio callback via `userData`
  - Added mutex protection for audio state (`g_audio_mutex`)
  - Eliminated dangling pointer risks

- **RAII resource management** for audio system:
  - Created `AudioContext` class with automatic cleanup
  - Destructor ensures cleanup on all paths (success/failure/exception)
  - Deleted copy/move constructors for single ownership semantics
  - Global audio context managed via `std::unique_ptr`
  - `start_audio()` now performs cleanup on initialization/start failures
  - `stop_audio()` and `shutdown_audio()` properly manage lifecycle

- **Test suite bug** caught by new validation:
  - Fixed `test_chuck_now` using wrong dtype (float64 -> float32)
  - Fixed `test_chuck_now` missing channel configuration
  - All 15 tests now pass

### Security

- Input validation prevents buffer overruns and segmentation faults
- Array dimension and size checks before native code access
- Initialization state checked before operations
- Thread-safe audio operations with mutex protection

### Technical Details

- Simplified `validate_audio_buffer()` using template parameters instead of runtime dtype checks
- Type safety enforced at compile-time via nanobind's typed ndarrays
- Writable vs read-only buffers enforced by nanobind template parameters
- Mutex: `std::mutex` for audio state protection
- Smart pointers: `std::unique_ptr<AudioContext>` for resource ownership

### Design Decisions

- **Single global audio context**: Only one ChucK instance can have real-time audio active at a time
  - This is **intentional and appropriate** - ChucK VM handles concurrency via shreds
  - Multiple audio streams should use multiple shreds within one ChucK instance
  - Running multiple ChucK instances is inefficient and unnecessary
  - Documented in `docs/ARCHITECTURE.md` with rationale and correct usage patterns

## [0.1.0]

### Added

#### Core Features

- Initial Python bindings for ChucK using nanobind
- Complete ChucK class wrapper with all core functionality:
  - Parameter configuration (sample rate, channels, VM settings)
  - Code compilation from strings with `compile_code()`
  - **File compilation** with `compile_file()` - Load and run `.ck` files
  - Audio processing with numpy array integration (synchronous)
  - Shred management and VM control
  - Time tracking and status queries

#### Real-Time Audio (RtAudio)

- **Asynchronous audio playback** using RtAudio (cross-platform):
  - `start_audio()` - Start real-time audio stream
  - `stop_audio()` - Stop audio stream
  - `shutdown_audio()` - Shutdown audio system
  - `audio_info()` - Get audio system information
- **Offline audio processing** with numpy array integration
- Platform support:
  - macOS: CoreAudio backend
  - Windows: DirectSound/WASAPI (prepared, not tested)
  - Linux: ALSA/JACK (prepared, not tested)

#### Plugin Support (Chugins)

- **Chugin loading and usage**:
  - `PARAM_CHUGIN_ENABLE` - Enable/disable chugin support
  - `PARAM_USER_CHUGINS` - Set chugin search paths
- Pre-built chugins included in `examples/chugins/`:
  - Effects: Bitcrusher, ABSaturator, FoldbackSaturator, etc.
  - Filters: Elliptic, FIR, etc.
  - Delays: ExpDelay, ConvRev, etc.
  - Utilities: AbletonLink, Binaural, AmbPan, etc.

#### Examples and Resources

- **ChucK example files** in `examples/`:
  - `examples/basic/` - Basic synthesis examples
  - `examples/effects/` - Audio effect demonstrations
  - `examples/stereo/` - Stereo processing examples
  - More specialized examples (convrev, deep, extend, etc.)
- All examples can be loaded with `compile_file()`

#### Testing

- Comprehensive test suite (15 tests):
  - Basic functionality tests (7 tests)
  - Real-time audio tests (2 tests)
  - File loading and chugin tests (6 tests)
- Test coverage:
  - Version detection and initialization
  - Code and file compilation
  - Audio processing (sync and async)
  - Parameter configuration
  - Chugin loading
  - Multiple concurrent shreds
  - Error handling

#### Build System and Documentation

- Support for all ChucK parameter constants:
  - Core parameters (PARAM_SAMPLE_RATE, PARAM_INPUT_CHANNELS, PARAM_OUTPUT_CHANNELS)
  - VM configuration (PARAM_VM_ADAPTIVE, PARAM_VM_HALT, etc.)
  - Path configuration (PARAM_WORKING_DIRECTORY, PARAM_CHUGIN_ENABLE, PARAM_USER_CHUGINS)
- Float32 audio buffer support with interleaved layout
- CMake-based build system with scikit-build-core
- RtAudio and chuck_audio.cpp integrated into extension module
- Chugin build system integration
- Makefile with build, test, and clean targets
- Complete API documentation in README.md with examples:
  - Real-time audio examples
  - Offline rendering examples
  - File loading examples
  - Chugin usage examples
  - Multiple shred examples

### Technical Details

- ChucK core version: 1.5.5.3-dev (chai)
- Audio sample format: float32 (SAMPLE type)
- Buffer layout: Interleaved (e.g., [L0, R0, L1, R1, ...])
- Default sample rate: 44100 Hz
- Build system: CMake 3.15+ with Xcode generator on macOS
- Real-time audio: RtAudio with CoreAudio backend on macOS

### Fixed

- Float32 vs float64 audio buffer compatibility
- ChucK VM time advancement synchronization
- C source file compilation in ChucK core library
- Extension module output directory configuration
- Lambda capture issues in audio callback (using static function instead)

### Notes

- Requires numpy for audio processing
- macOS support with CoreAudio/CoreMIDI frameworks
- ChucK code must explicitly advance time for continuous audio generation
- Real-time audio plays asynchronously in background thread
