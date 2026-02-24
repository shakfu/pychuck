# Error Handling in numchuck

## Overview

numchuck uses **exception-based error handling** consistently across all APIs. This document describes the error handling strategy and best practices.

## Error Handling Strategy

### Principle: Exceptions for All Errors

All numchuck operations that can fail will raise Python exceptions. **Never rely on return values alone to detect errors** - check for exceptions.

### Exception Types

| Exception Type | When Raised | Example |
|----------------|-------------|---------|
| `ValueError` | Invalid input parameters | Empty strings, zero/negative counts |
| `RuntimeError` | Operation failed or ChucK not initialized | Compilation errors, VM not ready |
| `TypeError` | Incorrect type passed | Passing int where string expected |

## Common Patterns

### 1. Initialization

```python
import numchuck

# Always check initialization
chuck = numchuck.ChucK()
try:
    chuck.init(44100, 2)
except RuntimeError as e:
    print(f"Failed to initialize ChucK: {e}")
    exit(1)

# Or use the convenience method (raises on failure)
try:
    chuck = numchuck.ChucK.create(44100, 2)
except RuntimeError as e:
    print(f"Failed to create ChucK: {e}")
    exit(1)
```

### 2. Compilation

```python
# compile_code returns (success, shred_ids) tuple
# Raises exceptions for invalid inputs
try:
    success, shred_ids = chuck.compile_code(code)
    if success:
        print(f"Compiled: shred IDs {shred_ids}")
    else:
        print("Compilation failed (syntax error)")
except ValueError as e:
    print(f"Invalid input: {e}")  # e.g., empty code
except RuntimeError as e:
    print(f"Runtime error: {e}")  # e.g., not initialized
```

### 3. Global Variables

```python
# Setting global variables (raises on failure)
try:
    chuck.set_global_int("freq", 440)
except RuntimeError as e:
    print(f"Failed to set variable: {e}")  # Variable doesn't exist

# Getting global variables (async via callback)
def on_value(value):
    print(f"Got value: {value}")

try:
    chuck.get_global_int("freq", on_value)
except RuntimeError as e:
    print(f"Failed to get variable: {e}")  # Variable doesn't exist
```

### 4. Event Listeners

```python
# Listen for events (returns listener ID for cleanup)
try:
    listener_id = chuck.listen_for_global_event("myevent", on_event)
    print(f"Listening with ID {listener_id}")
except RuntimeError as e:
    print(f"Failed to listen: {e}")  # Event doesn't exist

# IMPORTANT: Clean up listeners when done to prevent memory leaks
try:
    chuck.stop_listening_for_global_event("myevent", listener_id)
except RuntimeError as e:
    print(f"Failed to stop listening: {e}")
```

### 5. Shred Management

```python
# Remove shred (raises if VM not initialized)
try:
    chuck.remove_shred(shred_id)
except RuntimeError as e:
    print(f"Failed to remove shred: {e}")

# Get shred info (raises if VM not initialized)
try:
    info = chuck.get_shred_info(shred_id)
    print(f"Shred state: {info['state']}")
except RuntimeError as e:
    print(f"Failed to get shred info: {e}")
```

## Input Validation

numchuck validates all inputs before calling ChucK APIs:

### Strings

- **Empty strings not allowed** for code, file paths, variable names
- Raises `ValueError`

```python
# [X] Will raise ValueError
chuck.compile_code("")  # ValueError: Code cannot be empty

# [x] Correct
chuck.compile_code("SinOsc s => dac;")
```

### Numeric Values

- **Counts must be >= 1**
- **Frames must be > 0**
- **Sample rates, channels must be > 0**
- Raises `ValueError`

```python
# [X] Will raise ValueError
chuck.compile_code("...", count=0)  # ValueError: Count must be at least 1
chuck.run(input, output, 0)         # ValueError: num_frames must be positive

# [x] Correct
chuck.compile_code("...", count=1)
chuck.run(input, output, 512)
```

### Initialization State

- **Most operations require ChucK to be initialized**
- Raises `RuntimeError` if not initialized

