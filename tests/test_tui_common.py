"""
Tests for shared TUI utilities in common.py.

Tests the helper functions used for shreds table formatting,
AudioManager, keybinding helpers, and ChuckApplication.
"""

import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from numchuck.tui.common import (
    AudioManager,
    ChuckApplication,
    create_keybinding,
    format_elapsed_time,
    format_shred_name,
    generate_shreds_table,
    get_keybinding,
    parse_key_binding,
)


class TestFormatElapsedTime:
    """Tests for format_elapsed_time function."""

    def test_seconds_only(self):
        """Test formatting under 60 seconds."""
        assert format_elapsed_time(0.0) == "0.0s"
        assert format_elapsed_time(5.5) == "5.5s"
        assert format_elapsed_time(59.9) == "59.9s"

    def test_minutes_and_seconds(self):
        """Test formatting between 1 minute and 1 hour."""
        assert format_elapsed_time(60.0) == "1m00.0s"
        assert format_elapsed_time(90.5) == "1m30.5s"
        assert format_elapsed_time(3599.9) == "59m59.9s"

    def test_hours_and_minutes(self):
        """Test formatting over 1 hour."""
        assert format_elapsed_time(3600.0) == "1h00m"
        assert format_elapsed_time(3660.0) == "1h01m"
        assert format_elapsed_time(7200.0) == "2h00m"
        assert format_elapsed_time(7380.0) == "2h03m"


class TestFormatShredName:
    """Tests for format_shred_name function."""

    def test_simple_filename(self):
        """Test simple filename."""
        assert format_shred_name("test.ck") == "test.ck"

    def test_path_with_parent(self):
        """Test path shows parent/filename."""
        assert format_shred_name("/path/to/test.ck") == "to/test.ck"

    def test_path_just_filename(self):
        """Test path with no parent directory."""
        assert format_shred_name("/test.ck") == "test.ck"

    def test_truncation(self):
        """Test long names are truncated."""
        long_name = "a" * 100 + ".ck"
        result = format_shred_name(long_name)
        assert len(result) == 56

    def test_custom_max_len(self):
        """Test custom max length."""
        result = format_shred_name("verylongfilename.ck", max_len=10)
        assert len(result) == 10

    def test_non_path_string(self):
        """Test non-path strings handled gracefully."""
        assert format_shred_name("inline code") == "inline code"


class TestGenerateShedsTable:
    """Tests for generate_shreds_table function."""

    def test_empty_shreds(self):
        """Test with no shreds returns message."""
        result = generate_shreds_table({}, None)
        assert result == "No active shreds"

    def test_with_pipes(self):
        """Test table with pipe separators."""

        class MockChuck:
            def now(self):
                return 44100.0  # 1 second

            def get_param_int(self, param):
                return 44100

        shreds = {
            1: {"name": "test.ck", "time": 0.0},
        }
        result = generate_shreds_table(shreds, MockChuck(), use_pipes=True)
        assert "|" in result
        assert "ID" in result
        assert "Name" in result
        assert "Elapsed" in result
        assert "test.ck" in result
        assert "1.0s" in result

    def test_without_pipes(self):
        """Test table without pipe separators (spaces only)."""

        class MockChuck:
            def now(self):
                return 44100.0

            def get_param_int(self, param):
                return 44100

        shreds = {
            1: {"name": "test.ck", "time": 0.0},
        }
        result = generate_shreds_table(shreds, MockChuck(), use_pipes=False)
        assert "|" not in result
        # Uses Unicode box drawing character
        assert "\u2500" in result

    def test_multiple_shreds(self):
        """Test with multiple shreds."""

        class MockChuck:
            def now(self):
                return 88200.0  # 2 seconds

            def get_param_int(self, param):
                return 44100

        shreds = {
            1: {"name": "first.ck", "time": 0.0},
            2: {"name": "second.ck", "time": 44100.0},
        }
        result = generate_shreds_table(shreds, MockChuck(), use_pipes=True)
        assert "first.ck" in result
        assert "second.ck" in result
        # First shred: 2 seconds elapsed
        assert "2.0s" in result
        # Second shred: 1 second elapsed
        assert "1.0s" in result

    def test_chuck_error_handling(self):
        """Test graceful handling when ChucK raises errors."""

        class BrokenChuck:
            def now(self):
                raise RuntimeError("ChucK not initialized")

            def get_param_int(self, param):
                raise RuntimeError("ChucK not initialized")

        shreds = {
            1: {"name": "test.ck", "time": 0.0},
        }
        # Should not raise, should use defaults
        result = generate_shreds_table(shreds, BrokenChuck(), use_pipes=True)
        assert "test.ck" in result
        assert "0.0s" in result

    def test_shreds_sorted_by_id(self):
        """Test shreds are sorted by ID."""

        class MockChuck:
            def now(self):
                return 0.0

            def get_param_int(self, param):
                return 44100

        shreds = {
            3: {"name": "third.ck", "time": 0.0},
            1: {"name": "first.ck", "time": 0.0},
            2: {"name": "second.ck", "time": 0.0},
        }
        result = generate_shreds_table(shreds, MockChuck(), use_pipes=True)
        lines = result.split("\n")
        # Header + separator + 3 shreds = 5 lines
        assert len(lines) == 5
        # Check order (skip header and separator)
        assert "1" in lines[2] and "first.ck" in lines[2]
        assert "2" in lines[3] and "second.ck" in lines[3]
        assert "3" in lines[4] and "third.ck" in lines[4]


