"""
Configuration file support for numchuck.

Provides loading and management of user preferences from ~/.numchuck/config.toml.

Example config.toml:
    [audio]
    sample_rate = 48000
    output_channels = 2
    input_channels = 0
    buffer_size = 512

    [repl]
    smart_enter = true
    show_sidebar = true
    start_audio = false

    [editor]
    start_audio = false

    [paths]
    working_directory = "~/chuck"
    chugin_paths = ["~/.chuck/chugins"]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_NUM_BUFFERS,
    DEFAULT_OSC_PORT,
    DEFAULT_OUTPUT_CHANNELS,
    DEFAULT_SAMPLE_RATE,
    MAX_CONSOLE_LINES,
)
from .paths import get_config_file

if sys.version_info >= (3, 11):
    import tomllib
else:
    # For Python 3.9-3.10, try tomli as fallback
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class AudioConfig:
    """Audio configuration settings."""

    sample_rate: int = DEFAULT_SAMPLE_RATE
    output_channels: int = DEFAULT_OUTPUT_CHANNELS
    input_channels: int = 0
    buffer_size: int = DEFAULT_BUFFER_SIZE
    num_buffers: int = DEFAULT_NUM_BUFFERS
    dac_device: int = 0
    adc_device: int = 0


@dataclass
class REPLConfig:
    """REPL configuration settings."""

    smart_enter: bool = True
    show_sidebar: bool = True
    start_audio: bool = False
    max_log_lines: int = MAX_CONSOLE_LINES


@dataclass
class EditorConfig:
    """Editor configuration settings."""

    start_audio: bool = False
    tab_size: int = 4
    wrap_lines: bool = False


@dataclass
class PathsConfig:
    """Path configuration settings."""

    working_directory: str = ""
    chugin_paths: list[str] = field(default_factory=list)


@dataclass
class ChuckConfig:
    """ChucK VM configuration settings."""

    chugin_enable: bool = True
    vm_adaptive: bool = False
    vm_halt: bool = False
    auto_depend: bool = False
    deprecate_level: int = 1
    tty_color: bool = False


@dataclass
class ThemeColors:
    """Color settings for TUI theming.

    All colors should be valid hex colors (e.g., '#ffffff') or named colors.
    """

    # Bottom toolbar
    bottom_toolbar_fg: str = "#aaaaaa"
    bottom_toolbar_bg: str = "#333333"

    # Status bar
    status_bar_fg: str = "#ffffff"
    status_bar_bg: str = "#444444"

    # Error bar
    error_bar_fg: str = "#ffffff"
    error_bar_bg: str = "#cc0000"

    # Help window
    help_fg: str = "#ffffff"
    help_bg: str = "#222244"

    # Shreds table
    shreds_table_fg: str = "#ffffff"
    shreds_table_bg: str = "#224422"

    # Log window
    log_fg: str = "#cccccc"
    log_bg: str = "#1a1a1a"

    # Audio status indicators
    audio_on_fg: str = "#00ff00"
    audio_off_fg: str = "#ff6600"

    # Input prompt
    prompt_fg: str = "#00aaff"

    # Code highlighting (used by Pygments lexer)
    keyword_fg: str = "#ff7700"
    type_fg: str = "#00aa00"
    operator_fg: str = "#ffffff"
    string_fg: str = "#ffff00"
    comment_fg: str = "#666666"
    number_fg: str = "#00ffff"


@dataclass
class ThemeConfig:
    """Theme configuration.

    Attributes:
        name: Theme name - 'dark', 'light', 'solarized', or 'custom'
        colors: Custom color settings (used when name is 'custom')
    """

    name: str = "dark"
    colors: ThemeColors = field(default_factory=ThemeColors)


@dataclass
class KeybindingsConfig:
    """Keybinding configuration.

    All keybindings use prompt_toolkit key notation:
    - 'c-q' for Ctrl+Q
    - 'f1' for F1
    - 'escape' for Escape
    - 'c-s-f' for Ctrl+Shift+F
    """

    # General
    exit: str = "c-q"
    toggle_help: str = "f1"
    toggle_shreds: str = "f2"
    toggle_log: str = "f3"
    toggle_waveform: str = "f4"

    # Audio controls
    start_audio: str = "f5"
    stop_audio: str = "f6"

    # Editor specific
    spork: str = "f5"
    replace_shred: str = "f6"
    new_tab: str = "c-n"
    close_tab: str = "c-w"
    next_tab: str = "c-pagedown"
    prev_tab: str = "c-pageup"

    # Navigation
    focus_input: str = "escape"


@dataclass
class OSCConfig:
    """OSC (Open Sound Control) configuration."""

    port: int = DEFAULT_OSC_PORT
    enabled: bool = False


@dataclass
class MIDIConfig:
    """MIDI configuration."""

    enabled: bool = False
    device: str = ""  # Empty string means auto-detect


@dataclass
class Config:
    """Complete numchuck configuration.

    Attributes:
        audio: Audio settings (sample rate, channels, etc.)
        repl: REPL interface settings
        editor: Editor interface settings
        paths: File path settings
        chuck: ChucK VM settings
        theme: Theme and color settings
        keybindings: Keyboard shortcut settings
        osc: OSC server settings
        midi: MIDI settings
    """

    audio: AudioConfig = field(default_factory=AudioConfig)
    repl: REPLConfig = field(default_factory=REPLConfig)
    editor: EditorConfig = field(default_factory=EditorConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    chuck: ChuckConfig = field(default_factory=ChuckConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    keybindings: KeybindingsConfig = field(default_factory=KeybindingsConfig)
    osc: OSCConfig = field(default_factory=OSCConfig)
    midi: MIDIConfig = field(default_factory=MIDIConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create Config from a dictionary (parsed TOML)."""
        config = cls()

        if "audio" in data:
            for key, value in data["audio"].items():
                if hasattr(config.audio, key):
                    setattr(config.audio, key, value)

        if "repl" in data:
            for key, value in data["repl"].items():
                if hasattr(config.repl, key):
                    setattr(config.repl, key, value)

        if "editor" in data:
            for key, value in data["editor"].items():
                if hasattr(config.editor, key):
                    setattr(config.editor, key, value)

        if "paths" in data:
            for key, value in data["paths"].items():
                if hasattr(config.paths, key):
                    setattr(config.paths, key, value)

        if "chuck" in data:
            for key, value in data["chuck"].items():
                if hasattr(config.chuck, key):
                    setattr(config.chuck, key, value)

        if "theme" in data:
            theme_data = data["theme"]
            if "name" in theme_data:
                config.theme.name = theme_data["name"]
            if "colors" in theme_data:
                for key, value in theme_data["colors"].items():
                    if hasattr(config.theme.colors, key):
                        setattr(config.theme.colors, key, value)

        if "keybindings" in data:
            for key, value in data["keybindings"].items():
                if hasattr(config.keybindings, key):
                    setattr(config.keybindings, key, value)

        if "osc" in data:
            for key, value in data["osc"].items():
                if hasattr(config.osc, key):
                    setattr(config.osc, key, value)

        if "midi" in data:
            for key, value in data["midi"].items():
                if hasattr(config.midi, key):
                    setattr(config.midi, key, value)

        return config

    def to_dict(self) -> dict[str, Any]:
        """Convert Config to a dictionary."""
        return {
            "audio": {
                "sample_rate": self.audio.sample_rate,
                "output_channels": self.audio.output_channels,
                "input_channels": self.audio.input_channels,
                "buffer_size": self.audio.buffer_size,
                "num_buffers": self.audio.num_buffers,
                "dac_device": self.audio.dac_device,
                "adc_device": self.audio.adc_device,
            },
            "repl": {
                "smart_enter": self.repl.smart_enter,
                "show_sidebar": self.repl.show_sidebar,
                "start_audio": self.repl.start_audio,
                "max_log_lines": self.repl.max_log_lines,
            },
            "editor": {
                "start_audio": self.editor.start_audio,
                "tab_size": self.editor.tab_size,
                "wrap_lines": self.editor.wrap_lines,
            },
            "paths": {
                "working_directory": self.paths.working_directory,
                "chugin_paths": self.paths.chugin_paths,
            },
            "chuck": {
                "chugin_enable": self.chuck.chugin_enable,
                "vm_adaptive": self.chuck.vm_adaptive,
                "vm_halt": self.chuck.vm_halt,
                "auto_depend": self.chuck.auto_depend,
                "deprecate_level": self.chuck.deprecate_level,
                "tty_color": self.chuck.tty_color,
            },
            "theme": {
                "name": self.theme.name,
                "colors": {
                    "bottom_toolbar_fg": self.theme.colors.bottom_toolbar_fg,
                    "bottom_toolbar_bg": self.theme.colors.bottom_toolbar_bg,
                    "status_bar_fg": self.theme.colors.status_bar_fg,
                    "status_bar_bg": self.theme.colors.status_bar_bg,
                    "error_bar_fg": self.theme.colors.error_bar_fg,
                    "error_bar_bg": self.theme.colors.error_bar_bg,
                    "help_fg": self.theme.colors.help_fg,
                    "help_bg": self.theme.colors.help_bg,
                    "shreds_table_fg": self.theme.colors.shreds_table_fg,
                    "shreds_table_bg": self.theme.colors.shreds_table_bg,
                    "log_fg": self.theme.colors.log_fg,
                    "log_bg": self.theme.colors.log_bg,
                    "audio_on_fg": self.theme.colors.audio_on_fg,
                    "audio_off_fg": self.theme.colors.audio_off_fg,
                    "prompt_fg": self.theme.colors.prompt_fg,
                    "keyword_fg": self.theme.colors.keyword_fg,
                    "type_fg": self.theme.colors.type_fg,
                    "operator_fg": self.theme.colors.operator_fg,
                    "string_fg": self.theme.colors.string_fg,
                    "comment_fg": self.theme.colors.comment_fg,
                    "number_fg": self.theme.colors.number_fg,
                },
            },
            "keybindings": {
                "exit": self.keybindings.exit,
                "toggle_help": self.keybindings.toggle_help,
                "toggle_shreds": self.keybindings.toggle_shreds,
                "toggle_log": self.keybindings.toggle_log,
                "toggle_waveform": self.keybindings.toggle_waveform,
                "start_audio": self.keybindings.start_audio,
                "stop_audio": self.keybindings.stop_audio,
                "spork": self.keybindings.spork,
                "replace_shred": self.keybindings.replace_shred,
                "new_tab": self.keybindings.new_tab,
                "close_tab": self.keybindings.close_tab,
                "next_tab": self.keybindings.next_tab,
                "prev_tab": self.keybindings.prev_tab,
                "focus_input": self.keybindings.focus_input,
            },
            "osc": {
                "port": self.osc.port,
                "enabled": self.osc.enabled,
            },
            "midi": {
                "enabled": self.midi.enabled,
                "device": self.midi.device,
            },
        }


