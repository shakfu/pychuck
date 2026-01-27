"""
Audio lifecycle management service.

Provides consistent audio start/stop/shutdown operations with proper
error handling and state tracking. Used by both CLI and TUI components.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Protocol

from .._numchuck import start_audio, stop_audio, shutdown_audio

if TYPE_CHECKING:
    from .._numchuck import ChucK


class Logger(Protocol):
    """Protocol for logger interface."""

    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str, exc: Exception | None = None) -> None: ...


class NullLogger:
    """No-op logger for when no logger is provided."""

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str, exc: Exception | None = None) -> None:
        pass


class AudioService:
    """Manages audio lifecycle for ChucK instances.

    Provides consistent start/stop/shutdown operations with proper
    error handling and state tracking.

    Usage:
        audio = AudioService(chuck)
        if audio.start():
            # Audio is running
            pass
        audio.stop()
    """

    def __init__(
        self,
        chuck: ChucK,
        logger: Logger | None = None,
        shutdown_timeout_ms: int = 500,
    ) -> None:
        """Initialize AudioService.

        Args:
            chuck: ChucK instance to manage
            logger: Optional logger for messages
            shutdown_timeout_ms: Timeout in milliseconds for shutdown (default 500)
        """
        self._chuck = chuck
        self._running = False
        self._logger: Logger = logger or NullLogger()
        self._shutdown_timeout_ms = shutdown_timeout_ms
        self._on_start: Callable[[], None] | None = None
        self._on_stop: Callable[[], None] | None = None

    @property
    def is_running(self) -> bool:
        """Check if audio is currently running."""
        return self._running

    @property
    def chuck(self) -> ChucK:
        """Get the managed ChucK instance."""
        return self._chuck

    def set_callbacks(
        self,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
    ) -> None:
        """Set optional callbacks for audio state changes.

        Args:
            on_start: Called after audio starts successfully
            on_stop: Called after audio stops
        """
        self._on_start = on_start
        self._on_stop = on_stop

    def start(self) -> bool:
        """Start real-time audio playback.

        Returns:
            True if audio started successfully, False otherwise
        """
        if self._running:
            self._logger.debug("Audio already running")
            return True

        try:
            start_audio(self._chuck)
            self._running = True
            self._logger.info("Audio started")
            if self._on_start:
                self._on_start()
            return True
        except Exception as e:
            self._logger.error("Could not start audio", exc=e)
            return False

    def stop(self) -> bool:
        """Stop real-time audio playback.

        Returns:
            True if stopped successfully, False if error occurred
        """
        if not self._running:
            self._logger.debug("Audio not running")
            return True

        success = True

        try:
            stop_audio()
            self._logger.debug("Audio stopped")
        except (RuntimeError, OSError) as e:
            self._logger.error("Error stopping audio", exc=e)
            success = False

        try:
            shutdown_audio(self._shutdown_timeout_ms)
            self._logger.debug("Audio shutdown complete")
        except (RuntimeError, OSError) as e:
            self._logger.error("Error shutting down audio", exc=e)
            success = False

        self._running = False
        if self._on_stop:
            self._on_stop()
        return success

    def shutdown(self, timeout_ms: int | None = None) -> bool:
        """Shutdown audio system.

        This performs stop + shutdown in one call. Use this for cleanup.

        Args:
            timeout_ms: Override shutdown timeout (uses default if None)

        Returns:
            True if shutdown successful
        """
        timeout = timeout_ms if timeout_ms is not None else self._shutdown_timeout_ms
        success = True

        if self._running:
            try:
                stop_audio()
            except (RuntimeError, OSError) as e:
                self._logger.error("Error stopping audio", exc=e)
                success = False

        try:
            shutdown_audio(timeout)
        except (RuntimeError, OSError) as e:
            self._logger.error("Error shutting down audio", exc=e)
            success = False

        self._running = False
        if self._on_stop:
            self._on_stop()
        return success

    def restart(self) -> bool:
        """Restart audio (stop then start).

        Returns:
            True if restart successful
        """
        self.stop()
        return self.start()
