"""Tests for theme functionality."""

from __future__ import annotations

import pytest

from numchuck.config import ThemeColors, ThemeConfig
from numchuck.tui.themes import (
    DARK_THEME_COLORS,
    LIGHT_THEME_COLORS,
    MONOKAI_THEME_COLORS,
    SOLARIZED_THEME_COLORS,
    THEME_PALETTES,
    create_default_style,
    create_style,
    get_theme_colors,
    list_available_themes,
)


class TestThemePalettes:
    """Tests for theme color palettes."""

    def test_dark_theme_exists(self) -> None:
        """Test that dark theme palette exists."""
        assert "dark" in THEME_PALETTES
        assert DARK_THEME_COLORS is not None

    def test_light_theme_exists(self) -> None:
        """Test that light theme palette exists."""
        assert "light" in THEME_PALETTES
        assert LIGHT_THEME_COLORS is not None

    def test_solarized_theme_exists(self) -> None:
        """Test that solarized theme palette exists."""
        assert "solarized" in THEME_PALETTES
        assert SOLARIZED_THEME_COLORS is not None

    def test_monokai_theme_exists(self) -> None:
        """Test that monokai theme palette exists."""
        assert "monokai" in THEME_PALETTES
        assert MONOKAI_THEME_COLORS is not None

    def test_all_themes_have_required_colors(self) -> None:
        """Test that all themes have all required color keys."""
        required_keys = [
            "bottom_toolbar_fg",
            "bottom_toolbar_bg",
            "status_bar_fg",
            "status_bar_bg",
            "error_bar_fg",
            "error_bar_bg",
            "help_fg",
            "help_bg",
            "shreds_table_fg",
            "shreds_table_bg",
            "log_fg",
            "log_bg",
            "audio_on_fg",
            "audio_off_fg",
            "prompt_fg",
            "keyword_fg",
            "type_fg",
            "operator_fg",
            "string_fg",
            "comment_fg",
            "number_fg",
        ]

        for theme_name, colors in THEME_PALETTES.items():
            for key in required_keys:
                assert key in colors, f"Theme '{theme_name}' missing key '{key}'"

    def test_all_colors_are_valid_hex(self) -> None:
        """Test that all color values are valid hex colors."""
        import re

        hex_pattern = re.compile(r"^#[0-9a-fA-F]{6}$")

        for theme_name, colors in THEME_PALETTES.items():
            for key, value in colors.items():
                assert hex_pattern.match(
                    value
                ), f"Theme '{theme_name}' key '{key}' has invalid color: {value}"


class TestGetThemeColors:
    """Tests for get_theme_colors function."""

    def test_get_dark_theme(self) -> None:
        """Test getting dark theme colors."""
        config = ThemeConfig(name="dark")
        colors = get_theme_colors(config)

        assert colors == DARK_THEME_COLORS

    def test_get_light_theme(self) -> None:
        """Test getting light theme colors."""
        config = ThemeConfig(name="light")
        colors = get_theme_colors(config)

        assert colors == LIGHT_THEME_COLORS

    def test_get_solarized_theme(self) -> None:
        """Test getting solarized theme colors."""
        config = ThemeConfig(name="solarized")
        colors = get_theme_colors(config)

        assert colors == SOLARIZED_THEME_COLORS

    def test_get_monokai_theme(self) -> None:
        """Test getting monokai theme colors."""
        config = ThemeConfig(name="monokai")
        colors = get_theme_colors(config)

        assert colors == MONOKAI_THEME_COLORS

    def test_get_custom_theme(self) -> None:
        """Test getting custom theme colors."""
        custom_colors = ThemeColors(
            bottom_toolbar_fg="#ff0000",
            bottom_toolbar_bg="#00ff00",
        )
        config = ThemeConfig(name="custom", colors=custom_colors)
        colors = get_theme_colors(config)

        assert colors["bottom_toolbar_fg"] == "#ff0000"
        assert colors["bottom_toolbar_bg"] == "#00ff00"

    def test_unknown_theme_defaults_to_dark(self) -> None:
        """Test that unknown theme name defaults to dark."""
        config = ThemeConfig(name="unknown_theme")
        colors = get_theme_colors(config)

        assert colors == DARK_THEME_COLORS


class TestCreateStyle:
    """Tests for create_style function."""

    def test_create_dark_style(self) -> None:
        """Test creating dark theme style."""
        config = ThemeConfig(name="dark")
        style = create_style(config)

        assert style is not None

    def test_create_light_style(self) -> None:
        """Test creating light theme style."""
        config = ThemeConfig(name="light")
        style = create_style(config)

        assert style is not None

    def test_create_custom_style(self) -> None:
        """Test creating custom theme style."""
        config = ThemeConfig(
            name="custom",
            colors=ThemeColors(prompt_fg="#ff00ff"),
        )
        style = create_style(config)

        assert style is not None

    def test_create_default_style(self) -> None:
        """Test creating default style."""
        style = create_default_style()

        assert style is not None


class TestListAvailableThemes:
    """Tests for list_available_themes function."""

    def test_returns_list(self) -> None:
        """Test that function returns a list."""
        themes = list_available_themes()
        assert isinstance(themes, list)

    def test_includes_all_built_in_themes(self) -> None:
        """Test that all built-in themes are listed."""
        themes = list_available_themes()

        assert "dark" in themes
        assert "light" in themes
        assert "solarized" in themes
        assert "monokai" in themes

    def test_includes_custom(self) -> None:
        """Test that custom is included."""
        themes = list_available_themes()
        assert "custom" in themes


class TestThemeConfig:
    """Tests for ThemeConfig dataclass."""

    def test_default_theme_is_dark(self) -> None:
        """Test that default theme name is dark."""
        config = ThemeConfig()
        assert config.name == "dark"

    def test_default_colors_are_created(self) -> None:
        """Test that default colors are created."""
        config = ThemeConfig()
        assert config.colors is not None
        assert isinstance(config.colors, ThemeColors)


class TestThemeColors:
    """Tests for ThemeColors dataclass."""

    def test_has_all_color_fields(self) -> None:
        """Test that ThemeColors has all required fields."""
        colors = ThemeColors()

        assert hasattr(colors, "bottom_toolbar_fg")
        assert hasattr(colors, "bottom_toolbar_bg")
        assert hasattr(colors, "status_bar_fg")
        assert hasattr(colors, "status_bar_bg")
        assert hasattr(colors, "error_bar_fg")
        assert hasattr(colors, "error_bar_bg")
        assert hasattr(colors, "help_fg")
        assert hasattr(colors, "help_bg")
        assert hasattr(colors, "shreds_table_fg")
        assert hasattr(colors, "shreds_table_bg")
        assert hasattr(colors, "log_fg")
        assert hasattr(colors, "log_bg")
        assert hasattr(colors, "audio_on_fg")
        assert hasattr(colors, "audio_off_fg")
        assert hasattr(colors, "prompt_fg")
        assert hasattr(colors, "keyword_fg")
        assert hasattr(colors, "type_fg")
        assert hasattr(colors, "operator_fg")
        assert hasattr(colors, "string_fg")
        assert hasattr(colors, "comment_fg")
        assert hasattr(colors, "number_fg")

    def test_custom_colors(self) -> None:
        """Test creating custom colors."""
        colors = ThemeColors(
            prompt_fg="#123456",
            error_bar_bg="#654321",
        )

        assert colors.prompt_fg == "#123456"
        assert colors.error_bar_bg == "#654321"