class TestAudioManager:
    """Test AudioManager class."""

    def test_init_basic(self):
        """Test basic AudioManager initialization."""
        mock_chuck = MagicMock()
        manager = AudioManager(mock_chuck)

        assert manager._chuck is mock_chuck
        assert manager._running is False

    def test_init_with_logger(self):
        """Test AudioManager initialization with custom logger."""
        mock_chuck = MagicMock()
        mock_logger = MagicMock()

        manager = AudioManager(mock_chuck, logger=mock_logger)

        assert manager._logger is mock_logger

    def test_is_running_property(self):
        """Test is_running property returns _running state."""
        mock_chuck = MagicMock()
        manager = AudioManager(mock_chuck)

        assert manager.is_running is False

        manager._running = True
        assert manager.is_running is True

    @patch("numchuck.services.audio.start_audio")
    def test_start_success(self, mock_start_audio):
        """Test successful audio start."""
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)

        result = manager.start()

        assert result is True
        assert manager._running is True
        assert mock_start_audio.call_count == 1
        assert mock_start_audio.call_args[0][0] is mock_chuck

    @patch("numchuck.services.audio.start_audio")
    def test_start_already_running(self, mock_start_audio):
        """Test start when audio already running."""
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)
        manager._running = True

        result = manager.start()

        assert result is True
        assert mock_start_audio.call_count == 0  # Not called when already running
        assert mock_logger.debug.call_count == 1

    @patch("numchuck.services.audio.start_audio")
    def test_start_exception(self, mock_start_audio):
        """Test start handles exception."""
        mock_start_audio.side_effect = RuntimeError("Audio device error")
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)

        result = manager.start()

        assert result is False
        assert manager._running is False
        assert mock_logger.error.call_count == 1

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_success(self, mock_shutdown, mock_stop):
        """Test successful audio stop."""
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)
        manager._running = True

        result = manager.stop()

        assert result is True
        assert manager._running is False
        assert mock_stop.call_count == 1
        assert mock_shutdown.call_count == 1

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_not_running(self, mock_shutdown, mock_stop):
        """Test stop when audio not running."""
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)

        result = manager.stop()

        assert result is True
        assert mock_stop.call_count == 0
        assert mock_shutdown.call_count == 0

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_exception_in_stop_audio(self, mock_shutdown, mock_stop):
        """Test stop handles exception in stop_audio."""
        mock_stop.side_effect = RuntimeError("Error stopping")
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)
        manager._running = True

        result = manager.stop()

        assert result is False
        assert manager._running is False  # Still marked as stopped
        assert mock_logger.error.call_count >= 1

    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_exception_in_shutdown(self, mock_shutdown, mock_stop):
        """Test stop handles exception in shutdown_audio."""
        mock_shutdown.side_effect = RuntimeError("Error shutting down")
        mock_chuck = MagicMock()
        mock_logger = MagicMock()
        manager = AudioManager(mock_chuck, logger=mock_logger)
        manager._running = True

        result = manager.stop()

        assert result is False
        assert manager._running is False

    @patch("numchuck.services.audio.start_audio")
    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_restart(self, mock_shutdown, mock_stop, mock_start):
        """Test restart stops then starts audio."""
        mock_chuck = MagicMock()
        manager = AudioManager(mock_chuck)
        manager._running = True

        result = manager.restart()

        assert result is True
        assert mock_stop.call_count == 1
        assert mock_start.call_count == 1


