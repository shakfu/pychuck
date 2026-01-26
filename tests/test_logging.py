"""Tests for TUI logging module."""

import io
import pytest

from numchuck.tui.logging import (
    TUILogger,
    LogLevel,
    get_logger,
    set_logger,
    debug,
    info,
    warning,
    error,
)


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_levels_ordered(self):
        """Test that log levels are properly ordered."""
        assert LogLevel.DEBUG < LogLevel.INFO < LogLevel.WARNING < LogLevel.ERROR

    def test_log_level_values(self):
        """Test log level numeric values."""
        assert LogLevel.DEBUG == 10
        assert LogLevel.INFO == 20
        assert LogLevel.WARNING == 30
        assert LogLevel.ERROR == 40


class TestTUILogger:
    """Test TUILogger class."""

    def test_default_level(self):
        """Test default log level is INFO."""
        logger = TUILogger()
        assert logger.level == LogLevel.INFO

    def test_set_level(self):
        """Test setting log level."""
        logger = TUILogger(level=LogLevel.DEBUG)
        assert logger.level == LogLevel.DEBUG

        logger.level = LogLevel.ERROR
        assert logger.level == LogLevel.ERROR

    def test_log_filtering(self):
        """Test that messages below level are filtered."""
        messages = []
        logger = TUILogger(level=LogLevel.WARNING)
        logger.set_callback(lambda msg, lvl: messages.append((msg, lvl)))

        logger.debug("debug msg")
        logger.info("info msg")
        logger.warning("warning msg")
        logger.error("error msg")

        assert len(messages) == 2
        assert "WARN" in messages[0][0]
        assert "ERROR" in messages[1][0]

    def test_log_callback(self):
        """Test callback is called with message."""
        messages = []
        logger = TUILogger()
        logger.set_callback(lambda msg, lvl: messages.append(msg))

        logger.info("test message")

        assert len(messages) == 1
        assert "test message" in messages[0]

    def test_log_to_stream(self):
        """Test logging to stream."""
        stream = io.StringIO()
        logger = TUILogger(stream=stream)

        logger.info("stream test")

        output = stream.getvalue()
        assert "stream test" in output
        assert "INFO" in output

    def test_timestamps_enabled(self):
        """Test timestamps in log messages."""
        messages = []
        logger = TUILogger(timestamps=True)
        logger.set_callback(lambda msg, lvl: messages.append(msg))

        logger.info("timestamp test")

        # Should have time pattern like [HH:MM:SS]
        assert "[" in messages[0] and ":" in messages[0]

    def test_timestamps_disabled(self):
        """Test no timestamps by default."""
        messages = []
        logger = TUILogger(timestamps=False)
        logger.set_callback(lambda msg, lvl: messages.append(msg))

        logger.info("no timestamp")

        # Format should be [INFO] message
        assert messages[0].startswith("[INFO]")

    def test_error_with_exception(self):
        """Test error logging with exception."""
        messages = []
        logger = TUILogger()
        logger.set_callback(lambda msg, lvl: messages.append(msg))

        try:
            raise ValueError("test error")
        except ValueError as e:
            logger.error("operation failed", exc=e)

        assert len(messages) == 1
        assert "operation failed" in messages[0]
        assert "test error" in messages[0]

    def test_get_messages(self):
        """Test retrieving stored messages."""
        logger = TUILogger()
        logger.info("msg1")
        logger.warning("msg2")
        logger.error("msg3")

        all_msgs = logger.get_messages()
        assert len(all_msgs) == 3

        error_msgs = logger.get_messages(level=LogLevel.ERROR)
        assert len(error_msgs) == 1

    def test_clear_messages(self):
        """Test clearing stored messages."""
        logger = TUILogger()
        logger.info("test")
        assert len(logger.get_messages()) == 1

        logger.clear()
        assert len(logger.get_messages()) == 0


class TestGlobalLogger:
    """Test global logger functions."""

    def test_get_logger_singleton(self):
        """Test that get_logger returns same instance."""
        logger1 = get_logger()
        logger2 = get_logger()
        assert logger1 is logger2

    def test_set_logger(self):
        """Test setting global logger."""
        original = get_logger()
        new_logger = TUILogger(level=LogLevel.DEBUG)

        set_logger(new_logger)
        assert get_logger() is new_logger

        # Restore original
        set_logger(original)

    def test_convenience_functions(self):
        """Test module-level logging functions."""
        messages = []
        logger = TUILogger(level=LogLevel.DEBUG)
        logger.set_callback(lambda msg, lvl: messages.append((msg, lvl)))
        set_logger(logger)

        debug("debug test")
        info("info test")
        warning("warning test")
        error("error test")

        assert len(messages) == 4
        assert any("DEBUG" in msg for msg, _ in messages)
        assert any("INFO" in msg for msg, _ in messages)
        assert any("WARN" in msg for msg, _ in messages)
        assert any("ERROR" in msg for msg, _ in messages)
