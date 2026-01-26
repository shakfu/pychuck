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

    sample_rate: int = 44100
    output_channels: int = 2
    input_channels: int = 0
    buffer_size: int = 512
    num_buffers: int = 8
    dac_device: int = 0
    adc_device: int = 0


@dataclass
class REPLConfig:
    """REPL configuration settings."""

    smart_enter: bool = True
    show_sidebar: bool = True
    start_audio: bool = False
    max_log_lines: int = 100


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
class Config:
    """Complete numchuck configuration.

    Attributes:
        audio: Audio settings (sample rate, channels, etc.)
        repl: REPL interface settings
        editor: Editor interface settings
        paths: File path settings
        chuck: ChucK VM settings
    """

    audio: AudioConfig = field(default_factory=AudioConfig)
    repl: REPLConfig = field(default_factory=REPLConfig)
    editor: EditorConfig = field(default_factory=EditorConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    chuck: ChuckConfig = field(default_factory=ChuckConfig)

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
        }


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".numchuck" / "config.toml"


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
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}")
            elif isinstance(value, str):
                lines.append(f'{key} = "{value}"')
            elif isinstance(value, list):
                items = ", ".join(f'"{v}"' for v in value)
                lines.append(f"{key} = [{items}]")
            else:
                lines.append(f"{key} = {value}")
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
