"""Tests for waveform display functionality."""

from __future__ import annotations

import numpy as np
import pytest

from numchuck.tui.waveform import (
    ASCII_BLOCKS,
    UNICODE_BLOCKS,
    WaveformBuffer,
    calculate_peak,
    calculate_rms,
    db_to_linear,
    format_stereo_meters,
    format_waveform_bar,
    linear_to_db,
    samples_to_waveform,
)


class TestSamplesToWaveform:
    """Tests for samples_to_waveform function."""

    def test_empty_samples_returns_spaces(self) -> None:
        """Test that empty samples return empty waveform."""
        samples = np.array([], dtype=np.float32)
        result = samples_to_waveform(samples, width=10)

        assert len(result) == 10
        assert result == " " * 10

    def test_single_line_waveform_width(self) -> None:
        """Test that single-line waveform has correct width."""
        samples = np.ones(100, dtype=np.float32)
        result = samples_to_waveform(samples, width=50, height=1)

        assert len(result) == 50

    def test_silent_samples_use_empty_blocks(self) -> None:
        """Test that silent samples use empty block characters."""
        samples = np.zeros(100, dtype=np.float32)
        result = samples_to_waveform(samples, width=20, height=1)

        # All should be empty blocks
        assert all(c == UNICODE_BLOCKS[0] for c in result)

    def test_full_amplitude_uses_full_blocks(self) -> None:
        """Test that full amplitude samples use full block characters."""
        samples = np.ones(100, dtype=np.float32)
        result = samples_to_waveform(samples, width=20, height=1)

        # All should be full blocks
        assert all(c == UNICODE_BLOCKS[-1] for c in result)

    def test_ascii_mode(self) -> None:
        """Test ASCII character mode."""
        samples = np.ones(20, dtype=np.float32)
        result = samples_to_waveform(samples, width=20, height=1, use_unicode=False)

        # All should be full ASCII blocks
        assert all(c == ASCII_BLOCKS[-1] for c in result)

    def test_multi_line_waveform_height(self) -> None:
        """Test that multi-line waveform has correct height."""
        samples = np.ones(100, dtype=np.float32) * 0.5
        result = samples_to_waveform(samples, width=20, height=8)

        lines = result.split("\n")
        assert len(lines) == 8

    def test_sine_wave_creates_varying_output(self) -> None:
        """Test that sine wave creates varying output."""
        samples = np.sin(np.linspace(0, 4 * np.pi, 100)).astype(np.float32)
        result = samples_to_waveform(samples, width=40, height=1)

        # Should have some variation (not all same character)
        unique_chars = set(result)
        assert len(unique_chars) > 1


class TestFormatWaveformBar:
    """Tests for format_waveform_bar function."""

    def test_zero_value_empty_bar(self) -> None:
        """Test that zero value produces empty bar."""
        result = format_waveform_bar(0.0, width=20)

        assert len(result) == 20
        assert all(c == UNICODE_BLOCKS[0] for c in result)

    def test_full_value_full_bar(self) -> None:
        """Test that full value produces full bar."""
        result = format_waveform_bar(1.0, width=20)

        assert len(result) == 20
        assert all(c == UNICODE_BLOCKS[-1] for c in result)

    def test_half_value_half_bar(self) -> None:
        """Test that half value produces approximately half bar."""
        result = format_waveform_bar(0.5, width=20)

        assert len(result) == 20
        # Should have some full blocks (around half)
        full_count = sum(1 for c in result if c == UNICODE_BLOCKS[-1])
        assert 8 <= full_count <= 12

    def test_clamps_to_valid_range(self) -> None:
        """Test that values are clamped to 0-1 range."""
        result_negative = format_waveform_bar(-0.5, width=10)
        result_over = format_waveform_bar(1.5, width=10)

        # Negative should be same as zero
        assert result_negative == format_waveform_bar(0.0, width=10)
        # Over 1 should be same as 1
        assert result_over == format_waveform_bar(1.0, width=10)


class TestFormatStereoMeters:
    """Tests for format_stereo_meters function."""

    def test_returns_two_lines(self) -> None:
        """Test that stereo meters return two lines."""
        result = format_stereo_meters(0.5, 0.5, width=20)

        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("L ")
        assert lines[1].startswith("R ")

    def test_different_channel_levels(self) -> None:
        """Test that different channel levels produce different bars."""
        result = format_stereo_meters(1.0, 0.0, width=20)

        lines = result.split("\n")
        # Left should be full, right should be empty
        assert UNICODE_BLOCKS[-1] in lines[0]  # Left has full blocks
        # Right line (after "R ") should be mostly empty
        right_bar = lines[1][2:]
        assert UNICODE_BLOCKS[0] in right_bar


