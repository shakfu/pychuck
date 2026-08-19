"""numchuck web server module.

Provides a browser-based IDE for ChucK live coding.

Security
--------
Everything this server exposes -- ``/api/compile``, the WebSocket REPL, the
globals endpoints -- amounts to running arbitrary ChucK, and ChucK can touch the
filesystem. So the server is only as safe as the set of people who can reach it:

* It binds ``127.0.0.1`` unless the caller passes something else.
* Every bind gets an auth token, generated if one was not supplied, and without
  it each ``/api/`` request and the WebSocket upgrade are refused. Loopback is
  included: it keeps the browser honest, but it is not a private channel -- any
  other process on the machine can reach it, and a non-browser client sends no
  ``Origin`` for the check below to act on.
* The C++ layer rejects any request whose ``Origin`` disagrees with its
  ``Host``, which is what stops a page on another site from driving the IDE over
  a WebSocket -- those are not covered by the same-origin policy on their own.

Commands that would spawn a local process (``shell``, the external-editor
commands) are refused outright; see ``_DENIED_COMMANDS``.
"""

from __future__ import annotations

import ipaddress
import json
import secrets
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..constants import (
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
    MAX_CONSOLE_LINES,
    WEB_TOKEN_BYTES,
)
from ..services import AudioService, GlobalsService, ShredService
from ..tui.parser import Command, CommandParser
from ..tui.commands import CommandExecutor
from ..tui.session import ChuckSession

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


# Commands the shared executor supports but the web front-end must not run.
# Two kinds: those that start a process on the machine hosting the server, and
# those that only terminate at a terminal (an infinite loop broken by Ctrl-C
# would hold the server thread forever). Mapping them here rather than omitting
# them means the browser gets a reason instead of "unknown command", and the
# test suite can assert the list stays exhaustive against the executor.
_DENIED_COMMANDS: dict[str, str] = {
    "shell": "shell commands are disabled in the web IDE",
    "open_editor": "the external editor is not available in the web IDE",
    "edit_shred": "the external editor is not available in the web IDE; use 'edit' in the browser",
    "watch": "'watch' runs until interrupted at a terminal; the shreds panel updates live instead",
}


