"""
Open Sound Control (OSC) support for numchuck.

Provides OSC server/client for remote control and ChucK code generation
for native OSC integration using ChucK's built-in liblo support.
"""

from __future__ import annotations

import socket
import struct
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from .constants import (
    DEFAULT_OSC_HOST,
    DEFAULT_OSC_PORT,
    OSC_ALIGNMENT,
    OSC_SOCKET_TIMEOUT,
    OSC_THREAD_SHUTDOWN_TIMEOUT,
)

if TYPE_CHECKING:
    pass


def _pad_string(s: str) -> bytes:
    """Pad a string to 4-byte boundary with null terminator."""
    s_bytes = s.encode("utf-8") + b"\x00"
    padding = (OSC_ALIGNMENT - len(s_bytes) % OSC_ALIGNMENT) % OSC_ALIGNMENT
    return s_bytes + b"\x00" * padding


def _pad_bytes(b: bytes) -> bytes:
    """Pad bytes to 4-byte boundary."""
    padding = (OSC_ALIGNMENT - len(b) % OSC_ALIGNMENT) % OSC_ALIGNMENT
    return b + b"\x00" * padding


def encode_osc_message(address: str, *args: Any) -> bytes:
    """Encode an OSC message.

    Args:
        address: OSC address pattern (e.g., "/test")
        *args: Arguments (int, float, str, bytes supported)

    Returns:
        Encoded OSC message bytes
    """
    # Address
    data = _pad_string(address)

    # Type tag string
    type_tags = ","
    for arg in args:
        if isinstance(arg, int):
            type_tags += "i"
        elif isinstance(arg, float):
            type_tags += "f"
        elif isinstance(arg, str):
            type_tags += "s"
        elif isinstance(arg, bytes):
            type_tags += "b"
        else:
            raise ValueError(f"Unsupported OSC type: {type(arg)}")
    data += _pad_string(type_tags)

    # Arguments
    for arg in args:
        if isinstance(arg, int):
            data += struct.pack(">i", arg)
        elif isinstance(arg, float):
            data += struct.pack(">f", arg)
        elif isinstance(arg, str):
            data += _pad_string(arg)
        elif isinstance(arg, bytes):
            data += struct.pack(">i", len(arg))
            data += _pad_bytes(arg)

    return data


