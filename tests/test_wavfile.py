"""Tests for WAV file rendering using ChucK's native WvOut."""

import os
import tempfile
from pathlib import Path

import pytest

from numchuck import Chuck


def normalize_path(path: str) -> str:
    """Normalize path for ChucK (use forward slashes on all platforms)."""
    # ChucK expects forward slashes and can't handle Windows backslashes
    return str(Path(path).resolve()).replace('\\', '/')


class TestWvOut:
    """Test ChucK's native WvOut for WAV file writing."""

    def test_render_sine_to_wav(self):
        """Test rendering a sine wave to a WAV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Normalize path for Windows compatibility (ChucK needs forward slashes)
            output_path = normalize_path(os.path.join(tmpdir, "sine_output.wav"))

            chuck = Chuck(sample_rate=44100, output_channels=2)

            # ChucK code that records to WAV using WvOut
            # WvOut records automatically when samples flow through
            code = f'''
            // Connect an audio stream to WvOut
            SinOsc s1 => WvOut w => blackhole;

            // Set the output file path
            "{output_path}" => w.wavFilename;

            1 => w.record; // Start recording

            // Run your main logic
            4::second => now;

            0 => w.record; // Stop recording
            w.closeFile(); // Close the file
            '''

            success, shred_ids = chuck.compile(code)
            assert success, "Failed to compile WvOut code"
            assert len(shred_ids) == 1

            # Run for 4 seconds of audio (must match the ChucK code duration)
            chuck.run(44100 * 4)

            # Clean up Chuck to release file handles (required on Windows)
            del chuck

            # Verify WAV file was created
            assert os.path.exists(output_path), "WAV file was not created"
            file_size = os.path.getsize(output_path)
            assert file_size > 1000, f"WAV file too small: {file_size} bytes"

    def test_render_stereo_to_wav(self):
        """Test rendering stereo audio to a WAV file using WvOut2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Normalize path for Windows compatibility
            output_path = normalize_path(os.path.join(tmpdir, "stereo_output.wav"))

            chuck = Chuck(sample_rate=44100, output_channels=2)

            # Use WvOut2 for stereo recording
            code = f'''
            // Create stereo signal
            SinOsc left;
            SinOsc right;
            440 => left.freq;
            550 => right.freq;

            // Connect to stereo WvOut2
            left => WvOut2 w => blackhole;
            right => w;

            "{output_path}" => w.wavFilename;

            1 => w.record;
            1::second => now;
            0 => w.record;
            w.closeFile();
            '''

            success, shred_ids = chuck.compile(code)
            assert success, "Failed to compile stereo WvOut2 code"

            chuck.run(44100)

            # Clean up Chuck to release file handles (required on Windows)
            del chuck

            assert os.path.exists(output_path), "Stereo WAV file was not created"
            file_size = os.path.getsize(output_path)
            # Stereo file should be larger
            assert file_size > 2000, f"Stereo WAV file too small: {file_size} bytes"

    def test_me_dir_path(self):
        """Test using me.dir() style path construction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "medir_output.wav")
            # Normalize working directory for Windows compatibility
            working_dir = normalize_path(tmpdir)

            chuck = Chuck(sample_rate=44100, output_channels=2, working_directory=working_dir)

            code = '''
            SinOsc s => WvOut w => blackhole;
            440 => s.freq;

            me.dir() + "/medir_output.wav" => w.wavFilename;

            1 => w.record;
            0.5::second => now;
            0 => w.record;
            w.closeFile();
            '''

            success, shred_ids = chuck.compile(code)
            assert success, "Failed to compile me.dir() code"

            chuck.run(22050)  # 0.5 seconds

            # Clean up Chuck to release file handles (required on Windows)
            del chuck

            assert os.path.exists(output_path), "me.dir() WAV file was not created"
