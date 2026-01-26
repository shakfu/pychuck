"""
Waveform visualization for numchuck.

Provides ASCII/Unicode waveform rendering for audio visualization.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


# Unicode block characters for vertical bars (from empty to full)
# These create smooth-looking waveforms
UNICODE_BLOCKS = " \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

# ASCII fallback characters
ASCII_BLOCKS = " ._-=+#@"


def samples_to_waveform(
    samples: NDArray[np.float32],
    width: int = 80,
    height: int = 8,
    use_unicode: bool = True,
) -> str:
    """Convert audio samples to an ASCII/Unicode waveform visualization.

    Args:
        samples: Audio samples as float32 array (mono or interleaved stereo)
        width: Width of output in characters
        height: Height of output in lines (for multi-line display)
        use_unicode: If True, use Unicode block characters; if False, use ASCII

    Returns:
        String representation of waveform

    Example:
        >>> import numpy as np
        >>> samples = np.sin(np.linspace(0, 4*np.pi, 160)).astype(np.float32)
        >>> print(samples_to_waveform(samples, width=40, height=1))
    """
    blocks = UNICODE_BLOCKS if use_unicode else ASCII_BLOCKS
    num_levels = len(blocks) - 1

    if len(samples) == 0:
        return blocks[0] * width

    # Convert stereo to mono by taking every other sample (left channel)
    # or averaging if needed
    if len(samples) > width * 2:
        # Downsample by taking max absolute value in each chunk
        chunk_size = len(samples) // width
        if chunk_size < 1:
            chunk_size = 1

        downsampled = []
        for i in range(width):
            start = i * chunk_size
            end = min(start + chunk_size, len(samples))
            chunk = samples[start:end]
            if len(chunk) > 0:
                # Take peak value (preserves waveform shape better)
                downsampled.append(np.max(np.abs(chunk)))
            else:
                downsampled.append(0.0)
        values = np.array(downsampled, dtype=np.float32)
    else:
        # Use samples directly
        values = np.abs(samples[:width]).astype(np.float32)
        # Pad if needed
        if len(values) < width:
            values = np.pad(values, (0, width - len(values)))

    if height == 1:
        # Single-line waveform
        # Map values [0, 1] to block indices
        indices = np.clip(values * num_levels, 0, num_levels).astype(int)
        return "".join(blocks[i] for i in indices)
    else:
        # Multi-line waveform (centered, showing positive and negative)
        # For multi-line, we show centered waveform with +/- amplitude
        lines = []
        half_height = height // 2

        for row in range(height):
            line = []
            # Row 0 is top (positive), row height-1 is bottom (negative)
            # Center is at half_height
            for col in range(width):
                val = values[col] if col < len(values) else 0.0
                # Map value to height (0-1 maps to 0-half_height rows from center)
                amplitude_rows = int(val * half_height)

                if row < half_height:
                    # Upper half (positive)
                    dist_from_center = half_height - row - 1
                    if dist_from_center < amplitude_rows:
                        line.append(blocks[-1])  # Full block
                    else:
                        line.append(blocks[0])  # Empty
                else:
                    # Lower half (negative) - mirror
                    dist_from_center = row - half_height
                    if dist_from_center < amplitude_rows:
                        line.append(blocks[-1])
                    else:
                        line.append(blocks[0])

            lines.append("".join(line))

        return "\n".join(lines)


def format_waveform_bar(
    value: float,
    width: int = 20,
    use_unicode: bool = True,
) -> str:
    """Create a horizontal bar representing a single value.

    Args:
        value: Value between 0 and 1
        width: Width of the bar in characters
        use_unicode: Use Unicode block characters

    Returns:
        String representation of the bar
    """
    blocks = UNICODE_BLOCKS if use_unicode else ASCII_BLOCKS
    num_levels = len(blocks) - 1

    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    partial = (value * width) - filled

    result = blocks[-1] * filled
    if filled < width:
        partial_idx = int(partial * num_levels)
        result += blocks[partial_idx]
        result += blocks[0] * (width - filled - 1)

    return result


def format_stereo_meters(
    left: float,
    right: float,
    width: int = 20,
    use_unicode: bool = True,
) -> str:
    """Create stereo level meters.

    Args:
        left: Left channel level (0-1)
        right: Right channel level (0-1)
        width: Width of each meter

    Returns:
        Two-line string with L and R meters
    """
    left_bar = format_waveform_bar(left, width, use_unicode)
    right_bar = format_waveform_bar(right, width, use_unicode)
    return f"L {left_bar}\nR {right_bar}"


@dataclass
class WaveformBuffer:
    """Circular buffer for real-time waveform display.

    Stores recent audio samples for continuous visualization.

    Args:
        size: Buffer size in samples
        channels: Number of audio channels

    Example:
        >>> buf = WaveformBuffer(size=1024)
        >>> buf.write(audio_samples)
        >>> waveform = buf.render(width=80)
    """

    size: int = 4096
    channels: int = 2
    _buffer: deque = field(default_factory=deque, repr=False)
    _peak_left: float = field(default=0.0, repr=False)
    _peak_right: float = field(default=0.0, repr=False)
    _peak_decay: float = field(default=0.95, repr=False)

    def __post_init__(self) -> None:
        """Initialize the buffer."""
        self._buffer = deque(maxlen=self.size)

    def write(self, samples: NDArray[np.float32]) -> None:
        """Write samples to the buffer.

        Args:
            samples: Audio samples (interleaved if stereo)
        """
        # Add samples to circular buffer
        for s in samples:
            self._buffer.append(s)

        # Update peak levels
        if len(samples) > 0:
            if self.channels == 2:
                # Stereo: separate left and right
                left = samples[0::2]
                right = samples[1::2]
                if len(left) > 0:
                    current_peak_left = float(np.max(np.abs(left)))
                    self._peak_left = max(
                        current_peak_left, self._peak_left * self._peak_decay
                    )
                if len(right) > 0:
                    current_peak_right = float(np.max(np.abs(right)))
                    self._peak_right = max(
                        current_peak_right, self._peak_right * self._peak_decay
                    )
            else:
                # Mono
                current_peak = float(np.max(np.abs(samples)))
                self._peak_left = max(current_peak, self._peak_left * self._peak_decay)
                self._peak_right = self._peak_left

    def get_samples(self) -> NDArray[np.float32]:
        """Get all samples in the buffer.

        Returns:
            Numpy array of samples
        """
        return np.array(list(self._buffer), dtype=np.float32)

    def render(
        self,
        width: int = 80,
        height: int = 1,
        use_unicode: bool = True,
    ) -> str:
        """Render the buffer contents as a waveform.

        Args:
            width: Width in characters
            height: Height in lines
            use_unicode: Use Unicode characters

        Returns:
            Waveform string
        """
        samples = self.get_samples()
        return samples_to_waveform(samples, width, height, use_unicode)

    def render_with_meters(
        self,
        waveform_width: int = 60,
        meter_width: int = 15,
        use_unicode: bool = True,
    ) -> str:
        """Render waveform with stereo level meters.

        Args:
            waveform_width: Width of waveform display
            meter_width: Width of level meters

        Returns:
            Combined display string
        """
        waveform = self.render(waveform_width, 1, use_unicode)
        meters = format_stereo_meters(
            self._peak_left, self._peak_right, meter_width, use_unicode
        )
        return f"{waveform}\n{meters}"

    @property
    def peak_left(self) -> float:
        """Get current left channel peak level."""
        return self._peak_left

    @property
    def peak_right(self) -> float:
        """Get current right channel peak level."""
        return self._peak_right

    def reset_peaks(self) -> None:
        """Reset peak levels to zero."""
        self._peak_left = 0.0
        self._peak_right = 0.0

    def clear(self) -> None:
        """Clear the buffer."""
        self._buffer.clear()
        self.reset_peaks()


def calculate_rms(samples: NDArray[np.float32]) -> float:
    """Calculate RMS (root mean square) level of samples.

    Args:
        samples: Audio samples

    Returns:
        RMS level (0.0 to 1.0 for normalized audio)
    """
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples**2)))


def calculate_peak(samples: NDArray[np.float32]) -> float:
    """Calculate peak level of samples.

    Args:
        samples: Audio samples

    Returns:
        Peak level (0.0 to 1.0 for normalized audio)
    """
    if len(samples) == 0:
        return 0.0
    return float(np.max(np.abs(samples)))


def db_to_linear(db: float) -> float:
    """Convert decibels to linear amplitude.

    Args:
        db: Level in decibels

    Returns:
        Linear amplitude
    """
    return 10 ** (db / 20)


def linear_to_db(linear: float, min_db: float = -96.0) -> float:
    """Convert linear amplitude to decibels.

    Args:
        linear: Linear amplitude
        min_db: Minimum dB value to return (for zero/near-zero inputs)

    Returns:
        Level in decibels
    """
    if linear <= 0:
        return min_db
    db = 20 * math.log10(linear)
    return max(db, min_db)
