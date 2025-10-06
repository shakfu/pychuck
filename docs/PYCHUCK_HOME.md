# pychuck Home Directory

pychuck uses `~/.pychuck/` as its home directory for storing user data, configuration, and resources.

## Directory Structure

```
~/.pychuck/
├── history           # REPL command history
├── snippets/         # Reusable ChucK code snippets
├── sessions/         # Saved REPL sessions (future)
├── logs/             # ChucK VM and audio logs (future)
├── projects/         # Multi-file ChucK projects (future)
└── config.toml       # User configuration (future)
```

## Current Features

### REPL History (`~/.pychuck/history`)

Stores command history from the pychuck REPL:
- Persists across sessions
- Supports Ctrl+R reverse search
- Supports Ctrl+S forward search (prompt_toolkit only)
- Maximum 1000 entries (configurable via readline)

**Managed by:** `src/pychuck/cli/repl.py`

### Code Snippets (`~/.pychuck/snippets/`)

Directory for storing reusable ChucK code snippets that can be loaded instantly in the REPL.

**Usage:**
```bash
# Create a snippet
echo 'SinOsc s => dac; 440 => s.freq; while(true) { 1::samp => now; }' > ~/.pychuck/snippets/sine.ck

# Load it in the REPL
chuck> @sine
✓ sporked snippet @sine -> shred 1
```

**Features:**
- Auto-discovery: Any `.ck` file in this directory is available as `@<filename>`
- Tab completion: Type `@` and press Tab to see available snippets
- Auto-creation: Directory is created automatically on first REPL launch

**Common snippet examples:**
- `@sine` - Simple sine wave generator
- `@noise` - White noise generator
- `@kick` - Kick drum sound
- `@bass` - Bass line pattern
- `@reverb` - Reverb effect chain

**Managed by:** `src/pychuck/cli/commands.py`, `src/pychuck/cli/paths.py`

## Future Features

### Sessions (`~/.pychuck/sessions/`)

**Planned feature:** Save and restore REPL sessions

```bash
# Save current session
chuck> :save my_performance

# Restore session
chuck> :load my_performance
```

Each session would store:
- Active shreds and their code
- Global variable values
- Audio configuration
- Loaded files

### Logs (`~/.pychuck/logs/`)

**Planned feature:** Store ChucK VM logs and debugging output

Potential logs:
- `chuck_vm.log` - VM state changes, shred lifecycle
- `audio.log` - Audio engine events, device info
- `errors.log` - Compilation and runtime errors
- `repl.log` - REPL command history with timestamps

### Projects (`~/.pychuck/projects/`)

**Planned feature:** Store multi-file ChucK projects

```
~/.pychuck/projects/my_synth/
├── main.ck           # Entry point
├── oscillators.ck    # Oscillator library
├── effects.ck        # Effect processors
├── samples/          # Audio samples
│   ├── kick.wav
│   └── snare.wav
└── project.toml      # Project configuration
```

### Configuration (`~/.pychuck/config.toml`)

**Planned feature:** User preferences and defaults

Example configuration:
```toml
[audio]
sample_rate = 48000
output_channels = 2
buffer_size = 512
default_device = "Built-in Output"

[repl]
prompt = "chuck> "
show_toolbar = true
auto_init = true
theme = "monokai"

[paths]
chugins = [
    "~/chuck/chugins",
    "/usr/local/lib/chuck"
]
samples = "~/chuck/samples"

[snippets]
auto_reload = true
favorite = ["sine", "reverb", "kick"]
```

## API Reference

The `src/pychuck/cli/paths.py` module provides utilities for managing the pychuck home directory:

### Functions

- **`get_pychuck_home() -> Path`**
  Returns `~/.pychuck`

- **`get_snippets_dir() -> Path`**
  Returns `~/.pychuck/snippets`

- **`get_history_file() -> Path`**
  Returns `~/.pychuck/history`

