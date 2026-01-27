"""numchuck web server module.

Provides a browser-based IDE for ChucK live coding.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..constants import DEFAULT_WEB_PORT, MAX_CONSOLE_LINES

if TYPE_CHECKING:
    from ..api import Chuck

# Check if web module is available
try:
    from .._web import WebServer as _WebServer

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False
    _WebServer = None  # type: ignore


class WebChuckServer:
    """High-level web server for browser-based ChucK IDE.

    Provides REST API and WebSocket interface for controlling ChucK
    from a web browser.

    Example:
        >>> from numchuck import Chuck
        >>> from numchuck.web import WebChuckServer
        >>> chuck = Chuck()
        >>> server = WebChuckServer(chuck, port=8080)
        >>> server.start()
        >>> # Browse to http://localhost:8080
        >>> server.stop()
    """

    def __init__(
        self,
        chuck: Chuck,
        port: int = DEFAULT_WEB_PORT,
        static_dir: str | Path | None = None,
    ) -> None:
        """Initialize web server.

        Args:
            chuck: ChucK instance to control
            port: HTTP port to listen on (default: 8080)
            static_dir: Directory for static files (optional, uses embedded UI if None)
        """
        if not WEB_AVAILABLE:
            raise ImportError(
                "Web module not available. "
                "Rebuild numchuck with -DNUMCHUCK_ENABLE_WEB=ON"
            )

        self._chuck = chuck
        self._server = _WebServer()
        self._server.port = port

        if static_dir:
            self._server.static_dir = str(Path(static_dir).resolve())

        # Set up API handler
        self._server.set_api_handler(self._handle_api)

        # Track shred start times for elapsed display
        self._shred_times: dict[int, float] = {}

        # Track shred source code for preview
        self._shred_code: dict[int, str] = {}

        # Console output buffer
        self._console_lines: list[dict[str, str]] = []
        self._max_console_lines = MAX_CONSOLE_LINES

        # Recording state
        self._recording = False
        self._recorded_samples: list[float] = []

        # Set up console capture
        self._setup_console_capture()

    def _setup_console_capture(self) -> None:
        """Set up callbacks to capture ChucK console output."""

        def on_stdout(msg: str) -> None:
            self._log(msg.rstrip(), "info")

        def on_stderr(msg: str) -> None:
            self._log(msg.rstrip(), "error")

        self._chuck.set_stdout_callback(on_stdout)
        self._chuck.set_stderr_callback(on_stderr)

    def _log(self, text: str, level: str = "info") -> None:
        """Log message to console and broadcast to clients."""
        entry = {"type": "console", "text": text, "level": level}
        self._console_lines.append(entry)

        # Trim old entries
        if len(self._console_lines) > self._max_console_lines:
            self._console_lines = self._console_lines[-self._max_console_lines :]

        # Broadcast to WebSocket clients
        if self._server.is_running:
            self._server.broadcast(json.dumps(entry))

    def _handle_api(self, method: str, uri: str, body: str) -> str:
        """Handle API requests from web clients.

        Args:
            method: HTTP method (GET, POST, DELETE, WS)
            uri: Request URI
            body: Request body (JSON string)

        Returns:
            JSON response string
        """
        try:
            # Only parse body for methods that have one
            if body and body.strip() and method in ("POST", "PUT", "PATCH", "WS"):
                data = json.loads(body)
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}

        # Route API requests
        if uri == "/api/status":
            return self._api_status()
        elif uri == "/api/compile" and method == "POST":
            return self._api_compile(data)
        elif uri.startswith("/api/shred/") and method == "DELETE":
            shred_id = int(uri.split("/")[-1])
            return self._api_remove_shred(shred_id)
        elif uri == "/api/clear" and method == "POST":
            return self._api_clear()
        elif uri == "/api/audio/start" and method == "POST":
            return self._api_start_audio()
        elif uri == "/api/audio/stop" and method == "POST":
            return self._api_stop_audio()
        elif uri == "/api/globals" and method == "GET":
            return self._api_list_globals()
        elif uri.startswith("/api/global/") and method == "GET":
            name = uri.split("/")[-1]
            return self._api_get_global(name, data)
        elif uri.startswith("/api/global/") and method == "POST":
            name = uri.split("/")[-1]
            return self._api_set_global(name, data)
        elif uri.startswith("/api/shred/") and uri.endswith("/code") and method == "GET":
            shred_id = int(uri.split("/")[-2])
            return self._api_get_shred_code(shred_id)
        elif uri.startswith("/api/shred/") and uri.endswith("/replace") and method == "POST":
            shred_id = int(uri.split("/")[-2])
            return self._api_replace_shred(shred_id, data)
        elif method == "WS":
            # WebSocket message
            return self._handle_ws_message(data)
        else:
            return json.dumps({"error": f"Unknown endpoint: {method} {uri}"})

    def _api_status(self) -> str:
        """Get current status."""
        shreds = self._get_shreds_info()
        return json.dumps(
            {
                "audio_running": self._is_audio_running(),
                "shreds": shreds,
                "now": self._chuck.raw.now(),
            }
        )

    def _api_compile(self, data: dict[str, Any]) -> str:
        """Compile and spork ChucK code."""
        code = data.get("code", "")
        if not code:
            return json.dumps({"success": False, "error": "No code provided"})

        try:
            success, shred_ids = self._chuck.compile(code)
            if success:
                # Track shred start times and code
                now = time.time()
                # Truncate code for preview (first 500 chars)
                preview = code[:500] + ("..." if len(code) > 500 else "")
                for sid in shred_ids:
                    self._shred_times[sid] = now
                    self._shred_code[sid] = preview

                self._broadcast_shreds_update()
                return json.dumps({"success": True, "shred_ids": shred_ids})
            else:
                return json.dumps({"success": False, "error": "Compilation failed"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_remove_shred(self, shred_id: int) -> str:
        """Remove a shred by ID."""
        try:
            self._chuck.remove_shred(shred_id)
            self._shred_times.pop(shred_id, None)
            self._shred_code.pop(shred_id, None)
            self._broadcast_shreds_update()
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_clear(self) -> str:
        """Clear all shreds."""
        try:
            self._chuck.clear()
            self._shred_times.clear()
            self._shred_code.clear()
            self._broadcast_shreds_update()
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_start_audio(self) -> str:
        """Start real-time audio."""
        try:
            from .._numchuck import start_audio

            start_audio(self._chuck.raw)
            self._broadcast_audio_status(True)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_stop_audio(self) -> str:
        """Stop real-time audio."""
        try:
            from .._numchuck import stop_audio

            stop_audio()
            self._broadcast_audio_status(False)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_list_globals(self) -> str:
        """List all global variables with their values."""
        try:
            globals_list = self._chuck.raw.get_all_globals()
            result = []
            for var_type, name in globals_list:
                entry = {"type": var_type, "name": name}
                # Try to get the value
                try:
                    if var_type == "int":
                        entry["value"] = self._chuck.get_int(name)
                    elif var_type == "float":
                        entry["value"] = self._chuck.get_float(name)
                    elif var_type == "string":
                        entry["value"] = self._chuck.get_string(name)
                except Exception:
                    entry["value"] = None
                result.append(entry)
            return json.dumps({"globals": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _api_get_global(self, name: str, data: dict[str, Any]) -> str:
        """Get a global variable value."""
        var_type = data.get("type", "float")
        try:
            if var_type == "int":
                value = self._chuck.get_int(name)
            elif var_type == "float":
                value = self._chuck.get_float(name)
            elif var_type == "string":
                value = self._chuck.get_string(name)
            else:
                return json.dumps({"error": f"Unknown type: {var_type}"})
            return json.dumps({"name": name, "type": var_type, "value": value})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _api_get_shred_code(self, shred_id: int) -> str:
        """Get the code associated with a shred."""
        code = self._shred_code.get(shred_id, "")
        return json.dumps({"shred_id": shred_id, "code": code})

    def _api_replace_shred(self, shred_id: int, data: dict[str, Any]) -> str:
        """Replace a shred with new code."""
        code = data.get("code", "")
        if not code:
            return json.dumps({"success": False, "error": "No code provided"})

        try:
            # Remove old shred
            self._chuck.remove_shred(shred_id)
            self._shred_times.pop(shred_id, None)
            self._shred_code.pop(shred_id, None)

            # Compile new code
            success, shred_ids = self._chuck.compile(code)
            if success:
                now = time.time()
                preview = code[:500] + ("..." if len(code) > 500 else "")
                for sid in shred_ids:
                    self._shred_times[sid] = now
                    self._shred_code[sid] = preview
                self._broadcast_shreds_update()
                return json.dumps({"success": True, "shred_ids": shred_ids})
            else:
                return json.dumps({"success": False, "error": "Compilation failed"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _api_set_global(self, name: str, data: dict[str, Any]) -> str:
        """Set a global variable."""
        value = data.get("value")
        var_type = data.get("type", "float")

        try:
            if var_type == "int":
                self._chuck.set_int(name, int(value))
            elif var_type == "float":
                self._chuck.set_float(name, float(value))
            elif var_type == "string":
                self._chuck.set_string(name, str(value))
            else:
                return json.dumps({"success": False, "error": f"Unknown type: {var_type}"})
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _handle_ws_message(self, data: dict[str, Any]) -> str:
        """Handle WebSocket message from client."""
        msg_type = data.get("type", "")

        if msg_type == "ping":
            return json.dumps({"type": "pong"})
        elif msg_type == "status":
            return self._api_status()

        return ""

    def _get_shreds_info(self) -> list[dict[str, Any]]:
        """Get information about running shreds."""
        shreds = []
        now = time.time()

        for sid in self._chuck.shreds:
            try:
                info = self._chuck.shred_info(sid)
                start_time = self._shred_times.get(sid, now)
                elapsed = int(now - start_time)
                minutes, seconds = divmod(elapsed, 60)

                shreds.append(
                    {
                        "id": sid,
                        "name": info.get("name", "code") if info else "code",
                        "time": f"{minutes:02d}:{seconds:02d}",
                        "code": self._shred_code.get(sid, ""),
                    }
                )
            except Exception:
                shreds.append({"id": sid, "name": "code", "time": "00:00", "code": ""})

        return shreds

    def _is_audio_running(self) -> bool:
        """Check if audio is running."""
        try:
            from .._numchuck import is_audio_running

            return is_audio_running()
        except Exception:
            return False

    def _broadcast_shreds_update(self) -> None:
        """Broadcast shreds update to all clients."""
        if self._server.is_running:
            shreds = self._get_shreds_info()
            self._server.broadcast(json.dumps({"type": "shreds", "shreds": shreds}))

    def _broadcast_audio_status(self, running: bool) -> None:
        """Broadcast audio status to all clients."""
        if self._server.is_running:
            self._server.broadcast(
                json.dumps({"type": "audio_status", "running": running})
            )

    @property
    def port(self) -> int:
        """Server port."""
        return self._server.port

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._server.is_running

    @property
    def client_count(self) -> int:
        """Number of connected WebSocket clients."""
        return self._server.client_count

    @property
    def url(self) -> str:
        """Server URL."""
        return f"http://localhost:{self.port}"

    def start(self) -> None:
        """Start the web server."""
        if not self._server.start():
            raise RuntimeError("Failed to start web server")

    def stop(self) -> None:
        """Stop the web server."""
        self._server.stop()
        # Clear callbacks to break reference cycles and prevent crash at shutdown
        self._chuck.set_stdout_callback(None)
        self._chuck.set_stderr_callback(None)
        # Clear API handler to break cycle: self -> _server -> handler -> self
        self._server.set_api_handler(lambda m, u, b: "")

    def __enter__(self) -> "WebChuckServer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()


__all__ = ["WebChuckServer", "WEB_AVAILABLE"]
