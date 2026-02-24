# Static Chugin Linking - Investigation Notes

## Summary

Static chugin linking was investigated as a way to embed chugins directly into the `_numchuck` extension, eliminating the need for separate `.chug` dynamic library files. **This approach does not work** with the current ChucK architecture.

## What Was Attempted

### Build Configuration

1. Added `CM_STATIC_CHUGINS` CMake option to build chugins as static libraries instead of dynamic `.chug` files
2. Used `-force_load` (macOS) / `--whole-archive` (Linux) to force all symbols from static chugin libraries into the extension
3. Defined `__CK_DLL_STATIC__` preprocessor macro which changes chugin query functions from `ck_query()` to `ck_<Name>_query()` (e.g., `ck_Bitcrusher_query`)

### Registration Attempt

Added code to `_numchuck.cpp` to register static chugins after ChucK initialization:

```cpp
#ifdef CM_STATIC_CHUGINS

extern "C" {
    t_CKBOOL ck_Bitcrusher_query(Chuck_DL_Query*);
    // ... other chugins
}

static void register_static_chugins(ChucK* chuck) {
    Chuck_Compiler* compiler = chuck->compiler();
    compiler->bind(ck_Bitcrusher_query, "Bitcrusher", "global");
    // ... other chugins
}

#endif
```

The `bind()` function was called after `ChucK::init()` completed.

## Why It Doesn't Work

### Symbols Are Linked But Not Registered

1. **Symbols present**: `nm` shows the chugin symbols are in the extension:

   ```text
   0000000000000000 T _ck_Bitcrusher_query
   0000000000000000 T _ck_GVerb_query
   ```

2. **Types undefined**: Despite symbols being present, ChucK reports "undefined type 'Bitcrusher'" when compiling code

3. **No binding messages**: The `compiler->bind()` function should log "on-demand binding compiler module..." but no such messages appear

### Root Cause Analysis

ChucK's chugin system is designed for dynamic loading:

1. **Dynamic chugins**: Discovered at runtime via file system search, loaded with `dlopen()`, query function called to register types

2. **Internal modules**: Built-in modules (math, std, etc.) are registered during `load_internal_modules()` which runs as part of compiler initialization - **before** `ChucK::init()` returns

3. **Static chugins**: The `bind()` API exists but appears to require integration at a different point in ChucK's initialization sequence. Calling `bind()` after `init()` is too late - the type system has already been committed.

### What Would Be Required

To properly support static chugins would require:

1. **ChucK core changes**: Modify `chuck_compile.cpp` to support a static chugin registry that gets processed during `load_internal_modules()` or `load_external_modules()`

2. **Registration before init**: Static chugins need to be registered before the compiler finalizes its type system, not after

3. **Upstream coordination**: This would ideally be an upstream ChucK feature, not a numchuck-specific hack

## Naming Convention Gotchas

During investigation, discovered that some chugins use different names for their query function than their directory name:

| Directory | Query Function |
|-----------|---------------|
| AmbPan | `ck_AmbPan3_query` |
| Bitcrusher | `ck_Bitcrusher_query` |

The name comes from the `CK_DLL_QUERY(name)` macro argument in the chugin source, not the directory name.

## Recommendation

Use dynamic chugins (`.chug` files) which work correctly:

1. Build chugins as dynamic libraries (default behavior)
2. Set `PARAM_IMPORT_PATH_SYSTEM` to include the chugins directory
3. Use `@import "ChuginName";` in ChucK code

## Files Modified (Now Removed)

The following changes were made and subsequently removed:

- `src/CMakeLists.txt`: Static chugin linking logic
- `src/_numchuck.cpp`: Static chugin registration code
- `scripts/cmake/fn_add_chugin.cmake`: `__CK_DLL_STATIC__` define
- `pyproject.toml`: `cmake.args = ["-DCM_STATIC_CHUGINS=ON"]`
