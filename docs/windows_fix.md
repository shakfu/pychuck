# Windows Access Violation Fix

**Status: FIXED via a numchuck local patch to vendored chuck** (`thirdparty/chuck/core/chuck.cpp`).

> IMPORTANT: `thirdparty/chuck` is *vendored*, not a git submodule, and
> `scripts/update.sh` overwrites it wholesale on update -- which silently
> dropped this patch once already and reintroduced the crash. The patch now
> lives in `scripts/patches/0001-windows-shutdown-delay.patch` and is
> re-applied automatically by `apply_chuck_patches` in `update.sh` (which
> hard-fails if it no longer applies). Do not rely on the edit to
> `chuck.cpp` surviving an update on its own.

## Problem Summary

When running tests on Windows, the Python process crashed with an access violation (exit code 3221225477 / 0xC0000005) during ChucK object destruction. The crash occurred when Python's garbage collector destroyed ChucK instances at the end of test functions.

**Symptoms:**

- Tests passed individually but crashed during teardown
- Exit code: 3221225477 (Windows access violation)
- Crash happened in pytest's logging/runner code after test completion
- Affected all Python versions on Windows (3.9-3.13)

## Why Windows Only?

The crash is Windows-specific due to differences in how audio subsystems and threads are managed:

### 1. Audio Thread Cleanup Timing

**macOS (CoreAudio):**

- Audio threads are managed by the system's audio daemon
- Thread termination is handled gracefully by the OS
- Cleanup order is less critical

**Linux (ALSA/PulseAudio):**

- Audio threads are lightweight and terminate quickly
- POSIX thread cleanup is well-defined
- No special timing requirements

**Windows (WASAPI/DirectSound):**

- Audio threads run in a different execution model
- COM initialization/cleanup must happen on the same thread
- Threads may still be accessing memory when destruction begins
- Requires explicit delays to allow threads to terminate

### 2. Thread Handle Management

Windows requires explicit thread handle cleanup with `CloseHandle()`. If threads are still running when memory is freed, they may access deallocated memory, causing access violations.

### 3. VM Object Reference Counting

ChucK uses reference-counted `Chuck_VM_Object` instances. On Windows, concurrent access during destruction can cause race conditions. The `unlock_all()/lock_all()` pattern is needed to safely release objects.

## Root Cause Analysis