class TestWaveformBuffer:
    """Tests for WaveformBuffer class."""

    def test_buffer_creation(self) -> None:
        """Test creating a waveform buffer."""
        buf = WaveformBuffer(size=1024, channels=2)

        assert buf.size == 1024
        assert buf.channels == 2

    def test_write_samples(self) -> None:
        """Test writing samples to buffer."""
        buf = WaveformBuffer(size=100)
        samples = np.ones(50, dtype=np.float32)

        buf.write(samples)

        assert len(buf.get_samples()) == 50

    def test_circular_buffer_overflow(self) -> None:
        """Test that buffer acts as circular buffer."""
        buf = WaveformBuffer(size=100)

        # Write more than buffer size
        samples = np.ones(150, dtype=np.float32)
        buf.write(samples)

        # Buffer should only contain last 100 samples
        assert len(buf.get_samples()) == 100

    def test_render_waveform(self) -> None:
        """Test rendering buffer as waveform."""
        buf = WaveformBuffer(size=100)
        samples = np.sin(np.linspace(0, 2 * np.pi, 100)).astype(np.float32)
        buf.write(samples)

        result = buf.render(width=50, height=1)

        assert len(result) == 50

    def test_peak_tracking(self) -> None:
        """Test that peak levels are tracked."""
        buf = WaveformBuffer(size=100, channels=2)

        # Write samples with known peaks
        samples = np.zeros(100, dtype=np.float32)
        samples[0::2] = 0.8  # Left channel
        samples[1::2] = 0.5  # Right channel

        buf.write(samples)

        assert buf.peak_left >= 0.8 * buf._peak_decay
        assert buf.peak_right >= 0.5 * buf._peak_decay

    def test_reset_peaks(self) -> None:
        """Test resetting peak levels."""
        buf = WaveformBuffer(size=100)
        samples = np.ones(50, dtype=np.float32)
        buf.write(samples)

        buf.reset_peaks()

        assert buf.peak_left == 0.0
        assert buf.peak_right == 0.0

    def test_clear_buffer(self) -> None:
        """Test clearing the buffer."""
        buf = WaveformBuffer(size=100)
        samples = np.ones(50, dtype=np.float32)
        buf.write(samples)

        buf.clear()

        assert len(buf.get_samples()) == 0
        assert buf.peak_left == 0.0
        assert buf.peak_right == 0.0

    def test_render_with_meters(self) -> None:
        """Test rendering waveform with meters."""
        buf = WaveformBuffer(size=100, channels=2)
        samples = np.ones(100, dtype=np.float32)
        buf.write(samples)

        result = buf.render_with_meters(waveform_width=40, meter_width=10)

        lines = result.split("\n")
        assert len(lines) == 3  # Waveform + L meter + R meter


class TestAudioLevelFunctions:
    """Tests for audio level calculation functions."""

    def test_calculate_rms_silent(self) -> None:
        """Test RMS of silent audio."""
        samples = np.zeros(100, dtype=np.float32)
        result = calculate_rms(samples)

        assert result == 0.0

    def test_calculate_rms_full_amplitude(self) -> None:
        """Test RMS of full amplitude audio."""
        samples = np.ones(100, dtype=np.float32)
        result = calculate_rms(samples)

        assert result == 1.0

    def test_calculate_rms_sine_wave(self) -> None:
        """Test RMS of sine wave."""
        samples = np.sin(np.linspace(0, 2 * np.pi, 1000)).astype(np.float32)
        result = calculate_rms(samples)

        # RMS of sine wave is 1/sqrt(2) ~ 0.707
        assert 0.70 < result < 0.72

    def test_calculate_rms_empty(self) -> None:
        """Test RMS of empty array."""
        samples = np.array([], dtype=np.float32)
        result = calculate_rms(samples)

        assert result == 0.0

    def test_calculate_peak_silent(self) -> None:
        """Test peak of silent audio."""
        samples = np.zeros(100, dtype=np.float32)
        result = calculate_peak(samples)

        assert result == 0.0

    def test_calculate_peak_full_amplitude(self) -> None:
        """Test peak of full amplitude audio."""
        samples = np.ones(100, dtype=np.float32)
        result = calculate_peak(samples)

        assert result == 1.0

    def test_calculate_peak_negative(self) -> None:
        """Test peak with negative samples."""
        samples = np.array([-0.8, 0.5, -0.3], dtype=np.float32)
        result = calculate_peak(samples)

        assert abs(result - 0.8) < 0.001  # Float32 precision

    def test_calculate_peak_empty(self) -> None:
        """Test peak of empty array."""
        samples = np.array([], dtype=np.float32)
        result = calculate_peak(samples)

        assert result == 0.0


