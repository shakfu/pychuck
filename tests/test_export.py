"""Tests for WAV export functionality."""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path

import numpy as np
import pytest

from numchuck.render import (
    RenderError,
    render,
    render_file,
    to_wav,
)


class TestExportToWav:
    """Tests for export_to_wav function."""

    def test_export_simple_sine(self, tmp_path: Path) -> None:
        """Test exporting a simple sine wave to WAV."""
        # Create a simple ChucK file
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text(
            "SinOsc s => dac; 440 => s.freq; 0.5 => s.gain; 1::second => now;"
        )

        output_file = tmp_path / "output.wav"
        result = to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.1,  # Short duration for test
            sample_rate=44100,
            channels=2,
        )

        assert result == output_file
        assert output_file.exists()

        # Verify WAV file properties
        with wave.open(str(output_file), "rb") as wav:
            assert wav.getnchannels() == 2
            assert wav.getframerate() == 44100
            assert wav.getsampwidth() == 2  # 16-bit

    def test_export_custom_sample_rate(self, tmp_path: Path) -> None:
        """Test exporting with custom sample rate."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.05,
            sample_rate=48000,
            channels=1,
        )

        with wave.open(str(output_file), "rb") as wav:
            assert wav.getframerate() == 48000
            assert wav.getnchannels() == 1

    def test_export_mono(self, tmp_path: Path) -> None:
        """Test exporting mono audio."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.1,
            sample_rate=44100,
            channels=1,
        )

        with wave.open(str(output_file), "rb") as wav:
            assert wav.getnchannels() == 1

    def test_export_multiple_files(self, tmp_path: Path) -> None:
        """Test exporting multiple ChucK files."""
        ck_file1 = tmp_path / "osc1.ck"
        ck_file1.write_text(
            "SinOsc s => dac; 440 => s.freq; 0.3 => s.gain; 1::samp => now;"
        )

        ck_file2 = tmp_path / "osc2.ck"
        ck_file2.write_text(
            "SinOsc s => dac; 880 => s.freq; 0.2 => s.gain; 1::samp => now;"
        )

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file1, ck_file2],
            duration=0.1,
        )

        assert output_file.exists()

    def test_export_no_files_raises(self, tmp_path: Path) -> None:
        """Test that exporting with no files raises an error."""
        output_file = tmp_path / "output.wav"
        with pytest.raises(RenderError, match="No ChucK files provided"):
            to_wav(output=output_file, files=[], duration=1.0)

    def test_export_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that exporting a missing file raises an error."""
        output_file = tmp_path / "output.wav"
        with pytest.raises(FileNotFoundError):
            to_wav(
                output=output_file,
                files=[tmp_path / "nonexistent.ck"],
                duration=1.0,
            )

    def test_export_invalid_code_raises(self, tmp_path: Path) -> None:
        """Test that exporting invalid ChucK code raises an error."""
        ck_file = tmp_path / "invalid.ck"
        ck_file.write_text("this is not valid ChucK code @#$%")

        output_file = tmp_path / "output.wav"
        with pytest.raises(RenderError, match="Failed to compile"):
            to_wav(
                output=output_file,
                files=[ck_file],
                duration=0.1,
            )

    def test_export_creates_nonzero_audio(self, tmp_path: Path) -> None:
        """Test that exported audio actually contains sound."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text(
            "SinOsc s => dac; 440 => s.freq; 0.5 => s.gain; 0.1::second => now;"
        )

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.1,
            sample_rate=44100,
            channels=2,
        )

        # Read the WAV file and check it's not all zeros
        with wave.open(str(output_file), "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)
            # Audio should have some non-zero samples
            assert np.any(data != 0), "Audio output should not be all zeros"


class TestExportCodeToWav:
    """Tests for export_code_to_wav function."""

    def test_export_inline_code(self, tmp_path: Path) -> None:
        """Test exporting inline ChucK code."""
        output_file = tmp_path / "output.wav"
        code = "SinOsc s => dac; 440 => s.freq; 1::samp => now;"

        result = to_wav(
            output=output_file,
            code=code,
            duration=0.1,
        )

        assert result == output_file
        assert output_file.exists()

    def test_export_code_custom_params(self, tmp_path: Path) -> None:
        """Test exporting code with custom parameters."""
        output_file = tmp_path / "output.wav"
        code = "SinOsc s => dac; 1::samp => now;"

        to_wav(
            output=output_file,
            code=code,
            duration=0.05,
            sample_rate=22050,
            channels=1,
        )

        with wave.open(str(output_file), "rb") as wav:
            assert wav.getframerate() == 22050
            assert wav.getnchannels() == 1

    def test_export_invalid_code_raises(self, tmp_path: Path) -> None:
        """Test that exporting invalid code raises an error."""
        output_file = tmp_path / "output.wav"

        with pytest.raises(RenderError, match="Failed to compile"):
            to_wav(
                output=output_file,
                code="invalid code @#$%",
                duration=0.1,
            )

    def test_export_code_creates_audio(self, tmp_path: Path) -> None:
        """Test that exported code produces audio."""
        output_file = tmp_path / "output.wav"
        code = "SinOsc s => dac; 440 => s.freq; 0.5 => s.gain; 0.1::second => now;"

        to_wav(
            output=output_file,
            code=code,
            duration=0.1,
        )

        with wave.open(str(output_file), "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            data = np.frombuffer(frames, dtype=np.int16)
            assert np.any(data != 0), "Audio output should not be all zeros"


class TestExportChunking:
    """Tests for chunked rendering."""

    def test_export_with_small_chunk_size(self, tmp_path: Path) -> None:
        """Test that small chunk size still produces correct output."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.1,
            chunk_size=256,  # Small chunk size
        )

        assert output_file.exists()
        with wave.open(str(output_file), "rb") as wav:
            # Verify expected duration
            expected_frames = int(0.1 * 44100)
            assert wav.getnframes() == expected_frames

    def test_export_with_large_chunk_size(self, tmp_path: Path) -> None:
        """Test that large chunk size still produces correct output."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        output_file = tmp_path / "output.wav"
        to_wav(
            output=output_file,
            files=[ck_file],
            duration=0.1,
            chunk_size=8192,  # Large chunk size
        )

        assert output_file.exists()


class TestRenderToBuffer:
    """Tests for render_to_buffer function."""

    def test_render_returns_array(self, tmp_path: Path) -> None:
        """Test that render returns a numpy array."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 440 => s.freq; 1::samp => now;")

        audio = render_file([ck_file], duration=0.1)

        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32

    def test_render_correct_shape(self, tmp_path: Path) -> None:
        """Test that rendered buffer has correct shape."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        audio = render_file(
            [ck_file],
            duration=0.1,
            sample_rate=44100,
            channels=2,
        )

        expected_samples = int(0.1 * 44100) * 2  # stereo interleaved
        assert len(audio) == expected_samples

    def test_render_mono(self, tmp_path: Path) -> None:
        """Test rendering mono audio."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        audio = render_file(
            [ck_file],
            duration=0.1,
            sample_rate=44100,
            channels=1,
        )

        expected_samples = int(0.1 * 44100)  # mono
        assert len(audio) == expected_samples

    def test_render_int16_dtype(self, tmp_path: Path) -> None:
        """Test rendering with int16 dtype."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 0.5 => s.gain; 1::samp => now;")

        audio = render_file([ck_file], duration=0.1, dtype=np.int16)

        assert audio.dtype == np.int16

    def test_render_memoryview(self, tmp_path: Path) -> None:
        """Test that buffer can be accessed as memoryview."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text("SinOsc s => dac; 1::samp => now;")

        audio = render_file([ck_file], duration=0.1)

        # Both ways to get memoryview should work
        mv1 = memoryview(audio)
        mv2 = audio.data

        assert mv1 is not None
        assert mv2 is not None
        assert len(mv1) == len(audio)  # memoryview length equals array length
        assert mv1.nbytes == len(audio) * audio.itemsize  # total bytes

    def test_render_no_files_raises(self) -> None:
        """Test that rendering with no files raises error."""
        with pytest.raises(RenderError, match="No ChucK files provided"):
            render_file([])

    def test_render_missing_file_raises(self, tmp_path: Path) -> None:
        """Test that rendering missing file raises error."""
        with pytest.raises(FileNotFoundError):
            render_file([tmp_path / "nonexistent.ck"])

    def test_render_produces_audio(self, tmp_path: Path) -> None:
        """Test that rendered buffer contains actual audio."""
        ck_file = tmp_path / "sine.ck"
        ck_file.write_text(
            "SinOsc s => dac; 440 => s.freq; 0.5 => s.gain; 0.1::second => now;"
        )

        audio = render_file([ck_file], duration=0.1)

        assert np.any(audio != 0), "Audio should not be all zeros"


class TestRenderCodeToBuffer:
    """Tests for render_code_to_buffer function."""

    def test_render_code_returns_array(self) -> None:
        """Test that render_code returns a numpy array."""
        code = "SinOsc s => dac; 1::samp => now;"
        audio = render(code, duration=0.1)

        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32

    def test_render_code_correct_length(self) -> None:
        """Test that rendered code buffer has correct length."""
        code = "SinOsc s => dac; 1::samp => now;"
        audio = render(
            code,
            duration=0.1,
            sample_rate=44100,
            channels=2,
        )

        expected = int(0.1 * 44100) * 2
        assert len(audio) == expected

    def test_render_code_int16(self) -> None:
        """Test rendering code with int16 dtype."""
        code = "SinOsc s => dac; 0.5 => s.gain; 1::samp => now;"
        audio = render(code, duration=0.1, dtype=np.int16)

        assert audio.dtype == np.int16

    def test_render_code_memoryview(self) -> None:
        """Test that code buffer can be accessed as memoryview."""
        code = "SinOsc s => dac; 1::samp => now;"
        audio = render(code, duration=0.1)

        mv = memoryview(audio)
        assert len(mv) > 0

    def test_render_invalid_code_raises(self) -> None:
        """Test that invalid code raises error."""
        with pytest.raises(RenderError, match="Failed to compile"):
            render("invalid code @#$%", duration=0.1)

    def test_render_code_produces_audio(self) -> None:
        """Test that rendered code produces actual audio."""
        code = "SinOsc s => dac; 440 => s.freq; 0.5 => s.gain; 0.1::second => now;"
        audio = render(code, duration=0.1)

        assert np.any(audio != 0), "Audio should not be all zeros"
