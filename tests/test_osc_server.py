"""Tests for OSC server functionality."""

from __future__ import annotations

import socket
import time

import pytest

from numchuck.osc import (
    OSCClient,
    OSCController,
    OSCHandler,
    OSCServer,
    decode_osc_message,
    encode_osc_message,
    generate_osc_listener_code,
    generate_osc_sender_code,
)


class TestOSCEncoding:
    """Tests for OSC message encoding."""

    def test_encode_simple_message(self) -> None:
        """Test encoding a simple OSC message."""
        data = encode_osc_message("/test")

        # Should start with address
        assert data.startswith(b"/test\x00")
        # Should have comma for type tags
        assert b"," in data

    def test_encode_int_argument(self) -> None:
        """Test encoding message with int argument."""
        data = encode_osc_message("/test", 42)

        # Type tag should include 'i'
        decoded = decode_osc_message(data)
        assert decoded[0] == "/test"
        assert decoded[1] == [42]

    def test_encode_float_argument(self) -> None:
        """Test encoding message with float argument."""
        data = encode_osc_message("/test", 3.14)

        decoded = decode_osc_message(data)
        assert decoded[0] == "/test"
        assert len(decoded[1]) == 1
        assert abs(decoded[1][0] - 3.14) < 0.01

    def test_encode_string_argument(self) -> None:
        """Test encoding message with string argument."""
        data = encode_osc_message("/test", "hello")

        decoded = decode_osc_message(data)
        assert decoded[0] == "/test"
        assert decoded[1] == ["hello"]

    def test_encode_multiple_arguments(self) -> None:
        """Test encoding message with multiple arguments."""
        data = encode_osc_message("/test", 1, 2.0, "three")

        decoded = decode_osc_message(data)
        assert decoded[0] == "/test"
        assert len(decoded[1]) == 3
        assert decoded[1][0] == 1
        assert abs(decoded[1][1] - 2.0) < 0.01
        assert decoded[1][2] == "three"

    def test_encode_bytes_argument(self) -> None:
        """Test encoding message with bytes argument."""
        data = encode_osc_message("/test", b"binary")

        decoded = decode_osc_message(data)
        assert decoded[0] == "/test"
        assert decoded[1] == [b"binary"]

    def test_encode_unsupported_type_raises(self) -> None:
        """Test that encoding unsupported type raises error."""
        with pytest.raises(ValueError, match="Unsupported OSC type"):
            encode_osc_message("/test", object())


class TestOSCDecoding:
    """Tests for OSC message decoding."""

    def test_decode_simple_message(self) -> None:
        """Test decoding a simple message."""
        data = encode_osc_message("/test")

        address, args = decode_osc_message(data)

        assert address == "/test"
        assert args == []

    def test_decode_with_arguments(self) -> None:
        """Test decoding message with arguments."""
        data = encode_osc_message("/set/volume", 0.75)

        address, args = decode_osc_message(data)

        assert address == "/set/volume"
        assert len(args) == 1
        assert abs(args[0] - 0.75) < 0.01

    def test_decode_complex_address(self) -> None:
        """Test decoding complex address patterns."""
        data = encode_osc_message("/numchuck/set/tempo")

        address, args = decode_osc_message(data)

        assert address == "/numchuck/set/tempo"


class TestOSCHandler:
    """Tests for OSCHandler class."""

    def test_exact_match(self) -> None:
        """Test exact address matching."""
        handler = OSCHandler(pattern="/test", callback=lambda a, b: None)

        assert handler.matches("/test") is True
        assert handler.matches("/test2") is False
        assert handler.matches("/other") is False

    def test_wildcard_match(self) -> None:
        """Test wildcard pattern matching."""
        handler = OSCHandler(pattern="/numchuck/*", callback=lambda a, b: None)

        assert handler.matches("/numchuck/set") is True
        assert handler.matches("/numchuck/get") is True
        assert handler.matches("/other/path") is False


