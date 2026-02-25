# numchuck REPL Command Reference

Every symbol command has a readable word alias. Use whichever form you prefer.

## Shred Management

| Symbol | Word | Description |
|--------|------|-------------|
| `+ <file.ck>` | `add <file.ck>` | Spork a file |
| `+ "<code>"` | -- | Spork inline code |
| `- <id>` | `remove <id>` | Remove shred by ID |
| `- all` | `remove all` | Remove all shreds |
| `= <id> <file.ck>` | `replace <id> <file.ck>` | Replace shred with file |
| `= <id> "<code>"` | `replace <id> "<code>"` | Replace shred with code |
| `abort <id>` | `abort.shred <id>` | Abort shred |

## Status and Info

| Symbol | Word | Description |
|--------|------|-------------|
| `?` | `shreds` | List active shreds |
| `? <id>` | `shred <id>` | Show shred info |
| `?g` | `globals` | List global variables |
| `?a` | `audio` | Show audio info |
| `.` | `time` | Show current time |
| `^` | `status` | Show VM status |

## Global Variables

| Symbol | Word | Description |
|--------|------|-------------|
| `<name>?` | `get <name>` | Get global variable value |
| `<name>::<val>` | `set <name> <val>` | Set global variable |

## Events

| Symbol | Word | Description |
|--------|------|-------------|
| `<ev>!` | `signal <ev>` | Signal an event |
| `<ev>!!` | `broadcast <ev>` | Broadcast an event |

## Audio Control

| Symbol | Word | Description |
|--------|------|-------------|
| `>` | `start` | Start audio |
| `\|\|` | `stop` | Stop audio |
| `X` | `shutdown` | Shutdown audio engine |

## VM Control

| Command | Description |
|---------|-------------|
| `clear` | Clear the VM |
| `reset` | Reset shred ID counter |
| `cls` | Clear screen |

## File and Code Operations

| Symbol | Word | Description |
|--------|------|-------------|
| `: <file.ck>` | `compile <file.ck>` | Compile file (no spork) |
| `! "<code>"` | `exec "<code>"` | Execute code string |
| `$ <cmd>` | `shell <cmd>` | Run shell command |
| `@<name>` | `snippet <name>` | Load a snippet |

## Editor and File Watching

| Command | Description |
|---------|-------------|
| `edit` | Open editor |
| `edit <id>` | Edit shred source |
| `watch <file.ck>` | Auto-reload file on change |
| `unwatch <file.ck>` | Stop watching file |
| `unwatch all` | Stop all watches |
| `watching` | List watched files |

## Recording

| Command | Description |
|---------|-------------|
| `record start [name]` | Start recording |
| `record stop` | Stop and save |
| `record save <name>` | Save recording as name |
| `record discard` | Discard current recording |
| `record status` | Show recording status |

## Playback

| Command | Description |
|---------|-------------|
| `play <name> [speed]` | Play a recording |
| `play pause` | Pause playback |
| `play resume` | Resume playback |
| `play stop` | Stop playback |
| `recordings` | List all recordings |

## MIDI

| Command | Description |
|---------|-------------|
| `midi learn <var> <cc> [ch] [min max]` | Map CC to global |
| `midi list` | List mappings |
| `midi start` / `midi stop` | Start/stop listener |
| `midi status` | Show MIDI status |
| `midi monitor` | Monitor CC input |
| `midi remove <var>` | Remove mapping |

## OSC

| Command | Description |
|---------|-------------|
| `osc start [port]` | Start OSC server (default 9000) |
| `osc stop` | Stop OSC server |
| `osc status` | Show OSC status |

## Waveform Display

| Command | Description |
|---------|-------------|
| `wave` | Toggle waveform display |
| `wave on` / `wave off` | Enable/disable display |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `F1` | Toggle help panel |
| `F2` | Toggle shreds table |
| `Ctrl+Q` | Exit REPL |
| `Ctrl+R` | History search |
| `Esc+Enter` | Force-submit (bypass multiline) |
| `Tab` | Auto-complete |
| `exit` / `quit` | Exit REPL |
