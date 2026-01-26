# numchuck User Directory Template

This directory serves as a template for the `.numchuck` user directory.

## Directory Structure

```
.numchuck/
  snippets/         # ChucK code snippets (use @name in REPL)
  examples/         # Example ChucK files
  themes/           # Custom color themes
  keybindings/      # Custom key bindings
  chugins/          # User chugins (ChucK plugins)
  projects/         # Project directories with versioning
  sessions/         # Saved REPL sessions
  recordings/       # Recorded REPL sessions for playback
  logs/             # Log files
  config.toml       # Configuration file
  numchuck_history  # REPL command history
```

## Search Order

numchuck searches for `.numchuck` in this order:
1. Current working directory (`./.numchuck`)
2. Home directory (`~/.numchuck`)

This allows project-specific configuration to override global settings.

## Using Snippets

Place `.ck` files in the `snippets/` directory and load them in the REPL:

```
[=>] @sine        # Loads snippets/sine.ck
[=>] @drum        # Loads snippets/drum.ck
```

Tab completion is available for snippet names.

## Installation

Copy this directory to your home directory:

```bash
cp -r _numchuck ~/.numchuck
```

Or create a project-specific configuration:

```bash
cp -r _numchuck .numchuck
```
