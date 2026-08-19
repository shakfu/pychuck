"""
Audio rendering for numchuck.

Provides offline rendering of ChucK code to numpy arrays or WAV files.
"""

from __future__ import annotations

import wave
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray


class RenderError(Exception):
    """Error during audio rendering."""


def render(
    code: str,
    duration: float = 10.0,
    sample_rate: int = 44100,
    channels: int = 2,
    dtype: type = np.float32,
) -> "NDArray[np.float32] | NDArray[np.int16]":
    """Render ChucK code to a numpy array.

    Args:
        code: ChucK source code string
        duration: Duration in seconds to render (default: 10.0)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of output channels (default: 2)
        dtype: Output dtype (default: np.float32, can be np.int16)

    Returns:
        Numpy array with interleaved audio data. For stereo: [L0, R0, L1, R1, ...].
        Access as memoryview via array.data or memoryview(array).

    Raises:
        RenderError: If compilation fails

    Example:
        >>> audio = render("SinOsc s => dac; 1::second => now;", duration=1.0)
        >>> len(audio)
        88200
    """
    from .api import Chuck

    chuck = Chuck(
        sample_rate=sample_rate,
        output_channels=channels,
        input_channels=0,
    )

    success, shred_ids = chuck.compile(code)
    if not success:
        chuck.close()
        raise RenderError("Failed to compile code")

    if not shred_ids:
        chuck.close()
        raise RenderError("No shreds were created from the code")

    total_frames = int(duration * sample_rate)
    output = chuck.run(total_frames)
    chuck.close()

    if dtype == np.int16:
        clipped = np.clip(output, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16)

    return output


def render_file(
    files: Sequence[str | Path] | str | Path,
    duration: float = 10.0,
    sample_rate: int = 44100,
    channels: int = 2,
    dtype: type = np.float32,
) -> "NDArray[np.float32] | NDArray[np.int16]":
    """Render ChucK files to a numpy array.

    Args:
        files: ChucK file path or list of paths
        duration: Duration in seconds to render (default: 10.0)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of output channels (default: 2)
        dtype: Output dtype (default: np.float32, can be np.int16)

    Returns:
        Numpy array with interleaved audio data.

    Raises:
        RenderError: If compilation fails or no files provided
        FileNotFoundError: If a ChucK file doesn't exist

    Example:
        >>> audio = render_file("sine.ck", duration=1.0)
        >>> audio = render_file(["osc1.ck", "osc2.ck"], duration=2.0)
    """
    from .api import Chuck

    # Normalize to list
    if isinstance(files, (str, Path)):
        files = [files]

    if not files:
        raise RenderError("No ChucK files provided")

    for f in files:
        path = Path(f)
        if not path.exists():
            raise FileNotFoundError(f"ChucK file not found: {path}")

    chuck = Chuck(
        sample_rate=sample_rate,
        output_channels=channels,
        input_channels=0,
    )

    compiled_any = False
    for f in files:
        path = Path(f)
        success, shred_ids = chuck.compile_file(str(path.absolute()))
        if not success:
            chuck.close()
            raise RenderError(f"Failed to compile: {path}")
        if shred_ids:
            compiled_any = True

    if not compiled_any:
        chuck.close()
        raise RenderError("No shreds were created from the provided files")

    total_frames = int(duration * sample_rate)
    output = chuck.run(total_frames)
    chuck.close()

    if dtype == np.int16:
        clipped = np.clip(output, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16)

    return output


def to_wav(
    output: str | Path,
    code: str | None = None,
    files: Sequence[str | Path] | str | Path | None = None,
    duration: float = 10.0,
    sample_rate: int = 44100,
    channels: int = 2,
    chunk_size: int = 4096,
) -> Path:
    """Render ChucK code or files to a WAV file.

    Provide either code or files, not both.

    Args:
        output: Path to output WAV file
        code: ChucK source code string (mutually exclusive with files)
        files: ChucK file path(s) (mutually exclusive with code)
        duration: Duration in seconds to render (default: 10.0)
        sample_rate: Sample rate in Hz (default: 44100)
        channels: Number of output channels (default: 2)
        chunk_size: Frames per chunk for rendering (default: 4096)

    Returns:
        Path to the created WAV file

    Raises:
        RenderError: If compilation fails
        ValueError: If neither code nor files provided, or both provided
        FileNotFoundError: If a ChucK file doesn't exist

    Example:
        >>> to_wav("output.wav", code="SinOsc s => dac; 1::second => now;")
        >>> to_wav("output.wav", files=["sine.ck"], duration=5.0)
    """
    from .api import Chuck

    output_path = Path(output)

    if code is None and files is None:
        raise ValueError("Must provide either code or files")
    if code is not None and files is not None:
        raise ValueError("Cannot provide both code and files")

    # Normalize files to list
    if files is not None:
        if isinstance(files, (str, Path)):
            files = [files]
        if not files:
            raise RenderError("No ChucK files provided")
        for f in files:
            path = Path(f)
            if not path.exists():
                raise FileNotFoundError(f"ChucK file not found: {path}")

    chuck = Chuck(
        sample_rate=sample_rate,
        output_channels=channels,
        input_channels=0,
    )

    # Compile
    if code is not None:
        success, shred_ids = chuck.compile(code)
        if not success:
            chuck.close()
            raise RenderError("Failed to compile code")
        if not shred_ids:
            chuck.close()
            raise RenderError("No shreds were created from the code")
    else:
        assert files is not None  # Type narrowing: we checked above
        compiled_any = False
        for f in files:
            path = Path(f)
            success, shred_ids = chuck.compile_file(str(path.absolute()))
            if not success:
                chuck.close()
                raise RenderError(f"Failed to compile: {path}")
            if shred_ids:
                compiled_any = True
        if not compiled_any:
            chuck.close()
            raise RenderError("No shreds were created from the provided files")

    total_frames = int(duration * sample_rate)

    # Open WAV file for writing
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Render in chunks to avoid memory issues
        frames_rendered = 0
        while frames_rendered < total_frames:
            remaining = total_frames - frames_rendered
            current_chunk = min(chunk_size, remaining)

            output_buf = chuck.run(current_chunk)

            clipped = np.clip(output_buf, -1.0, 1.0)
            int16_data = (clipped * 32767).astype(np.int16)

            wav_file.writeframes(int16_data.tobytes())

            frames_rendered += current_chunk

    chuck.close()

    return output_path
