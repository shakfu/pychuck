"""Tests for the CLI watcher module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from numchuck.cli.watcher import WatchError, cmd_watch, watch_files


class TestWatchFiles:
    """Test watch_files function."""

    def test_no_files_raises_error(self):
        """Test that empty file list raises WatchError."""
        with pytest.raises(WatchError, match="No files provided"):
            watch_files([])

    def test_file_not_found_raises_error(self):
        """Test that nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            watch_files(["nonexistent_file.ck"])

    def test_non_ck_file_raises_error(self, tmp_path):
        """Test that non-.ck file raises WatchError."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not a chuck file")

        with pytest.raises(WatchError, match="Not a ChucK file"):
            watch_files([str(txt_file)])

    def test_mixed_valid_invalid_files(self, tmp_path):
        """Test that validation catches non-.ck file in list."""
        ck_file = tmp_path / "valid.ck"
        txt_file = tmp_path / "invalid.txt"
        ck_file.write_text("440 => SinOsc s => dac;")
        txt_file.write_text("not chuck")

        with pytest.raises(WatchError, match="Not a ChucK file"):
            watch_files([str(ck_file), str(txt_file)])

    def test_successful_initialization(self, tmp_path):
        """Test successful initialization of watch mode."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.shreds = [1]
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = [ck_file]

        # Simulate KeyboardInterrupt after first sleep
        call_count = [0]

        def sleep_then_interrupt(t):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", return_value=mock_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch("numchuck.services.audio.stop_audio"):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=sleep_then_interrupt):
                                    watch_files([str(ck_file)], verbose=False)

        # Verify watcher was started and stopped
        assert mock_watcher.start.call_count == 1
        assert mock_watcher.stop.call_count == 1
        assert mock_chuck.close.call_count == 1

    def test_compilation_failure_continues(self, tmp_path, capsys):
        """Test that compilation failure doesn't stop watching."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("invalid code")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (False, [])
        mock_chuck.shreds = []
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = []

        def immediate_interrupt(t):
            raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", return_value=mock_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch("numchuck.services.audio.stop_audio"):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=immediate_interrupt):
                                    watch_files([str(ck_file)], verbose=True)

        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        # Should still have started watching (even with no successful compiles)
        mock_watcher.start.assert_called_once()

    def test_verbose_output(self, tmp_path, capsys):
        """Test verbose mode output messages."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [42])
        mock_chuck.shreds = [42]
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = [ck_file]

        def immediate_interrupt(t):
            raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", return_value=mock_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch("numchuck.services.audio.stop_audio"):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=immediate_interrupt):
                                    watch_files([str(ck_file)], verbose=True)

        captured = capsys.readouterr()
        assert "Watching 1 file(s)" in captured.out
        assert "Press Ctrl+C to stop" in captured.out
        assert "Loading test.ck" in captured.out
        assert "shred 42" in captured.out
        assert "Audio started" in captured.out
        assert "Done" in captured.out

    def test_quiet_mode(self, tmp_path, capsys):
        """Test that quiet mode suppresses output."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.shreds = [1]
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = [ck_file]

        def immediate_interrupt(t):
            raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", return_value=mock_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch("numchuck.services.audio.stop_audio"):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=immediate_interrupt):
                                    watch_files([str(ck_file)], verbose=False)

        captured = capsys.readouterr()
        # Should have minimal output in quiet mode
        assert "Watching" not in captured.out
        assert "Audio started" not in captured.out

    def test_reload_callback_registration(self, tmp_path):
        """Test that reload and error callbacks are registered."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.shreds = [1]
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()

        captured_callbacks = {}

        def capture_watcher(chuck, session, on_reload, on_error):
            captured_callbacks["on_reload"] = on_reload
            captured_callbacks["on_error"] = on_error
            mock = MagicMock()
            mock.get_watched_files.return_value = [ck_file]
            return mock

        def immediate_interrupt(t):
            raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", side_effect=capture_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch("numchuck.services.audio.stop_audio"):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=immediate_interrupt):
                                    watch_files([str(ck_file)], verbose=False)

        # Callbacks should have been provided
        assert "on_reload" in captured_callbacks
        assert "on_error" in captured_callbacks
        assert callable(captured_callbacks["on_reload"])
        assert callable(captured_callbacks["on_error"])

    def test_stop_audio_error_handled(self, tmp_path):
        """Test that stop_audio RuntimeError is handled gracefully."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.shreds = [1]
        mock_chuck.raw = MagicMock()

        mock_session = MagicMock()
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = [ck_file]

        def immediate_interrupt(t):
            raise KeyboardInterrupt()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("numchuck.tui.session.ChuckSession", return_value=mock_session):
                with patch(
                    "numchuck.watcher.FileWatcher", return_value=mock_watcher
                ):
                    with patch("numchuck.services.audio.start_audio"):
                        with patch(
                            "numchuck.services.audio.stop_audio",
                            side_effect=RuntimeError("Audio not running"),
                        ):
                            with patch("numchuck.services.audio.shutdown_audio"):
                                with patch("time.sleep", side_effect=immediate_interrupt):
                                    # Should not raise despite stop_audio error
                                    watch_files([str(ck_file)], verbose=False)

        # Cleanup should still complete despite stop_audio error
        assert mock_chuck.close.call_count == 1


class TestCmdWatch:
    """Test cmd_watch CLI entry point."""

    def test_file_not_found_exits_with_error(self, capsys):
        """Test that FileNotFoundError causes sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            cmd_watch(["nonexistent.ck"])

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "nonexistent.ck" in captured.err

    def test_watch_error_exits_with_error(self, capsys):
        """Test that WatchError causes sys.exit(1)."""
        with pytest.raises(SystemExit) as exc_info:
            cmd_watch([])  # Empty list triggers WatchError

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "No files provided" in captured.err

    def test_quiet_flag_passed_to_watch_files(self, tmp_path):
        """Test that quiet flag is passed correctly."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        with patch(
            "numchuck.cli.watcher.watch_files", side_effect=KeyboardInterrupt()
        ) as mock_watch:
            try:
                cmd_watch([str(ck_file)], quiet=True)
            except KeyboardInterrupt:
                pass

        mock_watch.assert_called_once()
        call_kwargs = mock_watch.call_args[1]
        assert call_kwargs["verbose"] is False

    def test_sample_rate_and_channels_passed(self, tmp_path):
        """Test that sample_rate and channels are passed correctly."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        with patch(
            "numchuck.cli.watcher.watch_files", side_effect=KeyboardInterrupt()
        ) as mock_watch:
            try:
                cmd_watch([str(ck_file)], sample_rate=48000, channels=4)
            except KeyboardInterrupt:
                pass

        mock_watch.assert_called_once()
        call_kwargs = mock_watch.call_args[1]
        assert call_kwargs["sample_rate"] == 48000
        assert call_kwargs["channels"] == 4


class TestWatchError:
    """Test WatchError exception."""

    def test_exception_message(self):
        """Test that exception preserves message."""
        error = WatchError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Test that WatchError inherits from Exception."""
        assert issubclass(WatchError, Exception)