Comparing numchuck with [chuck-max](https://github.com/shakfu/chuck-max) (a Max/MSP external that works on Windows), the following differences were identified:

| Aspect | chuck-max | numchuck |
|--------|-----------|----------|
| Explicit VM shutdown | `vm->shutdown()` called before release | Missing |
| Object locking | `unlock_all()/lock_all()` around cleanup | Missing |
| Post-stop delay | 100ms wait after audio stop | Missing |
| Thread handle cleanup | Windows-specific `CloseHandle()` | Missing |
| Destructor control | Custom destructor with full cleanup | Uses ChucK's destructor |

The fundamental issue was that ChucK's `shutdown()` method didn't wait long enough for Windows audio threads to terminate.

## Solution Implemented

We went with **Solution 6: Upstream ChucK Fix** since ChucK is included as a submodule in numchuck.

### Changes Made

1. **`thirdparty/chuck/core/chuck.cpp`** - Added Windows-specific delay in `ChucK::shutdown()`:

```cpp
// In ChucK::shutdown(), after the VM stop wait loop:
#ifdef __PLATFORM_WINDOWS__
    // Windows audio threads (WASAPI/DirectSound) need additional time
    // to fully terminate after VM reports stopped
    ck_usleep( 50000 ); // 50ms delay
#endif
```

2. **`thirdparty/chuck/core/chuck.h`** - Made `shutdown()` public:

```cpp
public:
    // shutdown ChucK instance (can be called explicitly before destruction)
    t_CKBOOL shutdown();
```

3. **`src/_numchuck.cpp`** - Simplified `shutdown()` binding to call `ChucK::shutdown()` directly

### Why This Works

- ChucK's destructor calls `shutdown()` automatically
- The 50ms delay gives WASAPI/DirectSound threads time to fully terminate
- The fix is transparent - no code changes required for users
- Works for both explicit `close()` calls and automatic garbage collection

---

## Alternative Solutions Considered

The following alternatives were evaluated before choosing the upstream fix:

### Solution 1: C++ Wrapper Class (Recommended)

Create a wrapper class that ensures proper cleanup in its destructor:

```cpp
class ChucKWrapper {
private:
    std::unique_ptr<ChucK> m_chuck;
    bool m_shutdown_called;

public:
    ChucKWrapper() : m_chuck(std::make_unique<ChucK>()), m_shutdown_called(false) {}

    ~ChucKWrapper() {
        if (!m_shutdown_called) {
            shutdown();
        }
    }

    void shutdown() {
        if (m_shutdown_called) return;
        m_shutdown_called = true;

        // Clean up instance-specific callbacks
        cleanup_instance_callbacks(m_chuck.get());

        // Clear output callbacks
        m_chuck->setChoutCallback(nullptr);
        m_chuck->setCherrCallback(nullptr);

        // Explicitly shutdown VM
        if (m_chuck->vm()) {
            m_chuck->vm()->shutdown();
#ifdef _WIN32
            ck_usleep(50 * 1000);  // Wait for Windows threads
#endif
        }
    }

    // Accessor for the wrapped ChucK instance
    ChucK* get() { return m_chuck.get(); }
    ChucK* operator->() { return m_chuck.get(); }
};
```

Then bind `ChucKWrapper` instead of `ChucK`:

```cpp
nb::class_<ChucKWrapper>(m, "ChucK")
    .def(nb::init<>())
    .def("init", [](ChucKWrapper& self) { return self->init(); })
    .def("compile_code", [](ChucKWrapper& self, ...) { return self->compileCode(...); })
    // ... forward all methods
    .def("shutdown", &ChucKWrapper::shutdown);
```

**Pros:**

- Cleanup is automatic and guaranteed
- Runs before ChucK's destructor
- Works regardless of how Python destroys the object
- Platform-specific code stays in C++
- No changes required in Python code
- Works for both low-level and high-level API users

**Cons:**

- Requires forwarding all ChucK methods through the wrapper
- Slightly more code in the binding layer
- Need to maintain method forwarding as ChucK API evolves

### Solution 2: Custom Release Hook via Type Slots

Use nanobind's type slot mechanism to add a custom release hook:

```cpp
// Custom release function
void chuck_release(PyObject* obj) {
    ChucK* chuck = nb::cast<ChucK*>(nb::handle(obj));
    cleanup_instance_callbacks(chuck);
    if (chuck->vm()) {
        chuck->vm()->shutdown();
#ifdef _WIN32
        ck_usleep(50 * 1000);
#endif
    }
    // Let normal destruction proceed
}

// In module definition
nb::class_<ChucK>(m, "ChucK", nb::type_slots({
    {Py_tp_finalize, (void*)chuck_release}
}))
```

**Pros:**

- No wrapper class needed
- Less code changes
- Direct binding to ChucK class preserved

**Cons:**

- `tp_finalize` is called during garbage collection, which has restrictions
- Cannot reliably call Python code from finalizer
- Order of finalization not guaranteed
- May not work correctly during interpreter shutdown
- More complex to debug

### Solution 3: Python `__del__` with prevent-double-free

Add a destructor at the Python level in `api.py`:

```python
class Chuck:
    def __init__(self, ...):
        self._chuck = _numchuck.ChucK()
        self._closed = False
        # Register weak reference callback
        weakref.ref(self, self._weak_callback)

    def __del__(self):
        self.close()

    def close(self):
        if not self._closed:
            self._closed = True
            self._chuck.shutdown()
```

**Pros:**

- No C++ changes required
- Easy to understand and maintain
- Pythonic approach

**Cons:**

- `__del__` is not guaranteed to be called (especially during interpreter shutdown)
- Only works for high-level API; low-level `_numchuck.ChucK` users still affected
- GIL must be held, potential for deadlocks
- Weak reference callbacks have similar reliability issues
- Can't control order relative to C++ destructor

### Solution 4: Context Manager Pattern

Force users to use context managers:

```python
class Chuck:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

# Usage:
with Chuck() as chuck:
    chuck.compile("SinOsc s => dac;")
    chuck.run(44100)
# Automatic cleanup here
```

**Pros:**

- Explicit resource management
- Pythonic pattern
- Guaranteed cleanup within the `with` block

**Cons:**

- Doesn't fix automatic cleanup on destruction
- Breaking API change
- Inconvenient for interactive/REPL usage
- Users must remember to use `with` statement

### Solution 5: Instance Registry with atexit

Track all instances and clean them up at interpreter exit:

```cpp
static std::vector<ChucK*> g_all_instances;
static std::mutex g_instances_mutex;

// In ChucK binding constructor
.def(nb::init([&]() {
    auto* chuck = new ChucK();
    std::lock_guard<std::mutex> lock(g_instances_mutex);
    g_all_instances.push_back(chuck);
    return chuck;
}))

// Register atexit handler
void cleanup_all_instances() {
    std::lock_guard<std::mutex> lock(g_instances_mutex);
    for (auto* chuck : g_all_instances) {
        if (chuck->vm()) {
            chuck->vm()->shutdown();
#ifdef _WIN32
            ck_usleep(50 * 1000);
#endif
        }
    }
    g_all_instances.clear();
}
```

**Pros:**

- Ensures cleanup happens before interpreter shutdown
- Doesn't require wrapper class

**Cons:**

- Cleanup only happens at exit, not when objects are destroyed
- Memory leaks for long-running applications
- Doesn't help with mid-session cleanup
- Complex lifecycle management
- Thread safety concerns with the registry

### Solution 6: Upstream ChucK Fix

Modify ChucK's shutdown() method in the core library to include proper Windows cleanup:

```cpp
//-----------------------------------------------------------------------------
// name: shutdown()
// desc: shutdown ChucK instance
//-----------------------------------------------------------------------------
t_CKBOOL ChucK::shutdown()
{
// ...

    // stop VM
    if( m_carrier != NULL && m_carrier->vm != NULL  )
    {
        m_carrier->vm->stop();

        // wait for it to stop...
        while( m_carrier->vm->running() )
        {
            ck_usleep(1000);
        }

// ======================================================================
#ifdef __PLATFORM_WINDOWS__
        // Windows audio threads (WASAPI/DirectSound) need additional time
        // to fully terminate after VM reports stopped
        ck_usleep( 50000 ); // 50ms delay
#endif
// ======================================================================
    }

    // free vm, compiler, friends
    // first, otf
    // REFACTOR-2017 TODO: le_cb?

    // STK-specific
    stk_detach( m_carrier );

// ...
}
```

Also made `shutdown()` public in chuck.h

```cpp
public:
    // shutdown ChucK instance (can be called explicitly before destruction)
    t_CKBOOL shutdown();
```

**Pros:**

- Fixes the problem at the source
- Benefits all ChucK embeddings, not just numchuck
- No workarounds needed in binding layer

**Cons:**

- Requires upstream changes to ChucK repository
- Longer timeline to get merged and released
- May have unintended effects on other ChucK embeddings
- Not within numchuck's direct control

---

## Why We Chose the Upstream Fix

**Solution 6 (Upstream ChucK Fix)** was chosen for the following reasons:

1. **Simplicity**: Minimal code changes (just a delay and making `shutdown()` public)
2. **Transparency**: Users don't need to change their code
3. **Root cause**: Fixes the problem at its source
4. **Maintainability**: No wrapper class or complex binding changes needed
5. **Automatic**: Works for both explicit cleanup and garbage collection

Since ChucK is vendored in numchuck, we can patch the upstream code -- but the patch must be tracked in `scripts/patches/` and re-applied by `update.sh`, because a wholesale update overwrites the vendored tree (this is how the fix regressed once; see the note at the top of this document).

## Testing

The fix was verified by:

1. Running full test suite locally (216 tests pass)
2. Re-enabling Windows tests in `wheels.yml`
3. CI will verify on actual Windows runners

## References

- [chuck-max source code](https://github.com/shakfu/chuck-max) - Windows-compatible ChucK embedding
- [ChucK VM lifecycle](https://chuck.stanford.edu/doc/program/vm.html) - Official documentation
- [nanobind documentation](https://nanobind.readthedocs.io/) - Python binding library
- [Windows thread cleanup](https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-closehandle) - MSDN documentation