class TestOSCServer:
    """Tests for OSCServer class."""

    def test_server_creation(self) -> None:
        """Test creating an OSC server."""
        server = OSCServer(port=9999)

        assert server.port == 9999
        assert not server.is_running

    def test_register_handler(self) -> None:
        """Test registering a handler."""
        server = OSCServer()
        received = []

        server.register_handler("/test", lambda a, args: received.append((a, args)))

        assert len(server.handlers) == 1

    def test_unregister_handler(self) -> None:
        """Test unregistering a handler."""
        server = OSCServer()
        server.register_handler("/test", lambda a, args: None)

        result = server.unregister_handler("/test")

        assert result is True
        assert len(server.handlers) == 0

    def test_unregister_nonexistent(self) -> None:
        """Test unregistering nonexistent handler."""
        server = OSCServer()

        result = server.unregister_handler("/test")

        assert result is False

    def test_start_stop(self) -> None:
        """Test starting and stopping server."""
        server = OSCServer(port=9998)

        assert server.start() is True
        assert server.is_running is True

        server.stop()
        assert server.is_running is False

    def test_start_already_running(self) -> None:
        """Test starting already running server."""
        server = OSCServer(port=9997)
        server.start()

        try:
            result = server.start()
            assert result is True  # Should return True, not start again
        finally:
            server.stop()

    def test_receive_message(self) -> None:
        """Test receiving an OSC message."""
        server = OSCServer(port=9996)
        received = []

        server.register_handler("/test", lambda a, args: received.append((a, args)))
        server.start()

        try:
            # Send a message
            client = OSCClient(host="localhost", port=9996)
            client.send("/test", 42)
            client.close()

            # Wait for message to be processed
            time.sleep(0.2)

            assert len(received) == 1
            assert received[0][0] == "/test"
            assert received[0][1] == [42]
        finally:
            server.stop()


class TestOSCClient:
    """Tests for OSCClient class."""

    def test_client_creation(self) -> None:
        """Test creating an OSC client."""
        client = OSCClient(host="localhost", port=9000)

        assert client.host == "localhost"
        assert client.port == 9000

    def test_send_message(self) -> None:
        """Test sending a message (just verifies no error)."""
        client = OSCClient(host="localhost", port=9995)

        # This should not raise even if nothing is listening
        result = client.send("/test", 1)

        # UDP send returns True even if nothing receives
        assert result is True

        client.close()

    def test_close_client(self) -> None:
        """Test closing client."""
        client = OSCClient()

        client.close()

        # Sending after close should fail
        assert client.send("/test") is False