def get_config_path() -> Path:
    """Get the path to the config file.

    Delegates to paths.get_config_file() so there is one definition of where
    config lives. This module used to hardcode ~/.numchuck/config.toml, which
    silently disagreed with the paths module about whether a project-local
    .numchuck may override it.
    """
    return get_config_file()


def load_config(path: Path | str | None = None) -> Config:
    """Load configuration from a TOML file.

    Args:
        path: Path to config file, or None to use default (~/.numchuck/config.toml)

    Returns:
        Config object with loaded settings, or defaults if file doesn't exist
    """
    if path is None:
        path = get_config_path()
    else:
        path = Path(path)

    if not path.exists():
        return Config()

    if tomllib is None:
        # No TOML parser available, return defaults
        import warnings

        warnings.warn(
            "TOML parsing not available. Install 'tomli' for Python < 3.11. "
            "Using default configuration.",
            stacklevel=2,
        )
        return Config()

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return Config.from_dict(data)
    except Exception as e:
        import warnings

        warnings.warn(f"Failed to load config from {path}: {e}", stacklevel=2)
        return Config()


def _format_toml_value(value: Any) -> str:
    """Format a value for TOML output.

    Args:
        value: Value to format

    Returns:
        TOML-formatted string
    """
    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, list):
        items = ", ".join(f'"{v}"' for v in value)
        return f"[{items}]"
    else:
        return str(value)