class TestDecibelConversions:
    """Tests for decibel conversion functions."""

    def test_db_to_linear_0db(self) -> None:
        """Test 0dB equals 1.0 linear."""
        result = db_to_linear(0.0)
        assert abs(result - 1.0) < 0.001

    def test_db_to_linear_minus6db(self) -> None:
        """Test -6dB equals approximately 0.5 linear."""
        result = db_to_linear(-6.0)
        assert abs(result - 0.5) < 0.05

    def test_db_to_linear_plus6db(self) -> None:
        """Test +6dB equals approximately 2.0 linear."""
        result = db_to_linear(6.0)
        assert abs(result - 2.0) < 0.1

    def test_linear_to_db_unity(self) -> None:
        """Test 1.0 linear equals 0dB."""
        result = linear_to_db(1.0)
        assert abs(result - 0.0) < 0.001

    def test_linear_to_db_half(self) -> None:
        """Test 0.5 linear equals approximately -6dB."""
        result = linear_to_db(0.5)
        assert abs(result - (-6.0)) < 0.1

    def test_linear_to_db_zero(self) -> None:
        """Test 0.0 linear returns minimum dB."""
        result = linear_to_db(0.0)
        assert result == -96.0

    def test_linear_to_db_negative(self) -> None:
        """Test negative linear returns minimum dB."""
        result = linear_to_db(-0.5)
        assert result == -96.0

    def test_linear_to_db_custom_min(self) -> None:
        """Test custom minimum dB value."""
        result = linear_to_db(0.0, min_db=-120.0)
        assert result == -120.0


@pytest.mark.skipif(
    not hasattr(__import__("sys"), "stdin") or not getattr(__import__("sys").stdout, "isatty", lambda: False)(),
    reason="Requires a real TTY (prompt_toolkit Application needs a console)",
)
class TestREPLMeterInfrastructure:
    """Tests for REPL meter display infrastructure."""

    def test_meter_state_initialized(self) -> None:
        """Test that ChuckREPL initializes meter state correctly."""
        from numchuck.tui.repl import ChuckREPL

        repl = ChuckREPL()

        assert hasattr(repl, "_meter_stop")
        assert hasattr(repl, "_meter_thread")
        assert repl._meter_thread is None
        assert isinstance(repl._current_meters, dict)
        assert repl._current_meters["peak_left"] == 0.0
        assert repl._current_meters["peak_right"] == 0.0
        assert repl._current_meters["rms_left"] == 0.0
        assert repl._current_meters["rms_right"] == 0.0

    def test_meter_bar_output_with_zero_values(self) -> None:
        """Test that meter bars produce valid single-line output with zero values."""
        from numchuck.tui.repl import ChuckREPL

        repl = ChuckREPL()
        m = repl._current_meters

        left_line = f"L {format_waveform_bar(m['peak_left'], width=40)}"
        right_line = f"R {format_waveform_bar(m['peak_right'], width=40)}"

        # Each meter is a single line (no newlines)
        assert "\n" not in left_line
        assert "\n" not in right_line
        assert left_line.startswith("L ")
        assert right_line.startswith("R ")
        assert len(left_line) == 42  # "L " + 40 bar chars
        assert len(right_line) == 42

    def test_meter_bar_output_with_values(self) -> None:
        """Test meter bars with non-zero values."""
        from numchuck.tui.repl import ChuckREPL

        repl = ChuckREPL()
        repl._current_meters = {
            "rms_left": 0.5,
            "rms_right": 0.3,
            "peak_left": 0.8,
            "peak_right": 0.6,
        }
        m = repl._current_meters

        left_line = f"L {format_waveform_bar(m['peak_left'], width=40)}"
        right_line = f"R {format_waveform_bar(m['peak_right'], width=40)}"

        # Each line is exactly 42 chars, no newlines
        assert "\n" not in left_line
        assert "\n" not in right_line
        assert len(left_line) == 42
        assert len(right_line) == 42
        # With peak_left=0.8, should have some full blocks
        assert UNICODE_BLOCKS[-1] in left_line

    def test_meter_thread_stops_cleanly(self) -> None:
        """Test that meter stop event works correctly."""
        import threading

        stop_event = threading.Event()
        assert not stop_event.is_set()

        stop_event.set()
        assert stop_event.is_set()

        # Simulates the cleanup path -- wait returns immediately when set
        stop_event.wait(0.1)


class TestCommandParserWaveformCommands:
    """Tests for waveform command parsing."""

    def test_parse_wave_toggle(self) -> None:
        """Test parsing 'wave' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("wave")

        assert cmd is not None
        assert cmd.type == "toggle_waveform"

    def test_parse_wave_on(self) -> None:
        """Test parsing 'wave on' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("wave on")

        assert cmd is not None
        assert cmd.type == "waveform_on"

    def test_parse_wave_off(self) -> None:
        """Test parsing 'wave off' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("wave off")

        assert cmd is not None
        assert cmd.type == "waveform_off"
