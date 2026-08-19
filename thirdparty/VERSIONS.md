# Vendored dependencies

These trees are **vendored**, not git submodules: their sources are committed
directly into this repository. There is no `.gitmodules`, and `git clone`
without `--recursive` gets everything needed to build.

Why vendored rather than submodules: each tree carries numchuck-local content
that upstream knows nothing about (the CMakeLists.txt files, the pre-generated
bison/flex output committed for the Windows build, chugins that do not come
from ccrma/chugins at all). `scripts/update.sh` documents the merge rules and
refreshes each tree; local edits to upstream-owned files live in
`scripts/patches/` so they survive an update.

The consequence of vendoring is that nothing records where a tree came from.
That is what this file is for. Keep it current when running `scripts/update.sh`
— the script prints the upstream short SHA of each clone it makes.

| Tree | Upstream | Version | Ref / commit | Notes |
| --- | --- | --- | --- | --- |
| `chuck/` | https://github.com/ccrma/chuck | 1.5.5.9-dev (chai) | *unrecorded* | A development snapshot, not a tagged release. Version read from `core/chuck_def.h`. |
| `chugins/` | https://github.com/ccrma/chugins | — | *unrecorded* | 49 chugins. AbletonLink, AudioUnit, CLAP, Fauck, PdPatch and VST3 come from https://github.com/shakfu/my-chugins, not from ccrma. |
| `nanobind/` | https://github.com/wjakob/nanobind | 2.9.3-dev1 | *unrecorded* | Version read from `pyproject.toml`. |
| `mongoose/` | https://github.com/cesanta/mongoose | 7.9 | *unrecorded* | Two files (`mongoose.c`, `mongoose.h`). This is the component exposed to the network by the web IDE — see below. |

## Open items

- **The `ref / commit` column is unrecorded for every tree.** These were vendored
  before this file existed, so the upstream commits are not recoverable from the
  repository. Fill each row in on the next `scripts/update.sh` run, which prints
  `upstream <tree> at <sha>` for every clone.
- **mongoose 7.9 is several years behind upstream.** It serves the web IDE, so
  it is the only vendored component that parses untrusted input from a socket.
  Worth reviewing against upstream's release notes before the next release.
- **chuck is pinned to a `-dev` build.** Fine for tracking upstream closely, but
  it means the ChucK version numchuck reports does not correspond to any ChucK
  release users can consult.

## Local patches

`scripts/patches/` holds changes to upstream-owned files that must be re-applied
after every update; `scripts/update.sh` applies them automatically and fails
loudly if one no longer applies.

| Patch | Applies to | Purpose |
| --- | --- | --- |
| `0001-windows-shutdown-delay.patch` | `chuck/` | See `docs/windows_fix.md`. |
