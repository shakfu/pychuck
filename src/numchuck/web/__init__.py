"""numchuck web server module.

Provides a browser-based IDE for ChucK live coding.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..constants import DEFAULT_WEB_PORT, MAX_CONSOLE_LINES
from ..tui.parser import CommandParser

# Broadcast interval for meters and globals (seconds)
METER_BROADCAST_INTERVAL = 0.1  # 100ms for smooth meter updates
GLOBALS_CHECK_INTERVAL = 0.5  # 500ms for globals changes

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

    # Default static directory within the package
    _DEFAULT_STATIC_DIR = Path(__file__).parent / "static"

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
            static_dir: Directory for static files (optional, uses package's static/ if None)
        """
        if not WEB_AVAILABLE:
            raise ImportError(
                "Web module not available. "
                "Rebuild numchuck with -DNUMCHUCK_ENABLE_WEB=ON"
            )

        self._chuck = chuck
        self._server = _WebServer()
        self._server.port = port

        # Use provided static_dir or default to package's static folder
        if static_dir:
            self._server.static_dir = str(Path(static_dir).resolve())
        else:
            self._server.static_dir = str(self._DEFAULT_STATIC_DIR.resolve())

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

        # Broadcast loop state
        self._broadcast_thread: threading.Thread | None = None
        self._broadcast_stop_event = threading.Event()
        self._last_globals_json = ""

        # REPL support
        self._parser = CommandParser()

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
        elif (
            uri.startswith("/api/shred/") and uri.endswith("/code") and method == "GET"
        ):
            shred_id = int(uri.split("/")[-2])
            return self._api_get_shred_code(shred_id)
        elif (
            uri.startswith("/api/shred/")
            and uri.endswith("/replace")
            and method == "POST"
        ):
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
            result: list[dict[str, Any]] = []
            for var_type, name in globals_list:
                entry: dict[str, Any] = {"type": var_type, "name": name}
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
            value: int | float | str
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

        if value is None:
            return json.dumps({"success": False, "error": "No value provided"})

        try:
            if var_type == "int":
                self._chuck.set_int(name, int(value))
            elif var_type == "float":
                self._chuck.set_float(name, float(value))
            elif var_type == "string":
                self._chuck.set_string(name, str(value))
            else:
                return json.dumps(
                    {"success": False, "error": f"Unknown type: {var_type}"}
                )
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
        elif msg_type == "repl":
            return self._handle_repl_command(data.get("command", ""))

        return ""

    def _handle_repl_command(self, input_text: str) -> str:
        """Handle REPL command from web terminal."""
        input_text = input_text.strip()
        if not input_text:
            return ""

        # Handle help command directly
        if input_text.lower() == "help":
            return self._repl_help()

        # Try to parse as a command
        cmd = self._parser.parse(input_text)

        if cmd:
            return self._execute_repl_command(cmd)
        else:
            # Not a recognized command - try to compile as ChucK code
            return self._compile_repl_code(input_text)

    def _execute_repl_command(self, cmd: Any) -> str:
        """Execute a parsed REPL command."""
        cmd_type = cmd.type
        args = cmd.args

        try:
            # Shred management
            if cmd_type == "spork_file":
                path = args.get("path", "")
                success, shred_ids = self._chuck.compile_file(path)
                if success:
                    now = time.time()
                    for sid in shred_ids:
                        self._shred_times[sid] = now
                        self._shred_code[sid] = f"file: {path}"
                    self._broadcast_shreds_update()
                    return self._repl_output(
                        f"[shred {shred_ids}]: sporking file: {path}", "success"
                    )
                else:
                    return self._repl_error(f"Failed to compile: {path}")

            elif cmd_type == "spork_code":
                code = args.get("code", "")
                return self._compile_repl_code(code)

            elif cmd_type == "remove_shred":
                sid = args.get("id")
                self._chuck.remove_shred(sid)
                self._shred_times.pop(sid, None)
                self._shred_code.pop(sid, None)
                self._broadcast_shreds_update()
                return self._repl_output(f"[shred {sid}]: removed", "info")

            elif cmd_type == "abort_shred":
                sid = args.get("id")
                self._chuck.remove_shred(sid)
                self._shred_times.pop(sid, None)
                self._shred_code.pop(sid, None)
                self._broadcast_shreds_update()
                return self._repl_output(f"[shred {sid}]: abort", "info")

            elif cmd_type == "remove_all":
                self._chuck.clear()
                self._shred_times.clear()
                self._shred_code.clear()
                self._broadcast_shreds_update()
                return self._repl_output("Removed all shreds", "info")

            elif cmd_type == "clear_vm":
                self._chuck.clear()
                self._shred_times.clear()
                self._shred_code.clear()
                self._broadcast_shreds_update()
                return self._repl_output("VM cleared", "info")

            elif cmd_type == "reset_id":
                self._chuck.reset_id()
                return self._repl_output("Shred ID counter reset", "info")

            elif cmd_type == "replace_shred":
                sid = args.get("id")
                code = args.get("code", "")
                try:
                    new_id = self._chuck.replace_shred(sid, code)
                    self._shred_times.pop(sid, None)
                    self._shred_code.pop(sid, None)
                    now = time.time()
                    self._shred_times[new_id] = now
                    self._shred_code[new_id] = code[:100] + (
                        "..." if len(code) > 100 else ""
                    )
                    self._broadcast_shreds_update()
                    return self._repl_output(
                        f"[shred {sid}]: replaced with [shred {new_id}]", "success"
                    )
                except Exception as e:
                    return self._repl_error(f"Failed to replace shred {sid}: {e}")

            elif cmd_type == "replace_shred_file":
                sid = args.get("id")
                path = args.get("path", "")
                try:
                    # Read file and replace
                    with open(path) as f:
                        code = f.read()
                    new_id = self._chuck.replace_shred(sid, code)
                    self._shred_times.pop(sid, None)
                    self._shred_code.pop(sid, None)
                    now = time.time()
                    self._shred_times[new_id] = now
                    self._shred_code[new_id] = f"file: {path}"
                    self._broadcast_shreds_update()
                    return self._repl_output(
                        f"[shred {sid}]: replaced with {path} [shred {new_id}]",
                        "success",
                    )
                except FileNotFoundError:
                    return self._repl_error(f"File not found: {path}")
                except Exception as e:
                    return self._repl_error(f"Failed to replace shred {sid}: {e}")

            # Status commands
            elif cmd_type == "status":
                return self._repl_status()

            elif cmd_type == "list_shreds":
                return self._repl_list_shreds()

            elif cmd_type == "shred_info":
                sid = args.get("id")
                info = self._chuck.shred_info(sid)
                if info:
                    return self._repl_output(f"Shred {sid}: {info}", "info")
                else:
                    return self._repl_error(f"Shred {sid} not found")

            elif cmd_type == "current_time":
                now_time = self._chuck.raw.now()
                srate = self._chuck.sample_rate
                seconds = now_time / srate
                return self._repl_output(
                    f"now: {now_time:.0f} samples ({seconds:.3f}s)", "info"
                )

            elif cmd_type == "list_globals":
                return self._repl_list_globals()

            elif cmd_type == "audio_info":
                from .._numchuck import audio_info, is_audio_running

                running = is_audio_running()
                info = audio_info()
                status = "running" if running else "stopped"
                return self._repl_output(
                    f"Audio: {status}\n"
                    f"  Sample rate: {info.get('sample_rate', 0)} Hz\n"
                    f"  Output channels: {info.get('num_channels_out', 0)}\n"
                    f"  Input channels: {info.get('num_channels_in', 0)}\n"
                    f"  Buffer size: {info.get('buffer_size', 0)}",
                    "info",
                )

            # Global variables
            elif cmd_type == "set_global":
                name = args.get("name", "")
                value = args.get("value", "")
                # Try to determine type and set
                try:
                    if "." in value:
                        self._chuck.set_float(name, float(value))
                    else:
                        self._chuck.set_int(name, int(value))
                    return self._repl_output(f"{name} = {value}", "success")
                except ValueError:
                    self._chuck.set_string(name, value)
                    return self._repl_output(f'{name} = "{value}"', "success")

            elif cmd_type == "get_global":
                name = args.get("name", "")
                # Try to get value (try int, then float, then string)
                try:
                    value = self._chuck.get_int(name)
                    return self._repl_output(f"{name} = {value}", "info")
                except Exception:
                    pass
                try:
                    value = self._chuck.get_float(name)
                    return self._repl_output(f"{name} = {value}", "info")
                except Exception:
                    pass
                try:
                    value = self._chuck.get_string(name)
                    return self._repl_output(f'{name} = "{value}"', "info")
                except Exception:
                    return self._repl_error(f"Global '{name}' not found")

            # Events
            elif cmd_type == "signal_event":
                name = args.get("name", "")
                self._chuck.signal_event(name)
                return self._repl_output(f"Signaled event: {name}", "info")

            elif cmd_type == "broadcast_event":
                name = args.get("name", "")
                self._chuck.broadcast_event(name)
                return self._repl_output(f"Broadcast event: {name}", "info")

            # Audio control
            elif cmd_type == "start_audio":
                from .._numchuck import start_audio

                start_audio(self._chuck.raw)
                self._broadcast_audio_status(True)
                return self._repl_output("Audio started", "success")

            elif cmd_type == "stop_audio":
                from .._numchuck import stop_audio

                stop_audio()
                self._broadcast_audio_status(False)
                return self._repl_output("Audio stopped", "info")

            elif cmd_type == "shutdown_audio":
                from .._numchuck import shutdown_audio

                shutdown_audio()
                self._broadcast_audio_status(False)
                return self._repl_output("Audio shutdown", "info")

            # Help
            elif cmd_type == "help":
                return self._repl_help()

            # Exit (no-op in web)
            elif cmd_type == "exit":
                return self._repl_output("Use browser to close the page", "info")

            # Clear screen (handled client-side, but acknowledge)
            elif cmd_type == "clear_screen":
                return self._repl_output("", "info")

            else:
                return self._repl_error(f"Unknown command: {cmd_type}")

        except Exception as e:
            return self._repl_error(str(e))

    def _compile_repl_code(self, code: str) -> str:
        """Compile ChucK code from REPL input."""
        try:
            success, shred_ids = self._chuck.compile(code)
            if success:
                now = time.time()
                preview = code[:100] + ("..." if len(code) > 100 else "")
                for sid in shred_ids:
                    self._shred_times[sid] = now
                    self._shred_code[sid] = preview
                self._broadcast_shreds_update()
                return self._repl_output(
                    f"[shred {shred_ids}]: sporking code", "success"
                )
            else:
                return self._repl_error("Compilation failed")
        except Exception as e:
            return self._repl_error(str(e))

    def _repl_output(self, text: str, style: str = "info") -> str:
        """Create REPL output message."""
        return json.dumps({"type": "repl_output", "text": text, "style": style})

    def _repl_error(self, text: str) -> str:
        """Create REPL error message."""
        return json.dumps({"type": "repl_error", "text": text})

    def _repl_status(self) -> str:
        """Get REPL status output."""
        shreds = self._chuck.shreds
        running = self._is_audio_running()
        now_time = self._chuck.raw.now()
        srate = self._chuck.sample_rate

        lines = [
            f"Audio: {'running' if running else 'stopped'}",
            f"Shreds: {len(shreds)} running",
            f"Now: {now_time:.0f} samples ({now_time / srate:.3f}s)",
        ]
        if shreds:
            lines.append("Active shreds: " + ", ".join(str(s) for s in shreds))

        return self._repl_output("\n".join(lines), "info")

    def _repl_list_shreds(self) -> str:
        """List shreds for REPL."""
        shreds = self._get_shreds_info()
        if not shreds:
            return self._repl_output("No shreds running", "info")

        lines = ["ID    Name                 Time"]
        lines.append("-" * 40)
        for s in shreds:
            name = s.get("name", "code")[:20]
            lines.append(f"{s['id']:<5} {name:<20} {s['time']}")

        return self._repl_output("\n".join(lines), "info")

    def _repl_list_globals(self) -> str:
        """List global variables for REPL."""
        try:
            globals_list = self._chuck.raw.get_all_globals()
            if not globals_list:
                return self._repl_output("No global variables", "info")

            lines = ["Type    Name                 Value"]
            lines.append("-" * 45)
            for var_type, name in globals_list:
                value: str = "?"
                try:
                    if var_type == "int":
                        value = str(self._chuck.get_int(name))
                    elif var_type == "float":
                        value = f"{self._chuck.get_float(name):.4f}"
                    elif var_type == "string":
                        value = f'"{self._chuck.get_string(name)}"'
                except Exception:
                    pass
                lines.append(f"{var_type:<7} {name:<20} {value}")

            return self._repl_output("\n".join(lines), "info")
        except Exception as e:
            return self._repl_error(str(e))

    def _repl_help(self) -> str:
        """Show REPL help."""
        help_text = """numchuck REPL Commands:

Shred Management (ChucK-compatible):
  + file.ck          Spork/add a file
  + "code"           Spork inline code
  - <id>             Remove shred
  - all              Remove all shreds
  = <id> file.ck     Replace shred with file
  = <id> "code"      Replace shred with code
  status / ^         Show VM status
  ? / ?<id>          List shreds / shred info
  abort <id>         Abort shred (same as remove)

Global Variables:
  name::value        Set global (int/float)
  name?              Get global value
  ?g                 List all globals

Events:
  name!              Signal event
  name!!             Broadcast event

Audio:
  >                  Start audio
  ||                 Stop audio
  ?a                 Audio info

VM Control:
  .                  Show current time
  clear              Clear VM (clear.vm)
  reset              Reset shred ID counter (reset.id)
  help               Show this help

Or enter ChucK code directly to compile and run."""
        return self._repl_output(help_text, "info")

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

    def _broadcast_meters(self) -> None:
        """Broadcast audio meter values to all clients."""
        if not self._server.is_running:
            return

        try:
            from .._numchuck import get_audio_meters, is_audio_running

            if is_audio_running():
                meters = get_audio_meters()
                msg = {
                    "type": "audio_meters",
                    "rms_left": meters.get("rms_left", 0.0),
                    "rms_right": meters.get("rms_right", 0.0),
                    "peak_left": meters.get("peak_left", 0.0),
                    "peak_right": meters.get("peak_right", 0.0),
                }
                self._server.broadcast(json.dumps(msg))
        except Exception:
            pass

    def _broadcast_globals_if_changed(self) -> None:
        """Broadcast globals update if values have changed."""
        if not self._server.is_running:
            return

        try:
            globals_json = self._api_list_globals()
            if globals_json != self._last_globals_json:
                self._last_globals_json = globals_json
                # Parse and reformat for WebSocket message
                data = json.loads(globals_json)
                msg = {"type": "globals", "globals": data.get("globals", [])}
                self._server.broadcast(json.dumps(msg))
        except Exception:
            pass

    def _broadcast_loop(self) -> None:
        """Background loop for meter and globals broadcasting."""
        meter_counter = 0
        globals_interval_count = int(GLOBALS_CHECK_INTERVAL / METER_BROADCAST_INTERVAL)

        while not self._broadcast_stop_event.is_set():
            # Broadcast meters every iteration (100ms)
            self._broadcast_meters()

            # Broadcast globals less frequently (every 500ms)
            meter_counter += 1
            if meter_counter >= globals_interval_count:
                meter_counter = 0
                self._broadcast_globals_if_changed()

            # Sleep for the meter interval
            self._broadcast_stop_event.wait(METER_BROADCAST_INTERVAL)

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

        # Start broadcast loop thread
        self._broadcast_stop_event.clear()
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop, daemon=True, name="numchuck-web-broadcast"
        )
        self._broadcast_thread.start()

    def stop(self) -> None:
        """Stop the web server."""
        # Stop broadcast loop thread
        self._broadcast_stop_event.set()
        if self._broadcast_thread is not None:
            self._broadcast_thread.join(timeout=1.0)
            self._broadcast_thread = None

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