def save_config(config: Config, path: Path | str | None = None) -> None:
    """Save configuration to a TOML file.

    Args:
        config: Config object to save
        path: Path to config file, or None to use default
    """
    if path is None:
        path = get_config_path()
    else:
        path = Path(path)

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Generate TOML manually (tomllib is read-only)
    lines = []
    data = config.to_dict()

    for section, values in data.items():
        # Check if any values are dicts (nested tables)
        flat_values = {}
        nested_values = {}

        for key, value in values.items():
            if isinstance(value, dict):
                nested_values[key] = value
            else:
                flat_values[key] = value

        # Write section header and flat values
        lines.append(f"[{section}]")
        for key, value in flat_values.items():
            lines.append(f"{key} = {_format_toml_value(value)}")
        lines.append("")

        # Write nested sections
        for nested_key, nested_dict in nested_values.items():
            lines.append(f"[{section}.{nested_key}]")
            for key, value in nested_dict.items():
                lines.append(f"{key} = {_format_toml_value(value)}")
            lines.append("")

    path.write_text("\n".join(lines))


def create_default_config(path: Path | str | None = None) -> Config:
    """Create a default config file if it doesn't exist.

    Args:
        path: Path to config file, or None to use default

    Returns:
        The Config object (either loaded or newly created)
    """
    if path is None:
        path = get_config_path()
    else:
        path = Path(path)

    if path.exists():
        return load_config(path)

    config = Config()
    save_config(config, path)
    return config


# Global config instance (lazy-loaded)
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration.

    Loads from ~/.numchuck/config.toml on first access.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config() -> Config:
    """Reload the global configuration from disk."""
    global _config
    _config = load_config()
    return _config