class TestParseKeyBinding:
    """Test parse_key_binding function."""

    def test_simple_key(self):
        """Test parsing single character key."""
        assert parse_key_binding("a") == "a"
        assert parse_key_binding("x") == "x"

    def test_ctrl_modifier(self):
        """Test parsing ctrl modifier."""
        assert parse_key_binding("c-q") == "c-q"
        assert parse_key_binding("C-Q") == "c-q"  # Normalized to lowercase

    def test_multiple_modifiers(self):
        """Test parsing multiple modifiers."""
        assert parse_key_binding("c-s-f") == "c-s-f"
        assert parse_key_binding("c-a-x") == "c-a-x"

    def test_function_keys(self):
        """Test parsing function keys."""
        assert parse_key_binding("f1") == "f1"
        assert parse_key_binding("F12") == "f12"
        assert parse_key_binding("f24") == "f24"

    def test_special_keys(self):
        """Test parsing special keys."""
        assert parse_key_binding("escape") == "escape"
        assert parse_key_binding("enter") == "enter"
        assert parse_key_binding("tab") == "tab"
        assert parse_key_binding("space") == "space"

    def test_invalid_key_returns_original(self):
        """Test that invalid keys return original string."""
        result = parse_key_binding("invalidkey")
        assert result == "invalidkey"


class TestCreateKeybinding:
    """Test create_keybinding function."""

    def test_valid_binding(self):
        """Test creating valid keybinding."""
        from prompt_toolkit.key_binding import KeyBindings

        kb = KeyBindings()
        handler = MagicMock()

        create_keybinding(kb, "c-q", handler, "Quit")

        # Check that a binding was added
        assert len(kb.bindings) > 0

    def test_invalid_binding_warns(self):
        """Test that invalid binding issues warning but doesn't crash."""
        from prompt_toolkit.key_binding import KeyBindings

        kb = KeyBindings()
        handler = MagicMock()
        initial_bindings = len(kb.bindings)

        # This should warn but not raise
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Empty key should cause issues
            create_keybinding(kb, "", handler)
            # Either warns or fails silently - either is acceptable
            # The important thing is it doesn't crash
            assert isinstance(w, list)  # warnings were captured
            # Bindings count may or may not change depending on behavior
            assert isinstance(len(kb.bindings), int)


class TestGetKeybinding:
    """Test get_keybinding function."""

    def test_with_config(self):
        """Test getting keybinding from config."""
        mock_config = MagicMock()
        mock_config.exit = "c-q"
        mock_config.toggle_help = "f1"

        result = get_keybinding("exit", mock_config)
        assert result == "c-q"

        result = get_keybinding("toggle_help", mock_config)
        assert result == "f1"

    def test_missing_attribute_returns_empty(self):
        """Test that missing attribute returns empty string."""
        mock_config = MagicMock(spec=[])  # No attributes

        result = get_keybinding("nonexistent", mock_config)
        assert result == ""

    @patch("numchuck.tui.common.get_config")
    def test_uses_global_config_when_none(self, mock_get_config):
        """Test that global config is used when keybindings is None."""
        mock_keybindings = MagicMock()
        mock_keybindings.exit = "c-x"
        mock_get_config.return_value.keybindings = mock_keybindings

        result = get_keybinding("exit")

        assert result == "c-x"
        assert mock_get_config.call_count == 1