def is_loopback_host(host: str) -> bool:
    """Whether binding to ``host`` keeps the server off the network."""
    if host in ("localhost", ""):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


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
        >>> # Browse to server.url
        >>> server.stop()
    """

    # Default static directory within the package
    _DEFAULT_STATIC_DIR = Path(__file__).parent / "static"

    def __init__(
        self,
        chuck: Chuck,
        port: int = DEFAULT_WEB_PORT,
        host: str = DEFAULT_WEB_HOST,
        auth_token: str | None = None,
        static_dir: str | Path | None = None,
    ) -> None:
        """Initialize web server.

        Args:
            chuck: ChucK instance to control
            port: HTTP port to listen on (default: 8080)
            host: Address to bind (default: 127.0.0.1, loopback only)
            auth_token: Bearer token required on /api/ and /ws. Left as None a
                token is generated, exposed as ``auth_token`` and embedded in
                ``url`` -- including for a loopback bind, since loopback is not
                a private channel on a shared machine. Pass "" to disable auth
                deliberately.
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
        self._server.host = host
        self._host = host

        # Always minted, loopback included. The origin check stops a *browser*
        # on another site, but it only applies to requests that carry an Origin
        # -- any local process can POST to /api/compile without one, and on a
        # shared machine that is every other user on the box. The token is what
        # makes the IDE the operator's rather than the host's. Same reasoning as
        # Jupyter, which also tokenizes a localhost bind.
        if auth_token is None:
            auth_token = secrets.token_urlsafe(WEB_TOKEN_BYTES)
        self._server.auth_token = auth_token

        # Use provided static_dir or default to package's static folder
        if static_dir:
            self._server.static_dir = str(Path(static_dir).resolve())
        else:
            self._server.static_dir = str(self._DEFAULT_STATIC_DIR.resolve())

        # Set up API handler
        self._server.set_api_handler(self._handle_api)

        # Shared command layer. The web front-end runs the same executor as the
        # TUI over the same services, so a command added in one place exists in
        # both -- the two used to carry independent dispatchers that silently
        # drifted apart.
        raw = chuck.raw
        self._session = ChuckSession(raw)
        self._shreds = ShredService(raw, self._session)
        self._globals = GlobalsService(raw)
        self._audio = AudioService(raw)
        self._executor = CommandExecutor(
            self._session,
            shred_service=self._shreds,
            globals_service=self._globals,
            log_callback=self._executor_output,
        )
        self._parser = CommandParser()

        # Per-thread capture of executor output, so a REPL command can return
        # what it printed. Thread-local because the broadcast loop also logs.
        self._capture = threading.local()

        # Wall-clock start time per shred, for the elapsed column. The session
        # records ChucK VM time, which is not what the UI shows.
        self._shred_times: dict[int, float] = {}

        # Console output buffer
        self._console_lines: list[dict[str, str]] = []
        self._max_console_lines = MAX_CONSOLE_LINES

        # Broadcast loop state
        self._broadcast_thread: threading.Thread | None = None
        self._broadcast_stop_event = threading.Event()
        self._last_globals_json = ""
        self._last_audio_running = False

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

    def _executor_output(self, message: str) -> None:
        """Receive a line printed by the shared command executor."""
        buffer: list[str] | None = getattr(self._capture, "lines", None)
        if buffer is not None:
            buffer.append(message)
        else:
            self._log(message, "info")

    # -------------------------------------------------------------------------
    # Auth / addressing
    # -------------------------------------------------------------------------

    @property
    def host(self) -> str:
        """Address the server binds to."""
        return self._host

    @property
    def auth_token(self) -> str:
        """Bearer token required by clients, or "" when auth is disabled."""
        token: str = self._server.auth_token
        return token

    @property
    def url(self) -> str:
        """Server URL, carrying the auth token when one is required."""
        # A wildcard bind has no single address to advertise; loopback is the
        # one that always reaches it from the host itself.
        display = "localhost" if self._host in ("0.0.0.0", "::", "") else self._host
        if ":" in display and not display.startswith("["):
            display = f"[{display}]"
        base = f"http://{display}:{self.port}"
        return f"{base}/?token={self.auth_token}" if self.auth_token else base

    # -------------------------------------------------------------------------
    # HTTP API
    # -------------------------------------------------------------------------

    def _handle_api(self, method: str, uri: str, body: str) -> tuple[int, str]:
        """Handle API requests from web clients.

        Args:
            method: HTTP method (GET, POST, DELETE, WS)
            uri: Request URI
            body: Request body (JSON string)

        Returns:
            (http_status, json_response_body)
        """
        try:
            # Only parse body for methods that have one
            if body and body.strip() and method in ("POST", "PUT", "PATCH", "WS"):
                data = json.loads(body)
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}

        try:
            return self._route(method, uri, data)
        except Exception as e:  # noqa: BLE001 - must not escape into the C++ loop
            return 500, json.dumps({"error": f"{type(e).__name__}: {e}"})

    def _route(self, method: str, uri: str, data: dict[str, Any]) -> tuple[int, str]:
        """Dispatch a request to its handler."""
        if uri == "/api/status":
            return 200, self._api_status()
        if uri == "/api/compile" and method == "POST":
            return self._api_compile(data)
        if uri == "/api/clear" and method == "POST":
            return self._api_clear()
        if uri == "/api/audio/start" and method == "POST":
            return self._api_start_audio()
        if uri == "/api/audio/stop" and method == "POST":
            return self._api_stop_audio()
        if uri == "/api/globals" and method == "GET":
            return self._api_list_globals()
        if uri.startswith("/api/global/"):
            name = uri[len("/api/global/") :]
            if not name:
                return 404, json.dumps({"error": "Missing global name"})
            if method == "GET":
                return self._api_get_global(name, data)
            if method == "POST":
                return self._api_set_global(name, data)

        if uri.startswith("/api/shred/"):
            # /api/shred/<id>, /api/shred/<id>/code, /api/shred/<id>/replace
            rest = uri[len("/api/shred/") :].split("/")
            # A non-numeric id is a client mistake, not a server fault: parsing
            # it unguarded used to raise ValueError and answer 500.
            try:
                shred_id = int(rest[0])
            except ValueError:
                return 400, json.dumps({"error": f"Invalid shred id: {rest[0]!r}"})
            tail = rest[1] if len(rest) > 1 else ""
            if tail == "" and method == "DELETE":
                return self._api_remove_shred(shred_id)
            if tail == "code" and method == "GET":
                return 200, self._api_get_shred_code(shred_id)
            if tail == "replace" and method == "POST":
                return self._api_replace_shred(shred_id, data)

        if method == "WS":
            return 200, self._handle_ws_message(data)

        return 404, json.dumps({"error": f"Unknown endpoint: {method} {uri}"})

    @staticmethod
    def _ok(**fields: Any) -> tuple[int, str]:
        return 200, json.dumps({"success": True, **fields})

    @staticmethod
    def _fail(message: str, status: int = 400) -> tuple[int, str]:
        return status, json.dumps({"success": False, "error": message})

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

    def _api_compile(self, data: dict[str, Any]) -> tuple[int, str]:
        """Compile and spork ChucK code."""
        code = data.get("code", "")
        if not code:
            return self._fail("No code provided")

        result = self._shreds.spork_code(code)
        if not result.success:
            return self._fail(result.error or "Compilation failed", status=422)

        self._note_new_shreds(result.shred_ids)
        self._broadcast_shreds_update()
        return self._ok(shred_ids=result.shred_ids)

    def _api_remove_shred(self, shred_id: int) -> tuple[int, str]:
        """Remove a shred by ID."""
        if not self._shreds.remove_shred(shred_id):
            return self._fail(f"Failed to remove shred {shred_id}", status=404)
        self._shred_times.pop(shred_id, None)
        self._broadcast_shreds_update()
        return self._ok()

    def _api_clear(self) -> tuple[int, str]:
        """Clear all shreds."""
        if not self._shreds.clear_vm():
            return self._fail("Failed to clear VM", status=500)
        self._shred_times.clear()
        self._broadcast_shreds_update()
        return self._ok()

    def _api_start_audio(self) -> tuple[int, str]:
        """Start real-time audio."""
        self._audio.sync_state()
        if not self._audio.start():
            return self._fail("Failed to start audio", status=500)
        self._broadcast_audio_status(True)
        return self._ok()

    def _api_stop_audio(self) -> tuple[int, str]:
        """Stop real-time audio."""
        self._audio.sync_state()
        if not self._audio.stop():
            return self._fail("Failed to stop audio", status=500)
        self._broadcast_audio_status(False)
        return self._ok()

    def _api_list_globals(self) -> tuple[int, str]:
        """List all global variables with their values."""
        return 200, self._globals_json()

    def _globals_json(self) -> str:
        """Serialize the globals table."""
        result: list[dict[str, Any]] = []
        for info in self._globals.list_globals():
            entry: dict[str, Any] = {"type": info.type, "name": info.name}
            if info.type == "int":
                entry["value"] = self._globals.get_global_int(info.name)
            elif info.type == "float":
                entry["value"] = self._globals.get_global_float(info.name)
            elif info.type == "string":
                entry["value"] = self._globals.get_global_string(info.name)
            else:
                entry["value"] = None
            result.append(entry)
        return json.dumps({"globals": result})

    def _api_get_global(self, name: str, data: dict[str, Any]) -> tuple[int, str]:
        """Get a global variable value."""
        var_type = data.get("type")
        if var_type is None:
            found = self._globals.get_global(name)
            if found is None:
                return 404, json.dumps({"error": f"Global '{name}' not found"})
            var_type, value = found
        elif var_type == "int":
            value = self._globals.get_global_int(name)
        elif var_type == "float":
            value = self._globals.get_global_float(name)
        elif var_type == "string":
            value = self._globals.get_global_string(name)
        else:
            return 400, json.dumps({"error": f"Unknown type: {var_type}"})
        return 200, json.dumps({"name": name, "type": var_type, "value": value})

    def _api_get_shred_code(self, shred_id: int) -> str:
        """Get the code associated with a shred."""
        record = self._session.shreds.get(shred_id, {})
        return json.dumps({"shred_id": shred_id, "code": record.get("source", "")})

    def _api_replace_shred(
        self, shred_id: int, data: dict[str, Any]
    ) -> tuple[int, str]:
        """Replace a shred with new code."""
        code = data.get("code", "")
        if not code:
            return self._fail("No code provided")

        result = self._shreds.replace_shred(shred_id, code)
        if not result.success:
            return self._fail(result.error or "Compilation failed", status=422)

        self._shred_times.pop(shred_id, None)
        self._note_new_shreds(result.shred_ids)
        self._broadcast_shreds_update()
        return self._ok(shred_ids=result.shred_ids)

    def _api_set_global(self, name: str, data: dict[str, Any]) -> tuple[int, str]:
        """Set a global variable."""
        value = data.get("value")
        var_type = data.get("type", "float")

        if value is None:
            return self._fail("No value provided")

        try:
            if var_type == "int":
                ok = self._globals.set_global_int(name, int(value))
            elif var_type == "float":
                ok = self._globals.set_global_float(name, float(value))
            elif var_type == "string":
                ok = self._globals.set_global_string(name, str(value))
            else:
                return self._fail(f"Unknown type: {var_type}")
        except (TypeError, ValueError) as e:
            return self._fail(f"Invalid value for {var_type}: {e}")

        if not ok:
            return self._fail(f"Failed to set global '{name}'", status=500)
        return self._ok()

    # -------------------------------------------------------------------------
    # WebSocket / REPL
    # -------------------------------------------------------------------------

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

        if input_text.lower() == "help":
            return self._repl_help()

        cmd = self._parser.parse(input_text)
        if cmd is None:
            # Not a recognized command - treat it as ChucK source
            return self._compile_repl_code(input_text)
        return self._execute_repl_command(cmd)

    def _execute_repl_command(self, cmd: Command) -> str:
        """Run a parsed command through the shared executor."""
        denied = _DENIED_COMMANDS.get(cmd.type)
        if denied is not None:
            return self._repl_error(denied)

        if cmd.type == "help":
            return self._repl_help()
        if cmd.type == "exit":
            return self._repl_output("Close the browser tab to disconnect", "info")
        if cmd.type == "clear_screen":
            return json.dumps({"type": "repl_clear"})

        was_running = self._is_audio_running()
        self._capture.lines = []
        try:
            error = self._executor.execute(cmd)
            output = "\n".join(self._capture.lines)
        except Exception as e:  # noqa: BLE001 - a bad command must not kill the socket
            return self._repl_error(f"{type(e).__name__}: {e}")
        finally:
            self._capture.lines = None

        self._sync_shred_times()
        self._broadcast_shreds_update()
        now_running = self._is_audio_running()
        if now_running != was_running:
            self._broadcast_audio_status(now_running)

        if error:
            return self._repl_error(error)
        return self._repl_output(output, "success" if output else "info")

    def _compile_repl_code(self, code: str) -> str:
        """Compile ChucK code from REPL input."""
        result = self._shreds.spork_code(code)
        if not result.success:
            return self._repl_error(result.error or "Compilation failed")
        self._note_new_shreds(result.shred_ids)
        self._broadcast_shreds_update()
        return self._repl_output(
            f"[shred {result.shred_ids}]: sporking code", "success"
        )

    def _repl_output(self, text: str, style: str = "info") -> str:
        """Create REPL output message."""
        return json.dumps({"type": "repl_output", "text": text, "style": style})

    def _repl_error(self, text: str) -> str:
        """Create REPL error message."""
        return json.dumps({"type": "repl_error", "text": text})

    def _repl_help(self) -> str:
        """Show REPL help."""
        denied = "\n".join(
            f"  {name:<18} unavailable here" for name in sorted(_DENIED_COMMANDS)
        )
        help_text = f"""numchuck REPL Commands:

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

Disabled in the browser (they would run a process on the server):
{denied}

Or enter ChucK code directly to compile and run."""
        return self._repl_output(help_text, "info")

    # -------------------------------------------------------------------------
    # Shred bookkeeping
    # -------------------------------------------------------------------------

    def _note_new_shreds(self, shred_ids: list[int]) -> None:
        """Stamp wall-clock start times for freshly sporked shreds."""
        now = time.time()
        for sid in shred_ids:
            self._shred_times[sid] = now

    def _sync_shred_times(self) -> None:
        """Add times for shreds that appeared, drop those that are gone."""
        now = time.time()
        live = set(self._session.shreds)
        for sid in live - self._shred_times.keys():
            self._shred_times[sid] = now
        for sid in self._shred_times.keys() - live:
            del self._shred_times[sid]

    def _get_shreds_info(self) -> list[dict[str, Any]]:
        """Get information about running shreds."""
        # Reconcile with the VM's own shred list to pick up anything added out
        # of band (OTF) or since finished -- but only while the VM is actually
        # being driven. A spork is a queued message: with no audio running the
        # VM never processes it, so its id list stays empty and syncing against
        # it would discard every shred the session legitimately knows about.
        if self._is_audio_running():
            self._session.sync_shreds()
        self._sync_shred_times()

        now = time.time()
        shreds = []
        for sid, record in sorted(self._session.shreds.items()):
            elapsed = int(now - self._shred_times.get(sid, now))
            minutes, seconds = divmod(elapsed, 60)
            shreds.append(
                {
                    "id": sid,
                    "name": record.get("name", "code"),
                    "time": f"{minutes:02d}:{seconds:02d}",
                    "code": record.get("source", ""),
                }
            )
        return shreds

    def _is_audio_running(self) -> bool:
        """Check if audio is running, according to the audio system itself."""
        # Not self._audio.is_running: the REPL executor calls start_audio()
        # directly, so the service's own flag is not authoritative here.
        return self._audio.sync_state()

    # -------------------------------------------------------------------------
    # Broadcasting
    # -------------------------------------------------------------------------

    def _broadcast_shreds_update(self) -> None:
        """Broadcast shreds update to all clients."""
        if self._server.is_running:
            shreds = self._get_shreds_info()
            self._server.broadcast(json.dumps({"type": "shreds", "shreds": shreds}))

    def _broadcast_audio_status(self, running: bool) -> None:
        """Broadcast audio status to all clients."""
        self._last_audio_running = running
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
        except (RuntimeError, OSError):
            pass

    def _broadcast_globals_if_changed(self) -> None:
        """Broadcast globals update if values have changed."""
        if not self._server.is_running:
            return

        try:
            globals_json = self._globals_json()
        except (RuntimeError, OSError):
            return
        if globals_json == self._last_globals_json:
            return
        self._last_globals_json = globals_json
        data = json.loads(globals_json)
        self._server.broadcast(
            json.dumps({"type": "globals", "globals": data.get("globals", [])})
        )

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

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

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

    def start(self) -> None:
        """Start the web server."""
        if not self._server.start():
            raise RuntimeError(
                f"Failed to start web server on {self._host}:{self.port} "
                "(address in use, or not permitted)"
            )

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
        self._server.set_api_handler(lambda m, u, b: (204, ""))

    def __enter__(self) -> "WebChuckServer":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()


__all__ = ["WebChuckServer", "WEB_AVAILABLE", "is_loopback_host"]
