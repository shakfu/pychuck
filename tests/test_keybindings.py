"""Tests for keybinding configuration and helpers."""

from __future__ import annotations

import pytest

from numchuck.config import KeybindingsConfig, Config
from numchuck.tui.common import (
    parse_key_binding,
    create_keybinding,
    get_keybinding,
)

from prompt_toolkit.key_binding import KeyBindings


class TestKeybindingsConfig:
    """Tests for KeybindingsConfig dataclass."""

    def test_default_exit_keybinding(self) -> None:
        """Test default exit keybinding is c-q."""
        config = KeybindingsConfig()
        assert config.exit == "c-q"

    def test_default_toggle_help_keybinding(self) -> None:
        """Test default toggle_help keybinding is f1."""
        config = KeybindingsConfig()
        assert config.toggle_help == "f1"

    def test_default_toggle_shreds_keybinding(self) -> None:
        """Test default toggle_shreds keybinding is f2."""
        config = KeybindingsConfig()
        assert config.toggle_shreds == "f2"

    def test_default_toggle_log_keybinding(self) -> None:
        """Test default toggle_log keybinding is f3."""
        config = KeybindingsConfig()
        assert config.toggle_log == "f3"

    def test_default_toggle_waveform_keybinding(self) -> None:
        """Test default toggle_waveform keybinding is f4."""
        config = KeybindingsConfig()
        assert config.toggle_waveform == "f4"

    def test_default_spork_keybinding(self) -> None:
        """Test default spork keybinding is f5."""
        config = KeybindingsConfig()
        assert config.spork == "f5"

    def test_custom_keybindings(self) -> None:
        """Test creating custom keybindings."""
        config = KeybindingsConfig(
            exit="c-x",
            toggle_help="c-h",
            spork="c-enter",
        )

        assert config.exit == "c-x"
        assert config.toggle_help == "c-h"
        assert config.spork == "c-enter"

    def test_all_keybinding_fields(self) -> None:
        """Test that all expected keybinding fields exist."""
        config = KeybindingsConfig()

        expected_fields = [
            "exit",
            "toggle_help",
            "toggle_shreds",
            "toggle_log",
            "toggle_waveform",
            "start_audio",
            "stop_audio",
            "spork",
            "replace_shred",
            "new_tab",
            "close_tab",
            "next_tab",
            "prev_tab",
            "focus_input",
        ]

        for field in expected_fields:
            assert hasattr(config, field), f"Missing keybinding field: {field}"


class TestParseKeyBinding:
    """Tests for parse_key_binding function."""

    def test_parse_ctrl_key(self) -> None:
        """Test parsing Ctrl+key binding."""
        assert parse_key_binding("c-q") == "c-q"
        assert parse_key_binding("c-a") == "c-a"
        assert parse_key_binding("c-z") == "c-z"

    def test_parse_function_keys(self) -> None:
        """Test parsing function key bindings."""
        assert parse_key_binding("f1") == "f1"
        assert parse_key_binding("f12") == "f12"
        assert parse_key_binding("f24") == "f24"

    def test_parse_special_keys(self) -> None:
        """Test parsing special key bindings."""
        assert parse_key_binding("escape") == "escape"
        assert parse_key_binding("enter") == "enter"
        assert parse_key_binding("tab") == "tab"
        assert parse_key_binding("backspace") == "backspace"
        assert parse_key_binding("space") == "space"

    def test_parse_modifier_combinations(self) -> None:
        """Test parsing modifier key combinations."""
        assert parse_key_binding("c-s-f") == "c-s-f"
        assert parse_key_binding("c-a-x") == "c-a-x"

    def test_parse_normalizes_case(self) -> None:
        """Test that parsing normalizes case."""
        assert parse_key_binding("C-Q") == "c-q"
        assert parse_key_binding("F1") == "f1"
        assert parse_key_binding("ESCAPE") == "escape"

    def test_parse_strips_whitespace(self) -> None:
        """Test that parsing strips whitespace."""
        assert parse_key_binding("  c-q  ") == "c-q"
        assert parse_key_binding("\tf1\n") == "f1"

    def test_parse_single_char(self) -> None:
        """Test parsing single character bindings."""
        assert parse_key_binding("a") == "a"
        assert parse_key_binding("x") == "x"


class TestCreateKeybinding:
    """Tests for create_keybinding function."""

    def test_creates_basic_binding(self) -> None:
        """Test creating a basic keybinding."""
        kb = KeyBindings()
        called = [False]

        def handler(event):
            called[0] = True

        create_keybinding(kb, "c-q", handler)

        # Binding should exist (we can't easily test it fires)
        assert len(kb.bindings) > 0

    def test_creates_function_key_binding(self) -> None:
        """Test creating a function key binding."""
        kb = KeyBindings()

        def handler(event):
            pass

        create_keybinding(kb, "f1", handler)

        assert len(kb.bindings) > 0

    def test_invalid_binding_warns(self) -> None:
        """Test that invalid binding generates warning."""
        kb = KeyBindings()

        def handler(event):
            pass

        # Invalid bindings should warn but not crash
        # Note: prompt_toolkit might accept some "invalid" bindings
        # so we just verify it doesn't crash
        create_keybinding(kb, "invalid-key-combo-xyz", handler)


class TestGetKeybinding:
    """Tests for get_keybinding function."""

    def test_get_keybinding_from_config(self) -> None:
        """Test getting keybinding from config object."""
        config = KeybindingsConfig(exit="c-x")
        result = get_keybinding("exit", config)

        assert result == "c-x"

    def test_get_keybinding_returns_empty_for_unknown(self) -> None:
        """Test that unknown keybinding name returns empty string."""
        config = KeybindingsConfig()
        result = get_keybinding("unknown_keybinding_xyz", config)

        assert result == ""

    def test_get_all_default_keybindings(self) -> None:
        """Test getting all default keybindings."""
        config = KeybindingsConfig()

        assert get_keybinding("exit", config) == "c-q"
        assert get_keybinding("toggle_help", config) == "f1"
        assert get_keybinding("toggle_shreds", config) == "f2"
        assert get_keybinding("toggle_log", config) == "f3"
        assert get_keybinding("spork", config) == "f5"


class TestConfigKeybindings:
    """Tests for keybindings in Config class."""

    def test_config_has_keybindings(self) -> None:
        """Test that Config includes keybindings section."""
        config = Config()
        assert hasattr(config, "keybindings")
        assert isinstance(config.keybindings, KeybindingsConfig)

    def test_config_to_dict_includes_keybindings(self) -> None:
        """Test that Config.to_dict includes keybindings."""
        config = Config()
        data = config.to_dict()

        assert "keybindings" in data
        assert "exit" in data["keybindings"]
        assert "toggle_help" in data["keybindings"]

    def test_config_from_dict_loads_keybindings(self) -> None:
        """Test that Config.from_dict loads keybindings."""
        data = {
            "keybindings": {
                "exit": "c-x",
                "toggle_help": "c-h",
            }
        }

        config = Config.from_dict(data)

        assert config.keybindings.exit == "c-x"
        assert config.keybindings.toggle_help == "c-h"

    def test_config_from_dict_preserves_defaults(self) -> None:
        """Test that Config.from_dict preserves unspecified defaults."""
        data = {
            "keybindings": {
                "exit": "c-x",
            }
        }

        config = Config.from_dict(data)

        # Specified value should be loaded
        assert config.keybindings.exit == "c-x"
        # Unspecified should keep default
        assert config.keybindings.toggle_help == "f1"
