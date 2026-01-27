"""
Global variable and event service.

Provides operations for getting/setting global variables and signaling events.
Used by both CLI and TUI components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Protocol, Union

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


@dataclass
class GlobalInfo:
    """Information about a global variable."""

    name: str
    type: str


GlobalValue = Union[int, float, str, list[int], list[float]]


class GlobalsService:
    """Manages global variables and events for ChucK instances.

    Provides operations for getting and setting global variables,
    and signaling/broadcasting events.

    Usage:
        globals = GlobalsService(chuck)
        globals.set_global("myVar", 440)
        value = globals.get_global_int("myVar")
    """

    def __init__(
        self,
        chuck: ChucK,
        logger: Logger | None = None,
    ) -> None:
        """Initialize GlobalsService.

        Args:
            chuck: ChucK instance to manage
            logger: Optional logger for messages
        """
        self._chuck = chuck
        self._logger: Logger = logger or NullLogger()

    @property
    def chuck(self) -> ChucK:
        """Get the managed ChucK instance."""
        return self._chuck

    def set_global(self, name: str, value: GlobalValue) -> bool:
        """Set a global variable.

        Automatically detects the type and calls the appropriate setter.

        Args:
            name: Name of the global variable
            value: Value to set (int, float, str, or list)

        Returns:
            True if set successfully
        """
        try:
            if isinstance(value, int):
                self._chuck.set_global_int(name, value)
            elif isinstance(value, float):
                self._chuck.set_global_float(name, value)
            elif isinstance(value, str):
                self._chuck.set_global_string(name, value)
            elif isinstance(value, list):
                if all(isinstance(x, int) for x in value):
                    int_array: list[int] = [int(x) for x in value]
                    self._chuck.set_global_int_array(name, int_array)
                elif all(isinstance(x, (int, float)) for x in value):
                    # Convert to float array if mixed or all floats
                    float_array: list[float] = [float(x) for x in value]
                    self._chuck.set_global_float_array(name, float_array)
                else:
                    self._logger.error(f"Unsupported array type for {name}")
                    return False
            else:
                self._logger.error(f"Unsupported type for global {name}: {type(value)}")
                return False

            self._logger.debug(f"Set {name} = {value}")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set global '{name}': {e}")
            return False

    def set_global_int(self, name: str, value: int) -> bool:
        """Set an integer global variable.

        Args:
            name: Name of the global variable
            value: Integer value

        Returns:
            True if set successfully
        """
        try:
            self._chuck.set_global_int(name, value)
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set int global '{name}': {e}")
            return False

    def set_global_float(self, name: str, value: float) -> bool:
        """Set a float global variable.

        Args:
            name: Name of the global variable
            value: Float value

        Returns:
            True if set successfully
        """
        try:
            self._chuck.set_global_float(name, value)
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set float global '{name}': {e}")
            return False

    def set_global_string(self, name: str, value: str) -> bool:
        """Set a string global variable.

        Args:
            name: Name of the global variable
            value: String value

        Returns:
            True if set successfully
        """
        try:
            self._chuck.set_global_string(name, value)
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set string global '{name}': {e}")
            return False

    def set_global_int_array(self, name: str, value: list[int]) -> bool:
        """Set an integer array global variable.

        Args:
            name: Name of the global variable
            value: List of integers

        Returns:
            True if set successfully
        """
        try:
            self._chuck.set_global_int_array(name, value)
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set int array global '{name}': {e}")
            return False

    def set_global_float_array(self, name: str, value: list[float]) -> bool:
        """Set a float array global variable.

        Args:
            name: Name of the global variable
            value: List of floats

        Returns:
            True if set successfully
        """
        try:
            self._chuck.set_global_float_array(name, value)
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to set float array global '{name}': {e}")
            return False

    def get_global_int(
        self, name: str, callback: Callable[[int], None] | None = None
    ) -> int | None:
        """Get an integer global variable.

        Args:
            name: Name of the global variable
            callback: Optional callback for the value

        Returns:
            The integer value, or None if not found/wrong type
        """
        result: list[int | None] = [None]

        def capture_callback(v: int) -> None:
            result[0] = v
            if callback:
                callback(v)

        try:
            self._chuck.get_global_int(name, capture_callback)
            return result[0]
        except RuntimeError:
            return None

    def get_global_float(
        self, name: str, callback: Callable[[float], None] | None = None
    ) -> float | None:
        """Get a float global variable.

        Args:
            name: Name of the global variable
            callback: Optional callback for the value

        Returns:
            The float value, or None if not found/wrong type
        """
        result: list[float | None] = [None]

        def capture_callback(v: float) -> None:
            result[0] = v
            if callback:
                callback(v)

        try:
            self._chuck.get_global_float(name, capture_callback)
            return result[0]
        except RuntimeError:
            return None

    def get_global_string(
        self, name: str, callback: Callable[[str], None] | None = None
    ) -> str | None:
        """Get a string global variable.

        Args:
            name: Name of the global variable
            callback: Optional callback for the value

        Returns:
            The string value, or None if not found/wrong type
        """
        result: list[str | None] = [None]

        def capture_callback(v: str) -> None:
            result[0] = v
            if callback:
                callback(v)

        try:
            self._chuck.get_global_string(name, capture_callback)
            return result[0]
        except RuntimeError:
            return None

    def get_global(self, name: str) -> tuple[str, Any] | None:
        """Get a global variable value with its type.

        Tries int, float, then string in order.

        Args:
            name: Name of the global variable

        Returns:
            Tuple of (type_name, value) or None if not found
        """
        # Try int first
        int_val = self.get_global_int(name)
        if int_val is not None:
            return ("int", int_val)

        # Try float
        float_val = self.get_global_float(name)
        if float_val is not None:
            return ("float", float_val)

        # Try string
        str_val = self.get_global_string(name)
        if str_val is not None:
            return ("string", str_val)

        return None

    def list_globals(self) -> list[GlobalInfo]:
        """List all global variables.

        Returns:
            List of GlobalInfo objects
        """
        try:
            globals_list = self._chuck.get_all_globals()
            return [GlobalInfo(name=name, type=typ) for typ, name in globals_list]
        except RuntimeError:
            return []

    def signal_event(self, name: str) -> bool:
        """Signal a global event.

        Args:
            name: Name of the event to signal

        Returns:
            True if signaled successfully
        """
        try:
            self._chuck.signal_global_event(name)
            self._logger.debug(f"Signaled event '{name}'")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to signal event '{name}': {e}")
            return False

    def broadcast_event(self, name: str) -> bool:
        """Broadcast a global event.

        Args:
            name: Name of the event to broadcast

        Returns:
            True if broadcast successfully
        """
        try:
            self._chuck.broadcast_global_event(name)
            self._logger.debug(f"Broadcast event '{name}'")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to broadcast event '{name}': {e}")
            return False
