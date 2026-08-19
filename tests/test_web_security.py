"""Tests for the web IDE's trust boundary and its teardown under load.

The web server exposes arbitrary ChucK execution, so these cover the three
things that keep that from being reachable by anyone but the operator: the bind
address, the auth token, and the Origin/Host check. The last class covers
stopping the server while requests are in flight, which used to deadlock the
interpreter outright.
"""

from __future__ import annotations

import base64
import gc
import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request

import pytest

from numchuck import Chuck
from numchuck.web import WEB_AVAILABLE, WebChuckServer, is_loopback_host

pytestmark = pytest.mark.skipif(not WEB_AVAILABLE, reason="web module not built")


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _request(
    target: "int | WebChuckServer",
    path: str = "/api/status",
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> tuple[int, bytes]:
    """Issue a request, returning (status, body) even for error statuses.

    Pass a server to authenticate the way a real client does; pass a bare port
    to exercise the unauthenticated path.
    """
    headers = dict(headers or {})
    if isinstance(target, int):
        port = target
    else:
        port = target.port
        if target.auth_token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {target.auth_token}"

    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        method=method,
        data=body.encode() if body is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.fixture
def chuck():
    instance = Chuck()
    yield instance
    instance.close()
    gc.collect()


class _RunningServer:
    """Start a server for the duration of a `with` block."""

    def __init__(self, chuck, **kwargs):
        self.server = WebChuckServer(chuck, port=_free_port(), **kwargs)

    def __enter__(self) -> WebChuckServer:
        self.server.start()
        time.sleep(0.2)
        return self.server

    def __exit__(self, *exc) -> None:
        self.server.stop()
        gc.collect()


class TestBindAddress:
    """The server must not reach the network unless asked to."""

    def test_default_host_is_loopback(self, chuck):
        server = WebChuckServer(chuck, port=_free_port())
        try:
            assert server.host == "127.0.0.1"
            assert is_loopback_host(server.host)
        finally:
            server.stop()

    def test_url_reports_the_bound_address(self, chuck):
        server = WebChuckServer(chuck, port=8099)
        try:
            assert server.url.startswith("http://127.0.0.1:8099/")
            assert f"token={server.auth_token}" in server.url
        finally:
            server.stop()

    def test_url_without_auth_is_bare(self, chuck):
        server = WebChuckServer(chuck, port=8099, auth_token="")
        try:
            assert server.url == "http://127.0.0.1:8099"
        finally:
            server.stop()

    def test_wildcard_bind_advertises_a_reachable_url(self, chuck):
        # 0.0.0.0 is not an address a browser can visit, so the URL shown has
        # to name one that works from the host itself.
        server = WebChuckServer(chuck, port=8099, host="0.0.0.0")
        try:
            assert server.url.startswith("http://localhost:8099/")
        finally:
            server.stop()

    @pytest.mark.parametrize(
        "host,loopback",
        [
            ("127.0.0.1", True),
            ("localhost", True),
            ("::1", True),
            ("127.0.0.2", True),
            ("0.0.0.0", False),
            ("192.168.1.5", False),
            ("::", False),
            ("example.com", False),
        ],
    )
    def test_loopback_classification(self, host, loopback):
        assert is_loopback_host(host) is loopback


class TestAuthToken:
    """A server anyone can reach must demand a token."""

    def test_loopback_bind_is_tokenized_too(self, chuck):
        """Loopback is not a private channel on a shared machine.

        The origin check only constrains requests that carry an Origin, and a
        local process sends none -- so without a token any other user on the
        box could POST to /api/compile.
        """
        server = WebChuckServer(chuck, port=_free_port())
        try:
            assert len(server.auth_token) >= 20
            assert f"token={server.auth_token}" in server.url
        finally:
            server.stop()

    def test_local_client_cannot_compile_without_the_token(self, chuck):
        """The concrete hole the loopback token closes."""
        with _RunningServer(chuck) as server:
            status, _ = _request(
                server.port,          # bare port: no Authorization header
                path="/api/compile",
                method="POST",
                body=json.dumps({"code": "SinOsc s => dac; 1::samp => now;"}),
            )
            assert status == 401

    def test_non_loopback_bind_mints_a_token(self, chuck):
        # The point is that this cannot be forgotten: binding wide without
        # asking for auth still gets auth.
        server = WebChuckServer(chuck, port=_free_port(), host="0.0.0.0")
        try:
            assert len(server.auth_token) >= 20
            assert f"token={server.auth_token}" in server.url
        finally:
            server.stop()

    def test_explicit_token_is_used_verbatim(self, chuck):
        server = WebChuckServer(chuck, port=_free_port(), auth_token="s3cret")
        try:
            assert server.auth_token == "s3cret"
        finally:
            server.stop()

    def test_auth_can_be_waived_explicitly(self, chuck):
        server = WebChuckServer(chuck, port=_free_port(), host="0.0.0.0", auth_token="")
        try:
            assert server.auth_token == ""
        finally:
            server.stop()

    def test_request_without_token_is_refused(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(server.port)
            assert status == 401

    def test_request_with_wrong_token_is_refused(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(
                server.port, headers={"Authorization": "Bearer wrong"}
            )
            assert status == 401

    def test_bearer_header_is_accepted(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(
                server.port, headers={"Authorization": "Bearer s3cret"}
            )
            assert status == 200

    def test_query_parameter_is_accepted(self, chuck):
        # Browsers cannot set headers on a WebSocket handshake, so the token
        # has to be accepted from the query string too.
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(server.port, path="/api/status?token=s3cret")
            assert status == 200

    def test_compile_endpoint_is_behind_auth(self, chuck):
        """The endpoint that runs code is not an exception."""
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(
                server.port,
                path="/api/compile",
                method="POST",
                body=json.dumps({"code": "SinOsc s => dac; 1::samp => now;"}),
            )
            assert status == 401


class TestOriginCheck:
    """Cross-site requests are refused even when they reach loopback."""

    def test_foreign_origin_is_refused(self, chuck):
        with _RunningServer(chuck) as server:
            status, _ = _request(
                server.port, headers={"Origin": "http://evil.example"}
            )
            assert status == 403

    def test_foreign_origin_refused_on_compile(self, chuck):
        with _RunningServer(chuck) as server:
            status, _ = _request(
                server.port,
                path="/api/compile",
                method="POST",
                headers={"Origin": "https://evil.example", "Content-Type": "application/json"},
                body=json.dumps({"code": "SinOsc s => dac; 1::samp => now;"}),
            )
            assert status == 403

    def test_matching_origin_is_allowed(self, chuck):
        with _RunningServer(chuck) as server:
            status, _ = _request(
                server,
                headers={"Origin": f"http://127.0.0.1:{server.port}"},
            )
            assert status == 200

    def test_absent_origin_is_allowed(self, chuck):
        """curl and other non-browser clients send no Origin.

        They still need the token; the origin check is not what stops them.
        """
        with _RunningServer(chuck) as server:
            status, _ = _request(server)
            assert status == 200

    def test_null_origin_is_refused(self, chuck):
        """Sandboxed iframes and file:// pages send Origin: null."""
        with _RunningServer(chuck) as server:
            status, _ = _request(server.port, headers={"Origin": "null"})
            assert status == 403

    def test_static_files_are_not_readable_cross_origin(self, chuck):
        with _RunningServer(chuck) as server:
            status, _ = _request(
                server.port, path="/", headers={"Origin": "http://evil.example"}
            )
            assert status == 403


class TestApiStatusCodes:
    """Failures are reported as failures, not as 200 with an error body."""

    def test_unknown_endpoint_is_404(self, chuck):
        with _RunningServer(chuck) as server:
            status, body = _request(server, path="/api/nope")
            assert status == 404
            assert "error" in json.loads(body)

    def test_malformed_shred_id_is_400_not_500(self, chuck):
        # int(...) on the path segment used to raise ValueError and answer 500.
        with _RunningServer(chuck) as server:
            status, body = _request(
                server, path="/api/shred/not-a-number", method="DELETE"
            )
            assert status == 400
            assert "Invalid shred id" in json.loads(body)["error"]

    def test_compile_without_code_is_400(self, chuck):
        with _RunningServer(chuck) as server:
            status, body = _request(
                server, path="/api/compile", method="POST", body="{}"
            )
            assert status == 400
            assert json.loads(body)["success"] is False

    def test_successful_compile_is_200(self, chuck):
        with _RunningServer(chuck) as server:
            status, body = _request(
                server,
                path="/api/compile",
                method="POST",
                body=json.dumps({"code": "SinOsc s => dac; 1::samp => now;"}),
            )
            assert status == 200
            payload = json.loads(body)
            assert payload["success"] is True
            assert payload["shred_ids"]

    def test_path_traversal_is_refused(self, chuck):
        with _RunningServer(chuck) as server:
            status, _ = _request(server.port, path="/../../../../etc/passwd")
            assert status in (400, 403, 404)

    def test_error_bodies_are_valid_json(self, chuck):
        """Error text is escaped, not concatenated into a JSON literal."""
        with _RunningServer(chuck) as server:
            for path in ("/api/nope", '/api/shred/"quoted"'):
                status, body = _request(server, path=path, method="DELETE")
                assert status >= 400
                json.loads(body)  # must parse


class TestCaching:
    """Nothing this server sends may be cached.

    Loopback ports are shared ground: every local tool wants 8080, so a
    response cached for a *different* server on that origin can be served in
    place of this one. Without a Cache-Control header browsers fall back to
    heuristic caching and do exactly that -- observed as Safari showing a
    llama.cpp UI on numchuck's port. VM state is not cacheable either.
    """

    @pytest.mark.parametrize(
        "path,method,authenticate",
        [
            ("/", "GET", False),                    # the document
            ("/js/xterm.min.js", "GET", False),     # a static asset
            ("/api/status", "GET", True),           # a JSON response
            ("/api/status", "GET", False),          # the 401
            ("/api/nope", "GET", True),             # the 404
        ],
        ids=["document", "asset", "json", "unauthorized", "not-found"],
    )
    def test_responses_are_not_cacheable(self, chuck, path, method, authenticate):
        with _RunningServer(chuck) as server:
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}{path}", method=method
            )
            if authenticate and server.auth_token:
                req.add_header("Authorization", f"Bearer {server.auth_token}")
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    headers = resp.headers
            except urllib.error.HTTPError as e:
                headers = e.headers

            cache_control = headers.get("Cache-Control", "")
            assert "no-store" in cache_control, (
                f"{path} answered with Cache-Control: {cache_control!r}"
            )

    def test_cross_origin_refusal_is_not_cacheable(self, chuck):
        with _RunningServer(chuck) as server:
            req = urllib.request.Request(
                f"http://127.0.0.1:{server.port}/",
                headers={"Origin": "http://evil.example"},
            )
            try:
                urllib.request.urlopen(req, timeout=5)
                headers = None
            except urllib.error.HTTPError as e:
                headers = e.headers
            assert headers is not None
            assert "no-store" in headers.get("Cache-Control", "")


class TestTeardownUnderLoad:
    """Stopping the server must not wedge the interpreter.

    stop() joins the server thread; that thread blocks acquiring the GIL before
    every API callback. Joining with the GIL held was an unrecoverable deadlock
    -- no other Python thread ran, so not even a watchdog could notice.
    """

    def test_stop_returns_while_requests_are_in_flight(self, chuck):
        server = WebChuckServer(chuck, port=_free_port())
        server.start()
        time.sleep(0.2)

        stop = threading.Event()
        # Contend for the GIL: without a second runnable thread the race window
        # is narrow enough that a single-threaded test passes either way.
        def burn() -> None:
            x = 0
            while not stop.is_set():
                x += 1

        def hammer() -> None:
            while not stop.is_set():
                try:
                    _request(server.port)
                except OSError:
                    pass

        workers = [threading.Thread(target=burn, daemon=True)]
        workers += [threading.Thread(target=hammer, daemon=True) for _ in range(3)]
        for t in workers:
            t.start()
        time.sleep(0.3)

        try:
            started = time.time()
            server.stop()
            elapsed = time.time() - started
        finally:
            stop.set()
            for t in workers:
                t.join(timeout=2)

        assert server.is_running is False
        assert elapsed < 20, f"stop() took {elapsed:.1f}s"

    def test_repeated_start_stop_cycles(self, chuck):
        """The server survives being cycled, and does not leak its thread."""
        before = threading.active_count()
        for _ in range(5):
            with _RunningServer(chuck) as server:
                status, _ = _request(server)
                assert status == 200
        time.sleep(0.5)
        # Allow slack for daemon threads the runtime keeps around.
        assert threading.active_count() <= before + 2

    def test_two_servers_coexist(self, chuck):
        """Each instance handles its own connections.

        The event handler used to dispatch through a single process-wide
        pointer, so a second server displaced the first.
        """
        with _RunningServer(chuck, auth_token="one") as first:
            with _RunningServer(chuck, auth_token="two") as second:
                assert _request(
                    first.port, headers={"Authorization": "Bearer one"}
                )[0] == 200
                assert _request(
                    second.port, headers={"Authorization": "Bearer two"}
                )[0] == 200
                # Tokens are per-instance, not shared through a global.
                assert _request(
                    first.port, headers={"Authorization": "Bearer two"}
                )[0] == 401

def _ws_handshake(
    target: "int | WebChuckServer", path: str | None = None, origin: str | None = None
) -> int:
    """Perform a raw WebSocket upgrade, returning the HTTP status.

    Done by hand because a browser cannot put headers on a WebSocket handshake,
    so this is the one path where the token has to travel in the query string.
    """
    if isinstance(target, int):
        port = target
        path = path or "/ws"
    else:
        port = target.port
        if path is None:
            path = "/ws"
            if target.auth_token:
                path += f"?token={target.auth_token}"

    key = base64.b64encode(os.urandom(16)).decode()
    lines = [
        f"GET {path} HTTP/1.1",
        f"Host: 127.0.0.1:{port}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
    ]
    if origin is not None:
        lines.append(f"Origin: {origin}")
    with socket.create_connection(("127.0.0.1", port), timeout=5) as sock:
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode())
        status_line = sock.recv(256).split(b"\r\n")[0].decode()
    return int(status_line.split()[1])


class TestWebSocketUpgrade:
    """The upgrade is the path that matters most.

    WebSockets are not covered by the same-origin policy, so without these
    checks any page the user visited could open a socket to the IDE on their
    own machine and drive the REPL.
    """

    def test_upgrade_succeeds_with_the_generated_token(self, chuck):
        with _RunningServer(chuck) as server:
            assert _ws_handshake(server) == 101

    def test_upgrade_refused_on_loopback_without_the_token(self, chuck):
        """Loopback is tokenized, so a bare handshake is refused there too."""
        with _RunningServer(chuck) as server:
            assert _ws_handshake(server.port) == 401

    def test_upgrade_refused_without_the_token(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            assert _ws_handshake(server.port) == 401

    def test_upgrade_refused_with_the_wrong_token(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            assert _ws_handshake(server.port, "/ws?token=nope") == 401

    def test_upgrade_accepts_the_query_token(self, chuck):
        with _RunningServer(chuck, auth_token="s3cret") as server:
            assert _ws_handshake(server.port, "/ws?token=s3cret") == 101

    def test_upgrade_refused_from_a_foreign_origin(self, chuck):
        """Cross-site WebSocket hijacking, the reason the origin check exists."""
        with _RunningServer(chuck) as server:
            assert _ws_handshake(server, origin="http://evil.example") == 403

    def test_foreign_origin_refused_even_with_a_valid_token(self, chuck):
        """A stolen or guessed token must not be enough from another site."""
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status = _ws_handshake(
                server.port, "/ws?token=s3cret", origin="http://evil.example"
            )
            assert status == 403

    def test_own_origin_is_accepted(self, chuck):
        with _RunningServer(chuck) as server:
            status = _ws_handshake(
                server, origin=f"http://127.0.0.1:{server.port}"
            )
            assert status == 101


class TestBundledFrontendSendsTheToken:
    """The shipped UI has to satisfy the auth contract the server enforces.

    Enforcing a token server-side while the bundled page never sends one would
    leave the IDE working on loopback and broken in exactly the configuration
    that requires the token -- a failure nothing else here would catch, since
    every other test drives the API directly rather than through the page.

    These assert on the shipped asset because there is no JS runtime in the test
    environment; they check the mechanisms, not the formatting.
    """

    @pytest.fixture
    def page(self) -> str:
        from numchuck.web import WebChuckServer

        index = WebChuckServer._DEFAULT_STATIC_DIR / "index.html"
        assert index.is_file(), f"bundled UI missing at {index}"
        return index.read_text(encoding="utf-8")

    def test_page_is_served_without_a_token(self, chuck):
        """The page must load unauthenticated, or it can never read its token."""
        with _RunningServer(chuck, auth_token="s3cret") as server:
            status, _ = _request(server.port, path="/")
            assert status == 200

    def test_frontend_reads_the_token_from_the_url(self, page):
        assert "URLSearchParams" in page
        assert "'token'" in page or '"token"' in page

    def test_frontend_persists_the_token_across_reloads(self, page):
        """A reload drops the query string; without this the IDE dies on refresh."""
        assert "localStorage" in page
        assert "numchuck-token" in page

    def test_frontend_token_survives_a_new_tab(self, page):
        """sessionStorage is per-tab, so a second tab had no token at all.

        Verified against Chromium, Firefox and WebKit: with sessionStorage a
        fresh tab authenticated nothing and its WebSocket closed immediately.
        """
        # Assert the mechanism, not the prose -- a comment may well mention
        # sessionStorage to explain why it is not used.
        assert "localStorage.getItem(TOKEN_KEY)" in page
        assert "sessionStorage.getItem" not in page
        assert "sessionStorage.setItem" not in page

    def test_frontend_discards_a_rejected_token(self, page):
        """Otherwise a stale token from an earlier run wedges every later load."""
        assert "forgetToken" in page

    def test_frontend_feature_detects_the_clipboard(self, page):
        """navigator.clipboard is absent outside a secure context.

        Any non-loopback bind is insecure, so the unguarded calls in the REPL
        key handler threw TypeError on Ctrl+C/X/V -- in every browser.
        """
        assert "navigator.clipboard && navigator.clipboard.writeText" in page
        assert "navigator.clipboard && navigator.clipboard.readText" in page

    def test_frontend_sends_a_bearer_header_on_api_calls(self, page):
        assert "Authorization" in page
        assert "Bearer " in page

    def test_frontend_puts_the_token_on_the_websocket_url(self, page):
        assert "encodeURIComponent(authToken)" in page

    def test_frontend_reports_auth_failure(self, page):
        """Silently doing nothing is the worst way to report a rejected call."""
        assert "401" in page and "403" in page

    def test_frontend_websocket_scheme_follows_the_page(self, page):
        """A page served over https cannot open a ws:// socket."""
        assert "wss://" in page
