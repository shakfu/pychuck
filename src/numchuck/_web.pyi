"""Type stubs for numchuck web module."""

from typing import Callable

class WebServer:
    """Low-level web server binding for ChucK web IDE."""

    def __init__(self) -> None: ...
    @property
    def port(self) -> int:
        """Server port (default: 8080)."""
        ...

    @port.setter
    def port(self, value: int) -> None: ...
    @property
    def host(self) -> str:
        """Listen address (default: 127.0.0.1)."""
        ...

    @host.setter
    def host(self, value: str) -> None: ...
    @property
    def auth_token(self) -> str:
        """Bearer token required on /api/ and /ws (empty disables auth)."""
        ...

    @auth_token.setter
    def auth_token(self, value: str) -> None: ...
    @property
    def static_dir(self) -> str:
        """Directory for static files."""
        ...

    @static_dir.setter
    def static_dir(self, value: str) -> None: ...
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        ...

    @property
    def client_count(self) -> int:
        """Number of connected WebSocket clients."""
        ...

    def set_api_handler(
        self, handler: Callable[[str, str, str], tuple[int, str]]
    ) -> None:
        """Set the API request handler callback.

        Args:
            handler: Callback function(method, uri, body) -> (status, body)
        """
        ...

    def broadcast(self, message: str) -> None:
        """Broadcast message to all WebSocket clients.

        Args:
            message: Message string to broadcast
        """
        ...

    def start(self) -> bool:
        """Start the web server in background thread.

        Returns:
            True if server started successfully
        """
        ...

    def stop(self) -> None:
        """Stop the web server."""
        ...