```python
chuck = numchuck.ChucK()
# [X] Will raise RuntimeError
chuck.compile_code("...")  # RuntimeError: ChucK not initialized. Call init() first.

# [x] Correct
chuck.init(44100, 2)
chuck.compile_code("...")
```

## Error Messages

Error messages follow a consistent format:

```text
ValueError: <parameter> cannot be <invalid_value>
RuntimeError: ChucK instance not initialized. Call init() first.
RuntimeError: Failed to <operation> '<name>'
RuntimeError: VM not initialized
```

## Memory Management & Cleanup

### Event Listener Cleanup

**CRITICAL:** Event listeners created with `listen_for_global_event` persist in memory until explicitly removed.

```python
# Store listener IDs
listener_ids = []

# Add listener
listener_id = chuck.listen_for_global_event("myevent", callback)
listener_ids.append(listener_id)

# Clean up when done
for lid in listener_ids:
    chuck.stop_listening_for_global_event("myevent", lid)
listener_ids.clear()
```

### Context Manager Pattern (Recommended for Future)

```python
# Not yet implemented, but recommended pattern:
with numchuck.ChucK.create(44100, 2) as chuck:
    chuck.compile_code("...")
    # Automatic cleanup on exit
```

## Best Practices

### 1. Always Handle Exceptions

```python
# [X] Bad - ignores potential errors
success, shreds = chuck.compile_code(code)

# [x] Good - handles all error cases
try:
    success, shreds = chuck.compile_code(code)
    if not success:
        handle_compilation_failure()
except ValueError as e:
    handle_invalid_input(e)
except RuntimeError as e:
    handle_runtime_error(e)
```

### 2. Check Initialization State

```python
# [X] Bad - assumes initialized
chuck = numchuck.ChucK()
chuck.compile_code(code)

# [x] Good - ensures initialization
chuck = numchuck.ChucK()
if not chuck.is_init():
    chuck.init(44100, 2)
```

### 3. Clean Up Resources

```python
# [X] Bad - leaks event listeners
for i in range(1000):
    chuck.listen_for_global_event("event", lambda: print(i))
# All 1000 callbacks remain in memory!

# [x] Good - tracks and cleans up
listeners = []
for i in range(10):
    lid = chuck.listen_for_global_event("event", lambda: print(i))
    listeners.append(lid)

# Later:
for lid in listeners:
    chuck.stop_listening_for_global_event("event", lid)
```

### 4. Validate Before Passing to ChucK

```python
# [X] Bad - no validation
code = user_input
chuck.compile_code(code)

# [x] Good - validate first
code = user_input.strip()
if not code:
    print("Error: Code cannot be empty")
    return

try:
    chuck.compile_code(code)
except Exception as e:
    print(f"Compilation failed: {e}")
```

## Compilation Errors

Compilation errors return `(False, [])` rather than raising exceptions. This allows you to handle syntax errors gracefully:

```python
success, shred_ids = chuck.compile_code(code)
if not success:
    # Syntax error in code - check ChucK error output
    # Use chuck.set_cherr_callback() to capture error messages
    print("Compilation failed - check ChucK errors")
else:
    print(f"Success: {shred_ids}")
```

## Debugging Tips

### 1. Enable ChucK Error Output

```python
def on_error(msg):
    print(f"ChucK Error: {msg}", file=sys.stderr)

chuck.set_cherr_callback(on_error)
```

### 2. Check Initialization State

```python
if not chuck.is_init():
    print("ChucK not initialized!")
```

### 3. Use Verbose Logging

```python
import numchuck
numchuck.ChucK.set_log_level(numchuck.LOG_ALL)
```

## Summary

- **All errors raise exceptions** - never ignore return values
- **Check initialization** before operations
- **Clean up event listeners** to prevent memory leaks
- **Validate inputs** before passing to ChucK
- **Handle compilation failures** by checking return tuple
- **Use try/except** around all ChucK operations

Following these patterns ensures robust, leak-free numchuck applications.