class TestOSCController:
    """Tests for OSCController class."""

    def test_controller_creation(self) -> None:
        """Test creating a controller."""
        controller = OSCController()

        # Should not raise
        assert controller is not None

    def test_register_with_server(self) -> None:
        """Test registering controller with server."""
        controller = OSCController()
        server = OSCServer()

        controller.register_with_server(server)

        # Should have registered multiple handlers
        assert len(server.handlers) > 0

    def test_set_global_callback(self) -> None:
        """Test set global callback is called."""
        received = []
        controller = OSCController(
            on_set_global=lambda name, val: received.append((name, val))
        )
        server = OSCServer(port=9994)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9994)
            client.send("/numchuck/set/tempo", 120.0)
            client.close()

            time.sleep(0.2)

            assert len(received) == 1
            assert received[0][0] == "tempo"
            assert abs(received[0][1] - 120.0) < 0.01
        finally:
            server.stop()

    def test_signal_event_callback(self) -> None:
        """Test signal event callback is called."""
        received = []
        controller = OSCController(
            on_signal_event=lambda name: received.append(name)
        )
        server = OSCServer(port=9993)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9993)
            client.send("/numchuck/event/beat")
            client.close()

            time.sleep(0.2)

            assert "beat" in received
        finally:
            server.stop()

    def test_broadcast_event_callback(self) -> None:
        """Test broadcast event callback is called."""
        received = []
        controller = OSCController(
            on_broadcast_event=lambda name: received.append(name)
        )
        server = OSCServer(port=9992)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9992)
            client.send("/numchuck/broadcast/sync")
            client.close()

            time.sleep(0.2)

            assert "sync" in received
        finally:
            server.stop()

    def test_spork_callback(self) -> None:
        """Test spork callback is called."""
        received = []
        controller = OSCController(
            on_spork=lambda code: received.append(code)
        )
        server = OSCServer(port=9991)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9991)
            client.send("/numchuck/spork", "SinOsc s => dac;")
            client.close()

            time.sleep(0.2)

            assert "SinOsc s => dac;" in received
        finally:
            server.stop()

    def test_remove_callback(self) -> None:
        """Test remove callback is called."""
        received = []
        controller = OSCController(
            on_remove=lambda id: received.append(id)
        )
        server = OSCServer(port=9990)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9990)
            client.send("/numchuck/remove", 1)
            client.close()

            time.sleep(0.2)

            assert 1 in received
        finally:
            server.stop()

    def test_clear_callback(self) -> None:
        """Test clear callback is called."""
        received = []
        controller = OSCController(
            on_clear=lambda: received.append("cleared")
        )
        server = OSCServer(port=9989)
        controller.register_with_server(server)
        server.start()

        try:
            client = OSCClient(host="localhost", port=9989)
            client.send("/numchuck/clear")
            client.close()

            time.sleep(0.2)

            assert "cleared" in received
        finally:
            server.stop()


class TestGenerateChucKOSCCode:
    """Tests for ChucK OSC code generation (using native liblo)."""

    def test_generate_listener_default(self) -> None:
        """Test generating default OSC listener code."""
        code = generate_osc_listener_code()

        assert "OscIn" in code
        assert "6449" in code  # Default ChucK OSC port
        assert "liblo" in code

    def test_generate_listener_custom_port(self) -> None:
        """Test generating listener with custom port."""
        code = generate_osc_listener_code(port=9000)

        assert "9000" in code
        assert "9000 => oin.port" in code

    def test_generate_listener_with_mappings(self) -> None:
        """Test generating listener with address mappings."""
        mappings = {
            "/tempo": "tempo",
            "/volume": "vol",
        }
        code = generate_osc_listener_code(global_mappings=mappings)

        assert "/tempo" in code
        assert "/volume" in code
        assert "tempo" in code
        assert "vol" in code
        assert "addAddress" in code

    def test_generate_listener_generic_handler(self) -> None:
        """Test generating listener with generic handler."""
        code = generate_osc_listener_code()

        assert "/numchuck/*" in code or "/numchuck/set/" in code

    def test_generate_sender_code(self) -> None:
        """Test generating OSC sender code."""
        code = generate_osc_sender_code(host="192.168.1.100", port=8000)

        assert "OscOut" in code
        assert "192.168.1.100" in code
        assert "8000" in code

    def test_generate_sender_default(self) -> None:
        """Test generating sender with defaults."""
        code = generate_osc_sender_code()

        assert "localhost" in code
        assert "9000" in code


class TestCommandParserOSCCommands:
    """Tests for OSC command parsing."""

    def test_parse_osc_start(self) -> None:
        """Test parsing 'osc start' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("osc start")

        assert cmd is not None
        assert cmd.type == "osc_start"
        assert cmd.args["port"] == 9000  # Default port

    def test_parse_osc_start_with_port(self) -> None:
        """Test parsing 'osc start port' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("osc start 8000")

        assert cmd is not None
        assert cmd.type == "osc_start"
        assert cmd.args["port"] == 8000

    def test_parse_osc_stop(self) -> None:
        """Test parsing 'osc stop' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("osc stop")

        assert cmd is not None
        assert cmd.type == "osc_stop"

    def test_parse_osc_status(self) -> None:
        """Test parsing 'osc status' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("osc status")

        assert cmd is not None
        assert cmd.type == "osc_status"