- **`get_sessions_dir() -> Path`**
  Returns `~/.pychuck/sessions` (future)

- **`get_logs_dir() -> Path`**
  Returns `~/.pychuck/logs` (future)

- **`get_config_file() -> Path`**
  Returns `~/.pychuck/config.toml` (future)

- **`get_projects_dir() -> Path`**
  Returns `~/.pychuck/projects` (future)

- **`ensure_pychuck_directories()`**
  Creates all standard directories if they don't exist

- **`list_snippets() -> list[str]`**
  Lists all available snippet names (without `.ck` extension)

- **`get_snippet_path(name: str) -> Path`**
  Returns path to a specific snippet file

### Usage Example

```python
from pychuck.cli.paths import get_snippets_dir, list_snippets

# Get snippets directory
snippets = get_snippets_dir()
print(f"Snippets stored in: {snippets}")

# List available snippets
for name in list_snippets():
    print(f"  @{name}")
```

## Migration from Old Paths

If you have existing pychuck data:

**Old locations:**
- `~/.chuck_repl_history` → `~/.pychuck/history`
- `~/.chuck_snippets/` → `~/.pychuck/snippets/`

**Migration:**
```bash
# Create new directory structure
mkdir -p ~/.pychuck/snippets

# Migrate history (if exists)
if [ -f ~/.chuck_repl_history ]; then
    mv ~/.chuck_repl_history ~/.pychuck/history
fi

# Migrate snippets (if exists)
if [ -d ~/.chuck_snippets ]; then
    mv ~/.chuck_snippets/* ~/.pychuck/snippets/
    rmdir ~/.chuck_snippets
fi
```

## Best Practices

### Snippets

1. **Use descriptive names**: `@reverb_large` vs `@rev1`
2. **Include comments**: Explain parameters and usage
3. **Keep them focused**: One snippet, one purpose
4. **Version complex snippets**: `@synth_v1`, `@synth_v2`

Example snippet with documentation:
```chuck
// ~/.pychuck/snippets/reverb_large.ck
// Large hall reverb with configurable mix

SinOsc s => JCRev r => dac;
0.15 => r.mix;  // 15% wet, 85% dry
440 => s.freq;

while(true) { 1::samp => now; }
```

### Organization

Consider subdirectories for complex setups (requires code changes):
```
~/.pychuck/snippets/
├── synthesis/
│   ├── fm.ck
│   ├── additive.ck
│   └── subtractive.ck
├── effects/
│   ├── reverb.ck
│   ├── delay.ck
│   └── distortion.ck
└── drums/
    ├── kick.ck
    ├── snare.ck
    └── hihat.ck
```

## Troubleshooting

### Directory not created automatically

```bash
# Manually create directories
python3 -c "from pychuck.cli.paths import ensure_pychuck_directories; ensure_pychuck_directories()"
```

### Snippet not found

```bash
# Check snippet exists
ls -la ~/.pychuck/snippets/

# Verify filename (must end in .ck)
chuck> @mysound
✗ snippet 'mysound' not found
# Should be: ~/.pychuck/snippets/mysound.ck
```

### History not saving

```bash
# Check permissions
ls -la ~/.pychuck/history

# Check if directory is writable
touch ~/.pychuck/test && rm ~/.pychuck/test
```

## Security Considerations

The `~/.pychuck/` directory may contain:
- Command history (could include sensitive file paths)
- Custom ChucK code (intellectual property)
- Future: audio samples and recordings

**Recommendations:**
- Add `~/.pychuck/` to your backup routine
- Don't share snippets containing hardcoded credentials or paths
- Consider encrypting `~/.pychuck/` if working with sensitive audio/code

## See Also

- [REPL Documentation](dev/REPL_IMPROVEMENTS.md)
- [ChucK Language Specification](https://chuck.stanford.edu/doc/language/)
- [Path Management API](../src/pychuck/cli/paths.py)
