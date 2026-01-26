"""
Centralized logging for TUI components.

Provides consistent logging with levels, timestamps, and UI integration.
"""

from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Callable, TextIO


class LogLevel(IntEnum):
    """Log levels for filtering output."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


class TUILogger:
    """Centralized logger for TUI components.

    Provides:
    - Log levels (DEBUG, INFO, WARNING, ERROR)
    - Timestamps on messages
    - Callback support for UI integration (log window)
    - Consistent formatting

    Usage:
        logger = TUILogger()
        logger.info("Started audio")
        logger.error("Failed to compile", exc=e)

        # Set callback for UI integration
        logger.set_callback(lambda msg, level: log_area.text += msg)
    """

    def __init__(
        self,
        level: LogLevel = LogLevel.INFO,
        timestamps: bool = False,
        stream: TextIO | None = None,
    ):
        """Initialize the logger.

        Args:
            level: Minimum log level to output
            timestamps: Whether to include timestamps in messages
            stream: Output stream (default: None, only callbacks)
        """
        self._level = level
        self._timestamps = timestamps
        self._stream = stream
        self._callback: Callable[[str, LogLevel], None] | None = None
        self._messages: list[tuple[LogLevel, str]] = []
        self._max_messages = 1000

    @property
    def level(self) -> LogLevel:
        """Get current log level."""
        return self._level

    @level.setter
    def level(self, value: LogLevel) -> None:
        """Set log level."""
        self._level = value

    def set_callback(self, callback: Callable[[str, LogLevel], None] | None) -> None:
        """Set callback for log messages.

        Args:
            callback: Function called with (message, level) for each log entry
        """
        self._callback = callback

    def set_stream(self, stream: TextIO | None) -> None:
        """Set output stream.

        Args:
            stream: Output stream (None to disable stream output)
        """
        self._stream = stream

    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format a log message.

        Args:
            level: Log level
            message: Message text

        Returns:
            Formatted message string
        """
        parts = []

        if self._timestamps:
            timestamp = datetime.now().strftime("%H:%M:%S")
            parts.append(f"[{timestamp}]")

        level_names = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARN",
            LogLevel.ERROR: "ERROR",
        }
        parts.append(f"[{level_names[level]}]")
        parts.append(message)

        return " ".join(parts)

    def _log(self, level: LogLevel, message: str) -> None:
        """Internal logging method.

        Args:
            level: Log level
            message: Message to log
        """
        if level < self._level:
            return

        formatted = self._format_message(level, message)

        # Store message
        self._messages.append((level, formatted))
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages // 2 :]

        # Output to stream
        if self._stream is not None:
            self._stream.write(formatted + "\n")
            self._stream.flush()

        # Call callback
        if self._callback is not None:
            self._callback(formatted, level)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message)

    def warning(self, message: str) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message)

    def error(self, message: str, exc: BaseException | None = None) -> None:
        """Log error message.

        Args:
            message: Error message
            exc: Optional exception to include
        """
        if exc is not None:
            message = f"{message}: {exc}"
        self._log(LogLevel.ERROR, message)

    def get_messages(self, level: LogLevel | None = None) -> list[tuple[LogLevel, str]]:
        """Get stored log messages.

        Args:
            level: Optional filter by minimum level

        Returns:
            List of (level, message) tuples
        """
        if level is None:
            return list(self._messages)
        return [(lvl, msg) for lvl, msg in self._messages if lvl >= level]

    def clear(self) -> None:
        """Clear stored messages."""
        self._messages.clear()


# Global logger instance
_logger: TUILogger | None = None


def get_logger() -> TUILogger:
    """Get the global TUI logger instance.

    Returns:
        The global TUILogger instance
    """
    global _logger
    if _logger is None:
        _logger = TUILogger()
    return _logger


def set_logger(logger: TUILogger) -> None:
    """Set the global TUI logger instance.

    Args:
        logger: TUILogger instance to use globally
    """
    global _logger
    _logger = logger


# Convenience functions using global logger
def debug(message: str) -> None:
    """Log debug message to global logger."""
    get_logger().debug(message)


def info(message: str) -> None:
    """Log info message to global logger."""
    get_logger().info(message)


def warning(message: str) -> None:
    """Log warning message to global logger."""
    get_logger().warning(message)


def error(message: str, exc: BaseException | None = None) -> None:
    """Log error message to global logger."""
    get_logger().error(message, exc)
