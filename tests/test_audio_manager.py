"""Tests for AudioManager class."""

import pytest

from numchuck._numchuck import ChucK, PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS
from numchuck.tui.common import AudioManager
from numchuck.tui.logging import TUILogger, LogLevel


@pytest.fixture
def initialized_chuck():
    """Create and initialize a ChucK instance."""
    chuck = ChucK()
    chuck.set_param(PARAM_SAMPLE_RATE, 44100)
    chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
    chuck.init()
    yield chuck
    # Cleanup handled by test


class TestAudioManager:
    """Test AudioManager class."""

    def test_init_not_running(self, initialized_chuck):
        """Test AudioManager starts not running."""
        audio = AudioManager(initialized_chuck)
        assert audio.is_running is False

    def test_start_success(self, initialized_chuck):
        """Test successful audio start."""
        audio = AudioManager(initialized_chuck)

        # Start audio
        result = audio.start()

        try:
            # Should succeed
            assert result is True
            assert audio.is_running is True
        finally:
            # Cleanup
            audio.stop()

    def test_start_already_running(self, initialized_chuck):
        """Test start when already running returns True."""
        audio = AudioManager(initialized_chuck)

        try:
            audio.start()
            # Second start should also return True
            result = audio.start()
            assert result is True
            assert audio.is_running is True
        finally:
            audio.stop()

    def test_stop_success(self, initialized_chuck):
        """Test successful audio stop."""
        audio = AudioManager(initialized_chuck)

        try:
            audio.start()
            assert audio.is_running is True

            result = audio.stop()
            assert result is True
            assert audio.is_running is False
        finally:
            # Ensure cleanup
            if audio.is_running:
                audio.stop()

    def test_stop_not_running(self, initialized_chuck):
        """Test stop when not running returns True."""
        audio = AudioManager(initialized_chuck)

        # Stop without starting should be OK
        result = audio.stop()
        assert result is True
        assert audio.is_running is False

    def test_restart(self, initialized_chuck):
        """Test audio restart."""
        audio = AudioManager(initialized_chuck)

        try:
            audio.start()
            assert audio.is_running is True

            # Restart
            result = audio.restart()
            assert result is True
            assert audio.is_running is True
        finally:
            audio.stop()

    def test_custom_logger(self, initialized_chuck):
        """Test AudioManager uses custom logger."""
        messages = []
        logger = TUILogger(level=LogLevel.DEBUG)
        logger.set_callback(lambda msg, lvl: messages.append(msg))

        audio = AudioManager(initialized_chuck, logger=logger)

        try:
            audio.start()
            audio.stop()
        finally:
            if audio.is_running:
                audio.stop()

        # Should have logged start and stop (or error if audio not available)
        assert len(messages) > 0  # At least some log output

    def test_is_running_property(self, initialized_chuck):
        """Test is_running property reflects state correctly."""
        audio = AudioManager(initialized_chuck)

        assert audio.is_running is False

        try:
            audio.start()
            assert audio.is_running is True

            audio.stop()
            assert audio.is_running is False
        finally:
            if audio.is_running:
                audio.stop()
