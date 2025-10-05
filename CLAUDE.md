# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

pychuck is a Python wrapper for the ChucK audio programming language. The project uses nanobind to create efficient C++/Python bindings for the ChucK core library. It uses scikit-build-core for building Python packages with CMake.

## Architecture

### Build System
- **Python package build**: scikit-build-core as build backend (defined in pyproject.toml)
- **CMake integration**: CMake 3.15+ handles C++ compilation and nanobind integration
- **Make wrapper**: Convenience Makefile for low-level CMake builds
- **Multi-platform support**: macOS (primary), Windows via CMake generators

### Directory Structure
- `thirdparty/chuck/`: ChucK language implementation (submodule)
  - `core/`: ChucK core library (parser, compiler, VM, audio engine)
  - `host/`: Standalone ChucK host/runtime with RtAudio
- `thirdparty/nanobind/`: Python binding library (submodule)
- `src/`: Python binding implementation
  - `_pychuck.cpp`: C++ extension module (private module with leading underscore)
  - `pychuck/`: Python package directory
    - `__init__.py`: Public Python API that imports from `_pychuck`
- `tests/`: pytest test suite
- `scripts/`: Utility scripts including ChucK source updater

### Key Components
- **ChucK Core Library** (`chuck_lib`): Static library containing the ChucK language implementation, parser (bison/flex-generated), VM, audio processing (ugens), and I/O systems
- **ChucK Standalone** (`chuck`): Executable host that links against chuck_lib and uses RtAudio for cross-platform audio I/O
- **_pychuck Extension** (`_pychuck`): C++ extension module that exposes ChucK API via nanobind (follows Python convention of private extension with leading underscore)
- **pychuck Package**: Public Python package that provides clean API by wrapping `_pychuck`
- **nanobind**: Efficient C++/Python binding library providing ~4x faster compile, ~5x smaller binaries, ~10x lower runtime overhead vs pybind11

## Build and Development Commands

### Python Package Development
```bash
pip install .                    # Install package in current environment
pip install -e .                 # Install in editable/development mode
pip install -v .                 # Verbose build output
```

### Testing
```bash
pytest tests/                    # Run all tests
pytest tests/test_basic.py       # Run specific test file
```

### Low-Level CMake Build (for development)
```bash
make build                       # Build entire project (CMake + compile + install)
```

Platform-specific options (macOS):
- Universal binary: `make build UNIVERSAL=1`
- Xcode generator is default (`GENERATOR=-GXcode`)
- Build config defaults to `Release` (override via `CONFIG` variable)

### Build Process Details
The CMake build (via `make build`):
1. Creates `build/` directory
2. Runs CMake configuration with appropriate generator
3. Builds with specified config (Release/Debug)
4. Installs to `thirdparty/install/`

The Python build (via `pip install`):
1. scikit-build-core invokes CMake
2. CMake builds chuck_lib and _pychuck extension
3. nanobind_add_module creates the `_pychuck` extension with STABLE_ABI for Python 3.12+
4. Extension and pychuck package installed to site-packages

### ChucK Core Build Details
- On macOS: Runs bison/flex to generate parser (chuck.tab.c, chuck.yy.c)
- On Windows: Uses pre-generated parser (chuck_yacc.c)
- Platform-specific audio backends:
  - macOS: CoreAudio, CoreMIDI frameworks
  - Windows: DirectSound (dsound), DirectInput

## Development Notes

### ChucK Source Updates
Use `scripts/update.sh` to pull latest ChucK core from upstream (github.com/ccrma/chuck) while preserving CMake build files.

### Python Extension Development
- C++ extension source: `src/_pychuck.cpp` (currently a hello-world stub with `add()` function)
- Python package API: `src/pychuck/__init__.py` imports and exposes extension functionality
- Use `NB_MODULE(_pychuck, m)` macro to define the C++ extension module
- Extension uses `STABLE_ABI` for Python 3.12+ compatibility (reduces wheel variants needed)
- `NB_STATIC` flag statically links libnanobind into extension
- Follow Python convention: private C++ extension (`_pychuck`) wrapped by public Python package (`pychuck`)

### Platform Definitions
- macOS: `__MACOSX_CORE__`
- Windows: `__PLATFORM_WINDOWS__`, `__PLATFORM_WIN32__`, `__WINDOWS_DS__`
- Debug builds: `__CHUCK_DEBUG__`
