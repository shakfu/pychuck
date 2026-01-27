"""Tests for web server module."""

import pytest
import time
from unittest.mock import MagicMock, patch

# Skip all tests if web module not available
pytest.importorskip("numchuck._web")


class TestWebModuleImport:
    """Tests for web module availability."""

    def test_web_module_available(self):
        """Test that web module is available."""
        from numchuck.web import WEB_AVAILABLE

        assert WEB_AVAILABLE is True

    def test_web_server_class_exists(self):
        """Test WebChuckServer class can be imported."""
        from numchuck.web import WebChuckServer

        assert WebChuckServer is not None


class TestWebServer:
    """Tests for WebChuckServer class."""

    def test_server_init(self):
        """Test server initialization."""
        import gc
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        server = None
        try:
            server = WebChuckServer(chuck, port=8082)

            assert server.port == 8082
            assert server.is_running is False
            assert server.url == "http://localhost:8082"
        finally:
            if server is not None:
                server.stop()  # Break reference cycles
            chuck.close()
            gc.collect()

    def test_server_start_stop(self):
        """Test server start and stop."""
        import gc
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        server = WebChuckServer(chuck, port=8083)

        try:
            server.start()
            assert server.is_running is True

            # Give server time to initialize
            time.sleep(0.1)

            server.stop()
            assert server.is_running is False
        finally:
            if server.is_running:
                server.stop()
            chuck.close()
            gc.collect()

    def test_server_context_manager(self):
        """Test server as context manager."""
        import gc
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            with WebChuckServer(chuck, port=8084) as server:
                assert server.is_running is True
                time.sleep(0.1)

            assert server.is_running is False
        finally:
            chuck.close()
            gc.collect()

    def test_server_http_response(self):
        """Test server serves HTTP content."""
        import gc
        import urllib.request
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            with WebChuckServer(chuck, port=8085) as server:
                time.sleep(0.2)  # Give server time to start

                response = urllib.request.urlopen("http://localhost:8085/")
                html = response.read().decode("utf-8")

                assert len(html) > 0
                assert "numchuck" in html
        finally:
            chuck.close()
            gc.collect()

    def test_server_api_status(self):
        """Test server API status endpoint."""
        import gc
        import json
        import urllib.request
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            with WebChuckServer(chuck, port=8086) as server:
                time.sleep(0.2)

                req = urllib.request.Request(
                    "http://localhost:8086/api/status",
                    method="GET",
                )
                response = urllib.request.urlopen(req)
                data = json.loads(response.read().decode("utf-8"))

                assert "shreds" in data
                assert "now" in data
                assert isinstance(data["shreds"], list)
        finally:
            chuck.close()
            gc.collect()

    def test_server_api_compile(self):
        """Test server API compile endpoint."""
        import gc
        import json
        import urllib.request
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            with WebChuckServer(chuck, port=8087) as server:
                time.sleep(0.2)

                # Compile simple code
                code = "SinOsc s => dac; 100::ms => now;"
                req = urllib.request.Request(
                    "http://localhost:8087/api/compile",
                    data=json.dumps({"code": code}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                response = urllib.request.urlopen(req)
                data = json.loads(response.read().decode("utf-8"))

                assert data["success"] is True
                assert "shred_ids" in data
                assert len(data["shred_ids"]) > 0
        finally:
            chuck.close()
            gc.collect()


class TestLowLevelWebServer:
    """Tests for low-level _web module."""

    def test_raw_web_server(self):
        """Test raw WebServer class from _web module."""
        import gc
        from numchuck._web import WebServer

        server = WebServer()
        try:
            assert server.port == 8080  # default
            assert server.is_running is False

            server.port = 9000
            assert server.port == 9000
        finally:
            del server
            gc.collect()

    def test_raw_server_start_stop(self):
        """Test raw server start/stop without API handler."""
        import gc
        from numchuck._web import WebServer

        server = WebServer()
        server.port = 8088

        try:
            result = server.start()
            assert result is True
            assert server.is_running is True

            time.sleep(0.1)

            server.stop()
            assert server.is_running is False
        finally:
            if server.is_running:
                server.stop()
            del server
            gc.collect()


class TestAudioMeters:
    """Tests for audio metering functionality."""

    def test_get_audio_meters_exists(self):
        """Test that get_audio_meters function exists."""
        from numchuck._numchuck import get_audio_meters

        assert callable(get_audio_meters)

    def test_get_audio_meters_returns_dict(self):
        """Test that get_audio_meters returns a dict with expected keys."""
        from numchuck._numchuck import get_audio_meters

        meters = get_audio_meters()

        assert isinstance(meters, dict)
        assert "rms_left" in meters
        assert "rms_right" in meters
        assert "peak_left" in meters
        assert "peak_right" in meters

    def test_get_audio_meters_values_are_floats(self):
        """Test that meter values are floats."""
        from numchuck._numchuck import get_audio_meters

        meters = get_audio_meters()

        assert isinstance(meters["rms_left"], float)
        assert isinstance(meters["rms_right"], float)
        assert isinstance(meters["peak_left"], float)
        assert isinstance(meters["peak_right"], float)

    def test_get_audio_meters_values_non_negative(self):
        """Test that meter values are non-negative."""
        from numchuck._numchuck import get_audio_meters

        meters = get_audio_meters()

        assert meters["rms_left"] >= 0.0
        assert meters["rms_right"] >= 0.0
        assert meters["peak_left"] >= 0.0
        assert meters["peak_right"] >= 0.0

    def test_is_audio_running_exists(self):
        """Test that is_audio_running function exists."""
        from numchuck._numchuck import is_audio_running

        assert callable(is_audio_running)

    def test_is_audio_running_returns_bool(self):
        """Test that is_audio_running returns a boolean."""
        from numchuck._numchuck import is_audio_running

        result = is_audio_running()
        assert isinstance(result, bool)


class TestGlobalsSync:
    """Tests for globals synchronization via WebSocket."""

    def test_globals_api_endpoint(self):
        """Test the /api/globals REST endpoint."""
        import gc
        import json
        import urllib.request
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            with WebChuckServer(chuck, port=8089) as server:
                time.sleep(0.2)

                # First compile code with global variables
                code = "global float GAIN; 0.5 => GAIN;"
                req = urllib.request.Request(
                    "http://localhost:8089/api/compile",
                    data=json.dumps({"code": code}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req)

                # Run a few frames to process the code
                time.sleep(0.1)

                # Now fetch globals
                req = urllib.request.Request(
                    "http://localhost:8089/api/globals",
                    method="GET",
                )
                response = urllib.request.urlopen(req)
                data = json.loads(response.read().decode("utf-8"))

                assert "globals" in data
                assert isinstance(data["globals"], list)
        finally:
            chuck.close()
            gc.collect()

    def test_server_has_broadcast_thread(self):
        """Test that server starts broadcast thread when running."""
        import gc
        from numchuck import Chuck
        from numchuck.web import WebChuckServer

        chuck = Chuck()
        try:
            server = WebChuckServer(chuck, port=8090)
            server.start()
            time.sleep(0.2)

            # Check that broadcast thread exists
            assert server._broadcast_thread is not None
            assert server._broadcast_thread.is_alive()

            server.stop()
            time.sleep(0.2)

            # Thread should be stopped
            assert server._broadcast_thread is None or not server._broadcast_thread.is_alive()
        finally:
            if server.is_running:
                server.stop()
            chuck.close()
            gc.collect()

    def test_meter_broadcast_format(self):
        """Test that audio_meters message format is correct."""
        import gc
        import json
        from numchuck import Chuck
        from numchuck.web import WebChuckServer
        from numchuck._numchuck import get_audio_meters

        chuck = Chuck()
        try:
            # Get current meter values
            meters = get_audio_meters()

            # Create expected message format
            msg = {
                "type": "audio_meters",
                "rms_left": meters["rms_left"],
                "rms_right": meters["rms_right"],
                "peak_left": meters["peak_left"],
                "peak_right": meters["peak_right"],
            }

            # Verify it's valid JSON
            json_str = json.dumps(msg)
            parsed = json.loads(json_str)

            assert parsed["type"] == "audio_meters"
            assert "rms_left" in parsed
            assert "rms_right" in parsed
            assert "peak_left" in parsed
            assert "peak_right" in parsed
        finally:
            chuck.close()
            gc.collect()
