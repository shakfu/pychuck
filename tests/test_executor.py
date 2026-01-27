"""Tests for the CLI executor module."""

import signal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from numchuck.cli.executor import ExecutionError, execute_files


class TestExecuteFiles:
    """Test execute_files function."""

    def test_missing_files_raises_error(self):
        """Test that missing files raise ExecutionError."""
        with pytest.raises(ExecutionError, match="One or more files not found"):
            execute_files(["nonexistent_file.ck"])

    def test_multiple_missing_files(self, capsys):
        """Test error output lists all missing files."""
        with pytest.raises(ExecutionError):
            execute_files(["file1.ck", "file2.ck", "file3.ck"])

        captured = capsys.readouterr()
        assert "file1.ck" in captured.err
        assert "file2.ck" in captured.err
        assert "file3.ck" in captured.err

    def test_chuck_initialization_failure(self, tmp_path):
        """Test handling of ChucK VM initialization failure."""
        # Create a valid file
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("<<< 'hello' >>>;")

        with patch("numchuck.api.Chuck") as mock_chuck_class:
            mock_chuck_class.side_effect = RuntimeError("Audio init failed")

            with pytest.raises(ExecutionError, match="ChucK initialization failed"):
                execute_files([str(ck_file)], silent=True)

    def test_compilation_failure(self, tmp_path):
        """Test handling of ChucK compilation failure."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("invalid chuck code !!!")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (False, [])
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with pytest.raises(ExecutionError, match="Failed to compile"):
                execute_files([str(ck_file)], silent=True)

    def test_successful_compilation_silent_mode(self, tmp_path):
        """Test successful compilation in silent mode with duration."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            # Run for 0.1 seconds in silent mode (no audio start)
            execute_files([str(ck_file)], silent=True, duration=0.1)

        # Should have compiled the file
        assert mock_chuck.compile_file.call_count == 1
        assert mock_chuck.compile_file.call_args[0][0] == str(ck_file)
        # Should have removed the shred during cleanup
        assert mock_chuck.remove_shred.call_count == 1
        assert mock_chuck.remove_shred.call_args[0][0] == 1
        # Should have closed the Chuck instance
        assert mock_chuck.close.called

    def test_multiple_files_compilation(self, tmp_path):
        """Test compiling multiple files."""
        file1 = tmp_path / "test1.ck"
        file2 = tmp_path / "test2.ck"
        file1.write_text("440 => SinOsc s => dac;")
        file2.write_text("880 => SinOsc t => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.side_effect = [
            (True, [1]),
            (True, [2]),
        ]
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            execute_files([str(file1), str(file2)], silent=True, duration=0.1)

        # Should have compiled both files
        assert mock_chuck.compile_file.call_count == 2
        # Should have removed both shreds during cleanup
        assert mock_chuck.remove_shred.call_count == 2

    def test_audio_start_failure_continues_silently(self, tmp_path, capsys):
        """Test that audio start failure falls back to silent mode."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch(
                "numchuck._numchuck.start_audio",
                side_effect=RuntimeError("No audio device"),
            ):
                execute_files([str(ck_file)], silent=False, duration=0.1)

        captured = capsys.readouterr()
        assert "Failed to start audio" in captured.err
        assert "Continuing in silent mode" in captured.err

    def test_signal_handler_sets_shutdown(self, tmp_path):
        """Test that signal handler triggers graceful shutdown."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.raw = MagicMock()

        # Capture the signal handler that gets registered
        captured_handler = [None]
        original_signal = signal.signal

        def capture_signal(sig, handler):
            if sig == signal.SIGINT:
                captured_handler[0] = handler
            return original_signal(sig, handler)

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            with patch("signal.signal", side_effect=capture_signal):
                with patch("time.sleep") as mock_sleep:
                    # Simulate signal after first sleep
                    call_count = [0]

                    def sleep_and_signal(t):
                        call_count[0] += 1
                        if call_count[0] == 2 and captured_handler[0]:
                            captured_handler[0](signal.SIGINT, None)

                    mock_sleep.side_effect = sleep_and_signal
                    execute_files([str(ck_file)], silent=True)

        # Should have cleaned up - shred removed and instance closed
        assert mock_chuck.remove_shred.call_count == 1
        assert mock_chuck.remove_shred.call_args[0][0] == 1
        assert mock_chuck.close.called

    def test_output_messages(self, tmp_path, capsys):
        """Test that status messages are printed correctly."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [42])
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck):
            execute_files([str(ck_file)], silent=True, duration=0.1)

        captured = capsys.readouterr()
        assert "[shred 42]" in captured.out
        assert str(ck_file) in captured.out
        assert "Running for 0.1 seconds" in captured.out
        assert "Cleaning up" in captured.out
        assert "Done" in captured.out

    def test_custom_sample_rate_and_channels(self, tmp_path):
        """Test that sample rate and channels are set correctly."""
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("440 => SinOsc s => dac;")

        mock_chuck = MagicMock()
        mock_chuck.compile_file.return_value = (True, [1])
        mock_chuck.raw = MagicMock()

        with patch("numchuck.api.Chuck", return_value=mock_chuck) as mock_class:
            execute_files(
                [str(ck_file)],
                srate=48000,
                channels=4,
                silent=True,
                duration=0.1,
            )

        # Verify Chuck was created with correct parameters
        assert mock_class.call_count == 1
        call_kwargs = mock_class.call_args[1]
        assert call_kwargs["sample_rate"] == 48000
        assert call_kwargs["output_channels"] == 4
        assert call_kwargs["input_channels"] == 0


class TestExecutionError:
    """Test ExecutionError exception."""

    def test_exception_message(self):
        """Test that exception preserves message."""
        error = ExecutionError("Test error message")
        assert str(error) == "Test error message"

    def test_exception_inheritance(self):
        """Test that ExecutionError inherits from Exception."""
        assert issubclass(ExecutionError, Exception)