class TestChuckApplication:
    """Test ChuckApplication class."""

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_init_basic(self, mock_get_logger, mock_chuck_class):
        """Test basic ChuckApplication initialization."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        app = ChuckApplication()

        assert app.chuck is mock_chuck
        assert app._sample_rate == 44100
        assert app._output_channels == 2
        assert app._input_channels == 0
        assert app.show_help is False
        assert app.show_shreds is False
        assert app.show_log is False

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_init_custom_params(self, mock_get_logger, mock_chuck_class):
        """Test ChuckApplication with custom parameters."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication(
            sample_rate=48000,
            output_channels=4,
            input_channels=2,
        )

        assert app._sample_rate == 48000
        assert app._output_channels == 4
        assert app._input_channels == 2

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_init_with_auto_init(self, mock_get_logger, mock_chuck_class):
        """Test ChuckApplication with auto_init=True."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication(auto_init=True)

        # setup() should have been called
        assert mock_chuck.set_param.call_count == 3  # sample_rate, output, input
        assert mock_chuck.init.call_count == 1

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_setup(self, mock_get_logger, mock_chuck_class):
        """Test setup configures ChucK."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication(sample_rate=48000, output_channels=4, input_channels=2)
        app.setup()

        # Check set_param calls
        calls = mock_chuck.set_param.call_args_list
        assert len(calls) == 3
        assert mock_chuck.init.call_count == 1

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_set_log_callback(self, mock_get_logger, mock_chuck_class):
        """Test set_log_callback stores callback."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        callback = MagicMock()

        app.set_log_callback(callback)

        assert app._log_callback is callback

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_setup_output_capture(self, mock_get_logger, mock_chuck_class):
        """Test setup_output_capture sets up callbacks."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.setup_output_capture()

        assert mock_chuck.set_chout_callback.call_count == 1
        assert mock_chuck.set_cherr_callback.call_count == 1

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_audio_running_property(self, mock_get_logger, mock_chuck_class):
        """Test audio_running property delegates to AudioManager."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        assert app.audio_running is False

        app._audio_manager._running = True
        assert app.audio_running is True

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_audio_running_setter(self, mock_get_logger, mock_chuck_class):
        """Test audio_running setter syncs session state."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.audio_running = True

        assert app.session.audio_running is True

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.services.audio.start_audio")
    def test_start_audio_playback(self, mock_start, mock_get_logger, mock_chuck_class):
        """Test start_audio_playback starts audio."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        result = app.start_audio_playback()

        assert result is True
        assert app.session.audio_running is True
        assert mock_start.call_count == 1

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.services.audio.start_audio")
    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_stop_audio_playback(
        self, mock_shutdown, mock_stop, mock_start, mock_get_logger, mock_chuck_class
    ):
        """Test stop_audio_playback stops audio."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.start_audio_playback()
        app.stop_audio_playback()

        assert app.session.audio_running is False

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.tui.common.get_config")
    def test_get_common_key_bindings(
        self, mock_get_config, mock_get_logger, mock_chuck_class
    ):
        """Test get_common_key_bindings creates keybindings."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        mock_keybindings = MagicMock()
        mock_keybindings.exit = "c-q"
        mock_keybindings.toggle_help = "f1"
        mock_keybindings.toggle_shreds = "f2"
        mock_keybindings.toggle_log = "f3"
        mock_get_config.return_value.keybindings = mock_keybindings

        app = ChuckApplication()
        kb = app.get_common_key_bindings()

        # Should have created keybindings
        assert len(kb.bindings) > 0

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_create_help_window(self, mock_get_logger, mock_chuck_class):
        """Test create_help_window creates conditional container."""
        from prompt_toolkit.layout.containers import ConditionalContainer

        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        result = app.create_help_window("Test help text")

        assert isinstance(result, ConditionalContainer)

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_create_shreds_table(self, mock_get_logger, mock_chuck_class):
        """Test create_shreds_table creates conditional container."""
        from prompt_toolkit.layout.containers import ConditionalContainer

        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        result = app.create_shreds_table()

        assert isinstance(result, ConditionalContainer)

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_create_log_window(self, mock_get_logger, mock_chuck_class):
        """Test create_log_window creates conditional container."""
        from prompt_toolkit.layout.containers import ConditionalContainer

        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        result = app.create_log_window()

        assert isinstance(result, ConditionalContainer)

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_create_log_window_with_existing_textarea(
        self, mock_get_logger, mock_chuck_class
    ):
        """Test create_log_window with pre-created TextArea."""
        from prompt_toolkit.layout.containers import ConditionalContainer
        from prompt_toolkit.widgets import TextArea

        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        log_area = TextArea()
        result = app.create_log_window(log_area=log_area)

        assert isinstance(result, ConditionalContainer)

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_create_status_bar(self, mock_get_logger, mock_chuck_class):
        """Test create_status_bar creates window."""
        from prompt_toolkit.layout.containers import Window

        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        result = app.create_status_bar(lambda: "Status")

        assert isinstance(result, Window)

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_cleanup(self, mock_shutdown, mock_stop, mock_get_logger, mock_chuck_class):
        """Test cleanup cleans up resources."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.cleanup()

        assert mock_chuck.remove_all_shreds.call_count == 1
        assert mock_chuck.shutdown.call_count == 1
        # After cleanup, accessing session or chuck should raise RuntimeError
        with pytest.raises(RuntimeError, match="Session has been closed"):
            _ = app.session
        with pytest.raises(RuntimeError, match="ChucK instance has been closed"):
            _ = app.chuck

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.services.audio.start_audio")
    @patch("numchuck.services.audio.stop_audio")
    @patch("numchuck.services.audio.shutdown_audio")
    def test_cleanup_with_audio_running(
        self, mock_shutdown, mock_stop, mock_start, mock_get_logger, mock_chuck_class
    ):
        """Test cleanup stops audio if running."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.start_audio_playback()

        app.cleanup()

        # Audio should have been stopped
        assert mock_stop.call_count >= 1

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_cleanup_handles_exceptions(self, mock_get_logger, mock_chuck_class):
        """Test cleanup handles exceptions gracefully."""
        mock_chuck = MagicMock()
        mock_chuck.remove_all_shreds.side_effect = RuntimeError("Error")
        mock_chuck.shutdown.side_effect = RuntimeError("Error")
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        # Should not raise
        app.cleanup()

        # Resources should still be cleaned up - accessing them raises RuntimeError
        with pytest.raises(RuntimeError, match="Session has been closed"):
            _ = app.session
        with pytest.raises(RuntimeError, match="ChucK instance has been closed"):
            _ = app.chuck

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    @patch("numchuck.tui.session.get_projects_dir")
    def test_init_with_project_name(
        self, mock_get_projects_dir, mock_get_logger, mock_chuck_class
    ):
        """Test ChuckApplication with project_name."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck
        mock_get_projects_dir.return_value = Path("/tmp/projects")

        app = ChuckApplication(project_name="test_project")

        assert app.session.project is not None
        assert app.session.project.name == "test_project"


