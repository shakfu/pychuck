# Chugins Distribution Proposal

This document outlines options for distributing ChucK plugins (chugins) with the numchuck package.

## Background

Chugins are compiled native plugins (`.chug` files) that extend ChucK with additional UGens, effects, and functionality. Currently, numchuck builds chugins locally to `examples/chugins/` but does not include them in the distributed wheel.

### Current State

- 37 chugins built from `thirdparty/chugins/`
- Output to `examples/chugins/` during local build
- NOT bundled in PyPI wheel
- Users must build from source to get chugins
- Tests for chugins are skipped in CI

### The macOS Gatekeeper Problem

Distributing pre-built binaries via PyPI triggers macOS Gatekeeper issues:

1. Files downloaded from internet receive quarantine flag (`com.apple.quarantine`)
2. Gatekeeper checks quarantined binaries on first load
3. Ad-hoc signed binaries (`codesign -s -`) are NOT trusted for downloaded content
4. Result: "cannot be opened because the developer cannot be verified"

**Solutions to Gatekeeper:**

| Approach | Pros | Cons |
|----------|------|------|
| Apple Developer ID + Notarization | Fully trusted, professional | $99/year, CI complexity, certificate management |
| Build at install time | No quarantine (local build) | Requires CMake + compiler |
| Runtime quarantine removal | Works without Apple account | Hacky, may fail |
| Don't bundle | Simple, current approach | Users must build manually |

## Proposed Solution: On-Demand Compilation

Build chugins on first use rather than shipping pre-built binaries.

### User Experience

```bash
# Install numchuck (fast, no compilation)
pip install numchuck

# First time using chugins
numchuck repl
[=>] SinOsc s => Bitcrusher b => dac;

# numchuck detects Bitcrusher.chug is missing
# "Building chugins for first use... (requires CMake)"
# Progress output...
# "Built 37 chugins to ~/.numchuck/chugins/"

# Subsequent uses - instant, chugins already built
```

### Package Structure

```
src/numchuck/
  chugins/
    __init__.py          # get_chugins_path(), ensure_chugins_built()
    builder.py           # ChuginBuilder class
    sources/             # Chugin source code
      Bitcrusher/
        Bitcrusher.cpp
        CMakeLists.txt
      GVerb/
        GVerb.cpp
        CMakeLists.txt
      ...
```

### Core Components

#### 1. ChuginBuilder Class

```python
# src/numchuck/chugins/builder.py

from pathlib import Path
import subprocess
import shutil
import platform

class ChuginBuilder:
    """Builds chugins from source."""

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or (Path.home() / ".numchuck" / "chugins")
        self.source_dir = Path(__file__).parent / "sources"

    def check_requirements(self) -> tuple[bool, str]:
        """Check if CMake and compiler are available."""
        # Check cmake
        if shutil.which("cmake") is None:
            return False, "CMake not found. Install from https://cmake.org"

        # Check compiler
        if platform.system() == "Darwin":
            if shutil.which("clang") is None:
                return False, "Xcode command line tools not found. Run: xcode-select --install"
        elif platform.system() == "Linux":
            if shutil.which("g++") is None:
                return False, "g++ not found. Install build-essential package."
        elif platform.system() == "Windows":
            # Check for MSVC or MinGW
            pass

        return True, "Ready to build"

    def build_all(self, progress_callback=None) -> list[str]:
        """Build all chugins. Returns list of built chugin names."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        built = []
        sources = list(self.source_dir.iterdir())

        for i, chugin_dir in enumerate(sources):
            if not chugin_dir.is_dir():
                continue

            name = chugin_dir.name
            if progress_callback:
                progress_callback(name, i + 1, len(sources))

            if self._build_one(chugin_dir):
                built.append(name)

        return built

    def _build_one(self, source_dir: Path) -> bool:
        """Build a single chugin."""
        import tempfile

        with tempfile.TemporaryDirectory() as build_dir:
            # Configure
            result = subprocess.run([
                "cmake",
                "-S", str(source_dir),
                "-B", build_dir,
                "-DCMAKE_BUILD_TYPE=Release",
            ], capture_output=True)

            if result.returncode != 0:
                return False

            # Build
            result = subprocess.run([
                "cmake", "--build", build_dir, "--config", "Release"
            ], capture_output=True)

            if result.returncode != 0:
                return False

            # Find and copy .chug file
            for chug in Path(build_dir).rglob("*.chug"):
                dest = self.output_dir / chug.name
                shutil.copy2(chug, dest)

                # Codesign on macOS
                if platform.system() == "Darwin":
                    subprocess.run([
                        "codesign", "-vf", "-s", "-", str(dest)
                    ], capture_output=True)

                return True

        return False

    def is_built(self, name: str) -> bool:
        """Check if a chugin is already built."""
        return (self.output_dir / f"{name}.chug").exists()

    def list_available(self) -> list[str]:
        """List available chugin sources."""
        return [d.name for d in self.source_dir.iterdir() if d.is_dir()]

    def list_built(self) -> list[str]:
        """List already-built chugins."""
        return [f.stem for f in self.output_dir.glob("*.chug")]
```

#### 2. Auto-Build Integration

