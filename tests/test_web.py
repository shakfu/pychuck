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