def decode_osc_message(data: bytes) -> tuple[str, list[Any]]:
    """Decode an OSC message.

    Args:
        data: Raw OSC message bytes

    Returns:
        Tuple of (address, [arguments])
    """
    # Find address (null-terminated, padded to 4 bytes)
    null_idx = data.index(b"\x00")
    address = data[:null_idx].decode("utf-8")
    offset = null_idx + 1
    offset += (4 - offset % 4) % 4

    # Find type tag string
    if offset >= len(data) or data[offset : offset + 1] != b",":
        return address, []

    null_idx = data.index(b"\x00", offset)
    type_tags = data[offset + 1 : null_idx].decode("utf-8")
    offset = null_idx + 1
    offset += (4 - offset % 4) % 4

    # Parse arguments
    args = []
    for tag in type_tags:
        if tag == "i":
            args.append(struct.unpack(">i", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "f":
            args.append(struct.unpack(">f", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "s":
            null_idx = data.index(b"\x00", offset)
            args.append(data[offset:null_idx].decode("utf-8"))
            offset = null_idx + 1
            offset += (4 - offset % 4) % 4
        elif tag == "b":
            size = struct.unpack(">i", data[offset : offset + 4])[0]
            offset += 4
            args.append(data[offset : offset + size])
            offset += size
            offset += (4 - offset % 4) % 4
        elif tag == "T":
            args.append(True)
        elif tag == "F":
            args.append(False)
        elif tag == "N":
            args.append(None)

    return address, args


@dataclass
class OSCHandler:
    """An OSC message handler.

    Attributes:
        pattern: OSC address pattern to match
        callback: Function to call when pattern matches
    """

    pattern: str
    callback: Callable[[str, list[Any]], None]

    def matches(self, address: str) -> bool:
        """Check if address matches this handler's pattern.

        Args:
            address: OSC address to check

        Returns:
            True if matches
        """
        # Simple pattern matching (exact match or wildcard)
        if self.pattern == address:
            return True
        if self.pattern.endswith("*"):
            prefix = self.pattern[:-1]
            return address.startswith(prefix)
        return False


@dataclass
class OSCServer:
    """UDP-based OSC server.

    Listens for incoming OSC messages and dispatches to registered handlers.

    Example:
        >>> server = OSCServer(port=DEFAULT_OSC_PORT)
        >>> server.register_handler("/test", lambda addr, args: print(args))
        >>> server.start()
        >>> # ... later ...
        >>> server.stop()
    """

    port: int = DEFAULT_OSC_PORT
    # Loopback by default: OSCController maps incoming messages straight onto
    # global writes and event signals, so a wildcard bind hands VM control to
    # anything on the network. Pass host="0.0.0.0" deliberately to accept
    # messages from other machines.
    host: str = DEFAULT_OSC_HOST
    handlers: list[OSCHandler] = field(default_factory=list)
    _socket: socket.socket | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)

    def register_handler(
        self, pattern: str, callback: Callable[[str, list[Any]], None]
    ) -> None:
        """Register a handler for an OSC address pattern.

        Args:
            pattern: OSC address pattern (e.g., "/numchuck/set/*")
            callback: Function to call with (address, args)
        """
        self.handlers.append(OSCHandler(pattern=pattern, callback=callback))

    def unregister_handler(self, pattern: str) -> bool:
        """Unregister a handler by pattern.

        Args:
            pattern: The pattern to unregister

        Returns:
            True if a handler was removed
        """
        for i, handler in enumerate(self.handlers):
            if handler.pattern == pattern:
                del self.handlers[i]
                return True
        return False

    def start(self) -> bool:
        """Start the OSC server.

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind((self.host, self.port))
            self._socket.settimeout(OSC_SOCKET_TIMEOUT)  # For clean shutdown
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True
        except OSError:
            if self._socket:
                self._socket.close()
                self._socket = None
            return False

    def stop(self) -> None:
        """Stop the OSC server."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=OSC_THREAD_SHUTDOWN_TIMEOUT)
            self._thread = None
        if self._socket:
            self._socket.close()
            self._socket = None

    def _run(self) -> None:
        """Main server loop (runs in background thread)."""
        while self._running and self._socket:
            try:
                data, addr = self._socket.recvfrom(65535)
                self._handle_message(data)
            except socket.timeout:
                continue
            except OSError:
                break

    def _handle_message(self, data: bytes) -> None:
        """Handle an incoming OSC message.

        Args:
            data: Raw message bytes
        """
        try:
            address, args = decode_osc_message(data)
            for handler in self.handlers:
                if handler.matches(address):
                    handler.callback(address, args)
        except (ValueError, IndexError, struct.error):
            # Invalid OSC message, ignore
            pass

    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


@dataclass
class OSCClient:
    """Simple OSC client for sending messages.

    Example:
        >>> client = OSCClient(host="localhost", port=DEFAULT_OSC_PORT)
        >>> client.send("/test", 1, 2.0, "hello")
    """

    host: str = "localhost"
    port: int = DEFAULT_OSC_PORT
    _socket: socket.socket | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Initialize the socket."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, address: str, *args: Any) -> bool:
        """Send an OSC message.

        Args:
            address: OSC address
            *args: Message arguments

        Returns:
            True if sent successfully
        """
        if not self._socket:
            return False

        try:
            data = encode_osc_message(address, *args)
            self._socket.sendto(data, (self.host, self.port))
            return True
        except OSError:
            return False

    def close(self) -> None:
        """Close the client socket."""
        if self._socket:
            self._socket.close()
            self._socket = None


def generate_osc_listener_code(
    port: int = 6449,
    global_mappings: dict[str, str] | None = None,
) -> str:
    """Generate ChucK code for OSC to global variable mapping.

    Uses ChucK's native OscIn for efficient real-time parameter control.
    This leverages the liblo library built into ChucK.

    Args:
        port: OSC port to listen on (default: 6449, ChucK's default)
        global_mappings: Dict mapping OSC addresses to global variable names
                        e.g., {"/tempo": "tempo", "/volume": "vol"}

    Returns:
        ChucK code string
    """
    mappings = global_mappings or {}

    lines = [
        "// OSC listener using ChucK's native liblo",
        f"// Listening on port {port}",
        "",
        "OscIn oin;",
        "OscMsg msg;",
        f"{port} => oin.port;",
        "",
    ]

    # Add address subscriptions
    if mappings:
        for addr in mappings.keys():
            lines.append(f'oin.addAddress("{addr}");')
    else:
        # Listen to all if no specific mappings
        lines.append('oin.addAddress("/numchuck/*");')

    lines.extend(
        [
            "",
            f'<<< "OSC listener started on port {port}" >>>;',
            "",
            "while (true) {",
            "    oin => now;",
            "    while (oin.recv(msg)) {",
        ]
    )

    if mappings:
        first = True
        for addr, global_name in mappings.items():
            condition = "if" if first else "else if"
            first = False
            lines.extend(
                [
                    f'        {condition} (msg.address == "{addr}") {{',
                    "            msg.getFloat(0) => global float " + global_name + ";",
                    "        }",
                ]
            )
    else:
        # Generic handler for /numchuck/set/* pattern
        lines.extend(
            [
                '        if (msg.address.find("/numchuck/set/") == 0) {',
                "            // Extract variable name from address",
                "            msg.address.substring(14) => string varname;",
                "            msg.getFloat(0) => float value;",
                '            <<< "OSC set:", varname, "=", value >>>;',
                "        }",
            ]
        )

    lines.extend(
        [
            "    }",
            "}",
        ]
    )

    return "\n".join(lines)


def generate_osc_sender_code(
    host: str = "localhost",
    port: int = DEFAULT_OSC_PORT,
) -> str:
    """Generate ChucK code for sending OSC messages.

    Args:
        host: Target host
        port: Target port

    Returns:
        ChucK code string with OscOut setup
    """
    return f'''// OSC sender using ChucK's native liblo
OscOut oout;
("{host}", {port}) => oout.dest;

// Example: send a float value
// oout.start("/test");
// 0.5 => oout.add;
// oout.send();

<<< "OSC sender ready:", "{host}:{port}" >>>;
'''


class OSCController:
    """Maps OSC messages to REPL commands.

    Standard OSC addresses:
        /numchuck/set/<varname> <value>  - Set a global variable
        /numchuck/get/<varname>          - Get a global variable (response sent back)
        /numchuck/event/<name>           - Signal an event
        /numchuck/broadcast/<name>       - Broadcast an event
        /numchuck/spork <code>           - Compile and run ChucK code
        /numchuck/remove <id>            - Remove a shred by ID
        /numchuck/clear                  - Clear all shreds
    """

    def __init__(
        self,
        on_set_global: Callable[[str, float], None] | None = None,
        on_get_global: Callable[[str], float | None] | None = None,
        on_signal_event: Callable[[str], None] | None = None,
        on_broadcast_event: Callable[[str], None] | None = None,
        on_spork: Callable[[str], None] | None = None,
        on_remove: Callable[[int], None] | None = None,
        on_clear: Callable[[], None] | None = None,
    ) -> None:
        """Initialize the controller.

        Args:
            on_set_global: Callback for setting globals
            on_get_global: Callback for getting globals
            on_signal_event: Callback for signaling events
            on_broadcast_event: Callback for broadcasting events
            on_spork: Callback for sporking code
            on_remove: Callback for removing shreds
            on_clear: Callback for clearing VM
        """
        self._on_set_global = on_set_global
        self._on_get_global = on_get_global
        self._on_signal_event = on_signal_event
        self._on_broadcast_event = on_broadcast_event
        self._on_spork = on_spork
        self._on_remove = on_remove
        self._on_clear = on_clear
        self._server: OSCServer | None = None
        self._response_client: OSCClient | None = None

    def register_with_server(self, server: OSCServer) -> None:
        """Register handlers with an OSC server.

        Args:
            server: The server to register with
        """
        self._server = server
        server.register_handler("/numchuck/set/*", self._handle_set)
        server.register_handler("/numchuck/get/*", self._handle_get)
        server.register_handler("/numchuck/event/*", self._handle_signal)
        server.register_handler("/numchuck/broadcast/*", self._handle_broadcast)
        server.register_handler("/numchuck/spork", self._handle_spork)
        server.register_handler("/numchuck/remove", self._handle_remove)
        server.register_handler("/numchuck/clear", self._handle_clear)

    def _handle_set(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/set/<varname> <value>."""
        if not self._on_set_global or not args:
            return

        # Extract variable name from address
        parts = address.split("/")
        if len(parts) < 4:
            return

        varname = parts[3]
        value = float(args[0]) if args else 0.0
        self._on_set_global(varname, value)

    def _handle_get(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/get/<varname>."""
        if not self._on_get_global:
            return

        parts = address.split("/")
        if len(parts) < 4:
            return

        varname = parts[3]
        value = self._on_get_global(varname)

        # Send response if we have a response port
        if value is not None and self._response_client:
            self._response_client.send(f"/numchuck/value/{varname}", value)

    def _handle_signal(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/event/<name>."""
        if not self._on_signal_event:
            return

        parts = address.split("/")
        if len(parts) < 4:
            return

        event_name = parts[3]
        self._on_signal_event(event_name)

    def _handle_broadcast(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/broadcast/<name>."""
        if not self._on_broadcast_event:
            return

        parts = address.split("/")
        if len(parts) < 4:
            return

        event_name = parts[3]
        self._on_broadcast_event(event_name)

    def _handle_spork(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/spork <code>."""
        if not self._on_spork or not args:
            return

        code = str(args[0])
        self._on_spork(code)

    def _handle_remove(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/remove <id>."""
        if not self._on_remove or not args:
            return

        shred_id = int(args[0])
        self._on_remove(shred_id)

    def _handle_clear(self, address: str, args: list[Any]) -> None:
        """Handle /numchuck/clear."""
        if self._on_clear:
            self._on_clear()

    def set_response_client(self, client: OSCClient) -> None:
        """Set client for sending responses.

        Args:
            client: OSC client to use for responses
        """
        self._response_client = client
