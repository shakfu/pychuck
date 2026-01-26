"""
Theme support for numchuck TUI.

Provides predefined themes and the ability to create custom themes
from configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.styles import Style

if TYPE_CHECKING:
    from ..config import ThemeColors, ThemeConfig


# =============================================================================
# Predefined Theme Color Palettes
# =============================================================================

DARK_THEME_COLORS = {
    # Bottom toolbar
    "bottom_toolbar_fg": "#aaaaaa",
    "bottom_toolbar_bg": "#333333",
    # Status bar
    "status_bar_fg": "#ffffff",
    "status_bar_bg": "#444444",
    # Error bar
    "error_bar_fg": "#ffffff",
    "error_bar_bg": "#cc0000",
    # Help window
    "help_fg": "#ffffff",
    "help_bg": "#222244",
    # Shreds table
    "shreds_table_fg": "#ffffff",
    "shreds_table_bg": "#224422",
    # Log window
    "log_fg": "#cccccc",
    "log_bg": "#1a1a1a",
    # Audio status
    "audio_on_fg": "#00ff00",
    "audio_off_fg": "#ff6600",
    # Prompt
    "prompt_fg": "#00aaff",
    # Code highlighting
    "keyword_fg": "#ff7700",
    "type_fg": "#00aa00",
    "operator_fg": "#ffffff",
    "string_fg": "#ffff00",
    "comment_fg": "#666666",
    "number_fg": "#00ffff",
}

LIGHT_THEME_COLORS = {
    # Bottom toolbar
    "bottom_toolbar_fg": "#333333",
    "bottom_toolbar_bg": "#cccccc",
    # Status bar
    "status_bar_fg": "#000000",
    "status_bar_bg": "#dddddd",
    # Error bar
    "error_bar_fg": "#ffffff",
    "error_bar_bg": "#cc0000",
    # Help window
    "help_fg": "#000000",
    "help_bg": "#eeeeff",
    # Shreds table
    "shreds_table_fg": "#000000",
    "shreds_table_bg": "#eeffee",
    # Log window
    "log_fg": "#333333",
    "log_bg": "#f5f5f5",
    # Audio status
    "audio_on_fg": "#008800",
    "audio_off_fg": "#cc6600",
    # Prompt
    "prompt_fg": "#0066cc",
    # Code highlighting
    "keyword_fg": "#aa5500",
    "type_fg": "#006600",
    "operator_fg": "#000000",
    "string_fg": "#aa6600",
    "comment_fg": "#888888",
    "number_fg": "#006688",
}

SOLARIZED_THEME_COLORS = {
    # Solarized Dark palette
    # Bottom toolbar
    "bottom_toolbar_fg": "#839496",
    "bottom_toolbar_bg": "#073642",
    # Status bar
    "status_bar_fg": "#fdf6e3",
    "status_bar_bg": "#002b36",
    # Error bar
    "error_bar_fg": "#fdf6e3",
    "error_bar_bg": "#dc322f",
    # Help window
    "help_fg": "#93a1a1",
    "help_bg": "#002b36",
    # Shreds table
    "shreds_table_fg": "#93a1a1",
    "shreds_table_bg": "#073642",
    # Log window
    "log_fg": "#839496",
    "log_bg": "#002b36",
    # Audio status
    "audio_on_fg": "#859900",
    "audio_off_fg": "#cb4b16",
    # Prompt
    "prompt_fg": "#268bd2",
    # Code highlighting
    "keyword_fg": "#cb4b16",
    "type_fg": "#859900",
    "operator_fg": "#93a1a1",
    "string_fg": "#2aa198",
    "comment_fg": "#586e75",
    "number_fg": "#d33682",
}

MONOKAI_THEME_COLORS = {
    # Monokai palette
    # Bottom toolbar
    "bottom_toolbar_fg": "#f8f8f2",
    "bottom_toolbar_bg": "#3e3d32",
    # Status bar
    "status_bar_fg": "#f8f8f2",
    "status_bar_bg": "#49483e",
    # Error bar
    "error_bar_fg": "#f8f8f2",
    "error_bar_bg": "#f92672",
    # Help window
    "help_fg": "#f8f8f2",
    "help_bg": "#272822",
    # Shreds table
    "shreds_table_fg": "#f8f8f2",
    "shreds_table_bg": "#3e3d32",
    # Log window
    "log_fg": "#a6e22e",
    "log_bg": "#272822",
    # Audio status
    "audio_on_fg": "#a6e22e",
    "audio_off_fg": "#fd971f",
    # Prompt
    "prompt_fg": "#66d9ef",
    # Code highlighting
    "keyword_fg": "#f92672",
    "type_fg": "#66d9ef",
    "operator_fg": "#f92672",
    "string_fg": "#e6db74",
    "comment_fg": "#75715e",
    "number_fg": "#ae81ff",
}

# Map theme names to color palettes
THEME_PALETTES = {
    "dark": DARK_THEME_COLORS,
    "light": LIGHT_THEME_COLORS,
    "solarized": SOLARIZED_THEME_COLORS,
    "monokai": MONOKAI_THEME_COLORS,
}


# =============================================================================
# Style Generation
# =============================================================================


def get_theme_colors(theme_config: ThemeConfig) -> dict[str, str]:
    """Get the color palette for a theme configuration.

    Args:
        theme_config: Theme configuration object

    Returns:
        Dictionary mapping color names to hex values
    """
    if theme_config.name in THEME_PALETTES:
        return THEME_PALETTES[theme_config.name].copy()
    elif theme_config.name == "custom":
        # Use colors from the ThemeColors object
        colors = theme_config.colors
        return {
            "bottom_toolbar_fg": colors.bottom_toolbar_fg,
            "bottom_toolbar_bg": colors.bottom_toolbar_bg,
            "status_bar_fg": colors.status_bar_fg,
            "status_bar_bg": colors.status_bar_bg,
            "error_bar_fg": colors.error_bar_fg,
            "error_bar_bg": colors.error_bar_bg,
            "help_fg": colors.help_fg,
            "help_bg": colors.help_bg,
            "shreds_table_fg": colors.shreds_table_fg,
            "shreds_table_bg": colors.shreds_table_bg,
            "log_fg": colors.log_fg,
            "log_bg": colors.log_bg,
            "audio_on_fg": colors.audio_on_fg,
            "audio_off_fg": colors.audio_off_fg,
            "prompt_fg": colors.prompt_fg,
            "keyword_fg": colors.keyword_fg,
            "type_fg": colors.type_fg,
            "operator_fg": colors.operator_fg,
            "string_fg": colors.string_fg,
            "comment_fg": colors.comment_fg,
            "number_fg": colors.number_fg,
        }
    else:
        # Default to dark theme for unknown names
        return DARK_THEME_COLORS.copy()


def create_style(theme_config: ThemeConfig) -> Style:
    """Create a prompt_toolkit Style from theme configuration.

    Args:
        theme_config: Theme configuration object

    Returns:
        prompt_toolkit Style object
    """
    colors = get_theme_colors(theme_config)

    return Style.from_dict(
        {
            # Bottom toolbar (status bar at bottom)
            "bottom-toolbar": f"bg:{colors['bottom_toolbar_bg']} {colors['bottom_toolbar_fg']}",
            "bottom-toolbar.text": colors["bottom_toolbar_fg"],
            # Status bar elements
            "status-bar": f"bg:{colors['status_bar_bg']} {colors['status_bar_fg']}",
            "status-bar.audio-on": f"bold {colors['audio_on_fg']}",
            "status-bar.audio-off": f"{colors['audio_off_fg']}",
            # Error display
            "error-bar": f"bg:{colors['error_bar_bg']} {colors['error_bar_fg']}",
            # Help window
            "help-window": f"bg:{colors['help_bg']} {colors['help_fg']}",
            "help-window.title": f"bold {colors['help_fg']}",
            # Shreds table
            "shreds-table": f"bg:{colors['shreds_table_bg']} {colors['shreds_table_fg']}",
            "shreds-table.header": f"bold {colors['shreds_table_fg']}",
            "shreds-table.id": f"bold {colors['audio_on_fg']}",
            # Log window
            "log-window": f"bg:{colors['log_bg']} {colors['log_fg']}",
            # Prompt
            "prompt": f"bold {colors['prompt_fg']}",
            # Code syntax highlighting (for input)
            "pygments.keyword": colors["keyword_fg"],
            "pygments.keyword.type": colors["type_fg"],
            "pygments.name.builtin": colors["type_fg"],
            "pygments.operator": colors["operator_fg"],
            "pygments.string": colors["string_fg"],
            "pygments.comment": f"italic {colors['comment_fg']}",
            "pygments.number": colors["number_fg"],
        }
    )


def create_default_style() -> Style:
    """Create the default dark theme style.

    Returns:
        prompt_toolkit Style object with dark theme
    """
    from ..config import ThemeConfig

    return create_style(ThemeConfig(name="dark"))


def list_available_themes() -> list[str]:
    """List all available theme names.

    Returns:
        List of theme names
    """
    return list(THEME_PALETTES.keys()) + ["custom"]