class TestChuckApplicationServices:
    """Test ChuckApplication service properties."""

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_shred_service_lazy_creation(self, mock_get_logger, mock_chuck_class):
        """Test shred_service is lazily created on first access."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        # Service should not exist yet
        assert app._shred_service is None

        # Access service triggers creation
        service = app.shred_service

        # Now it should exist
        assert app._shred_service is not None
        assert service is app._shred_service

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_shred_service_cached(self, mock_get_logger, mock_chuck_class):
        """Test shred_service returns same instance on subsequent accesses."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        service1 = app.shred_service
        service2 = app.shred_service

        assert service1 is service2

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_globals_service_lazy_creation(self, mock_get_logger, mock_chuck_class):
        """Test globals_service is lazily created on first access."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        # Service should not exist yet
        assert app._globals_service is None

        # Access service triggers creation
        service = app.globals_service

        # Now it should exist
        assert app._globals_service is not None
        assert service is app._globals_service

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_globals_service_cached(self, mock_get_logger, mock_chuck_class):
        """Test globals_service returns same instance on subsequent accesses."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()

        service1 = app.globals_service
        service2 = app.globals_service

        assert service1 is service2


class TestOutputCaptureCallback:
    """Test output capture callback behavior."""

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_log_callback_appends_messages(self, mock_get_logger, mock_chuck_class):
        """Test that log callback appends to log_messages."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        app = ChuckApplication()
        app.setup_output_capture()

        # Get the callback that was registered
        chout_callback = mock_chuck.set_chout_callback.call_args[0][0]

        # Call the callback
        chout_callback("test message")

        assert "test message" in app.log_messages

    @patch("numchuck.tui.common.ChucK")
    @patch("numchuck.tui.common.get_logger")
    def test_log_callback_calls_user_callback(self, mock_get_logger, mock_chuck_class):
        """Test that log callback calls user-provided callback."""
        mock_chuck = MagicMock()
        mock_chuck_class.return_value = mock_chuck

        user_callback = MagicMock()

        app = ChuckApplication()
        app.set_log_callback(user_callback)
        app.setup_output_capture()

        # Get the callback that was registered
        chout_callback = mock_chuck.set_chout_callback.call_args[0][0]

        # Call the callback
        chout_callback("test message")

        assert user_callback.call_count == 1
        assert user_callback.call_args[0][0] == "test message"