```python
# src/numchuck/chugins/__init__.py

from pathlib import Path
from .builder import ChuginBuilder

_builder: ChuginBuilder | None = None

def get_builder() -> ChuginBuilder:
    global _builder
    if _builder is None:
        _builder = ChuginBuilder()
    return _builder

def get_chugins_dir() -> Path:
    """Get the chugins directory, building if necessary."""
    return get_builder().output_dir

def ensure_chugins_built(verbose: bool = True) -> bool:
    """Ensure chugins are built, building if necessary."""
    builder = get_builder()

    if builder.list_built():
        return True  # Already have some chugins

    ok, msg = builder.check_requirements()
    if not ok:
        if verbose:
            print(f"Cannot build chugins: {msg}")
        return False

    if verbose:
        print("Building chugins for first use...")

    def progress(name, current, total):
        if verbose:
            print(f"  [{current}/{total}] {name}")

    built = builder.build_all(progress_callback=progress)

    if verbose:
        print(f"Built {len(built)} chugins to {builder.output_dir}")

    return len(built) > 0
```

#### 3. CLI Commands

```bash
# Build all chugins
numchuck chugins build

# List available and built status
numchuck chugins list

# Rebuild all (clean + build)
numchuck chugins rebuild

# Show chugins directory
numchuck chugins path
```

```python
# src/numchuck/cli/chugins.py

import click
from ..chugins import get_builder, ensure_chugins_built

@click.group()
def chugins():
    """Manage ChucK plugins (chugins)."""
    pass

@chugins.command()
def build():
    """Build chugins from source."""
    builder = get_builder()

    ok, msg = builder.check_requirements()
    if not ok:
        click.echo(f"Error: {msg}")
        return

    click.echo("Building chugins...")
    built = builder.build_all(
        progress_callback=lambda n, i, t: click.echo(f"  [{i}/{t}] {n}")
    )
    click.echo(f"Built {len(built)} chugins to {builder.output_dir}")

@chugins.command()
def list():
    """List available and built chugins."""
    builder = get_builder()
    available = set(builder.list_available())
    built = set(builder.list_built())

    click.echo("Chugins:")
    for name in sorted(available):
        status = "[built]" if name in built else "[not built]"
        click.echo(f"  {name} {status}")

@chugins.command()
def path():
    """Show chugins directory path."""
    click.echo(get_builder().output_dir)
```

#### 4. Integration with Chuck Initialization

```python
# In api.py Chuck.__init__ or when configuring chugin paths

def _configure_chugins(self):
    """Configure chugin paths, building if necessary."""
    from .chugins import get_chugins_dir, ensure_chugins_built

    chugins_dir = get_chugins_dir()

    # Check if we have any chugins
    if not any(chugins_dir.glob("*.chug")):
        # Attempt to build (silent if requirements not met)
        ensure_chugins_built(verbose=False)

    # Set chugin path if directory exists and has chugins
    if chugins_dir.exists() and any(chugins_dir.glob("*.chug")):
        self.raw.set_param_string(
            PARAM_USER_CHUGINS,
            str(chugins_dir)
        )
```

### Advantages

1. **No Gatekeeper issues** - Locally built binaries don't have quarantine flag
2. **Small wheel size** - Source code is much smaller than compiled binaries
3. **Cross-platform** - Same source builds on any platform with CMake
4. **One-time cost** - Build happens once, cached in `~/.numchuck/chugins/`
5. **User control** - Explicit `numchuck chugins build` command available

### Disadvantages

1. **Build requirements** - Users need CMake and C++ compiler
2. **First-use delay** - Initial build takes 1-2 minutes
3. **Potential build failures** - Misconfigured systems may fail to build
4. **Maintenance** - Need to keep chugin sources in sync with upstream

### Requirements for Users

| Platform | Requirements |
|----------|--------------|
| macOS | Xcode Command Line Tools (`xcode-select --install`) |
| Linux | `build-essential` package, CMake |
| Windows | Visual Studio Build Tools or MinGW, CMake |

### Alternative: Hybrid Approach

For users without build tools, provide pre-built chugins as a separate download:

```bash
# Option 1: Build from source (recommended)
numchuck chugins build

# Option 2: Download pre-built (may trigger Gatekeeper on macOS)
numchuck chugins download

# On macOS, if Gatekeeper blocks:
numchuck chugins trust  # Runs xattr -d com.apple.quarantine
```

## Implementation Plan

### Phase 1: Package Structure
- [ ] Create `src/numchuck/chugins/` package
- [ ] Copy chugin sources to `src/numchuck/chugins/sources/`
- [ ] Implement `ChuginBuilder` class
- [ ] Add to `pyproject.toml` package data

### Phase 2: CLI Integration
- [ ] Add `numchuck chugins` CLI group
- [ ] Implement `build`, `list`, `path` commands
- [ ] Add progress reporting

### Phase 3: Auto-Build Integration
- [ ] Hook into Chuck initialization
- [ ] Detect missing chugins and offer to build
- [ ] Update `paths.py` to use built chugins directory

### Phase 4: Testing
- [ ] Test build process on macOS, Linux, Windows
- [ ] Test chugin loading after build
- [ ] Add CI tests for chugin build

### Phase 5: Documentation
- [ ] Update README with chugin build instructions
- [ ] Add troubleshooting guide for build failures
- [ ] Document platform-specific requirements

## Decision

**Status:** Proposal - Not yet implemented

The on-demand compilation approach is recommended as it:
- Avoids macOS Gatekeeper issues entirely
- Keeps the wheel size small
- Provides a good user experience after initial build

Implementation deferred pending prioritization.
