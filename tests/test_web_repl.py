"""Tests for the web IDE's REPL, which shares the TUI's command executor.

The web front-end used to carry its own if/elif dispatcher over the same parsed
commands as ``tui.commands.CommandExecutor``. The two drifted: ``shell``,
``watch``, ``record`` and ``midi`` all parsed cleanly in the browser and then
fell through to "Unknown command". These tests hold the front-end to the shared
executor and keep the one deliberate difference -- commands that would start a
process on the server -- explicit and complete.
"""

from __future__ import annotations

import gc
import json

import pytest

from numchuck import Chuck
from numchuck.tui.commands import CommandExecutor
from numchuck.tui.parser import CommandParser
from numchuck.web import WEB_AVAILABLE, WebChuckServer, _DENIED_COMMANDS

pytestmark = pytest.mark.skipif(not WEB_AVAILABLE, reason="web module not built")


@pytest.fixture
def server():
    chuck = Chuck()
    instance = WebChuckServer(chuck, port=8123)
    yield instance
    instance.stop()
    chuck.close()
    gc.collect()


def repl(server: WebChuckServer, text: str) -> dict:
    """Run one REPL line, returning the decoded response."""
    raw = server._handle_repl_command(text)
    return json.loads(raw) if raw else {}


class TestDeniedCommands:
    """Commands that would run a process on the server host are refused."""

    def test_every_denied_command_exists(self):
        """No stale entries: denying a command that no longer exists is a lie."""
        for name in _DENIED_COMMANDS:
            assert hasattr(CommandExecutor, f"_cmd_{name}"), (
                f"_DENIED_COMMANDS names {name!r}, which the executor does not handle"
            )

    @staticmethod
    def _hazardous_handlers() -> dict[str, str]:
        """Executor handlers that must not be reachable from a browser.

        Two hazards, both found by reading the handler source: starting a
        process on the server host, and looping until a terminal interrupt --
        the latter would pin the single-threaded server event loop forever.
        """
        import inspect

        hazards: dict[str, str] = {}
        for name, member in inspect.getmembers(CommandExecutor, inspect.isfunction):
            if not name.startswith("_cmd_"):
                continue
            try:
                source = inspect.getsource(member)
            except OSError:  # pragma: no cover - source always available here
                continue
            if "subprocess." in source:
                hazards[name[len("_cmd_") :]] = "spawns a process"
            elif "while True" in source and "KeyboardInterrupt" in source:
                hazards[name[len("_cmd_") :]] = "loops until interrupted"
        return hazards

    def test_hazardous_commands_are_all_denied(self):
        """The deny-list stays complete as commands are added.

        A new handler that shells out or blocks forever must be denied here
        too, or the browser gains it silently.
        """
        hazards = self._hazardous_handlers()

        assert hazards, "expected to find hazardous handlers to check"
        missing = sorted(set(hazards) - set(_DENIED_COMMANDS))
        assert not missing, (
            "these are unsafe in the web IDE but not denied: "
            + ", ".join(f"{name} ({hazards[name]})" for name in missing)
        )

    def test_watch_is_refused_rather_than_hanging(self):
        """'watch' loops until Ctrl-C, which never arrives over HTTP."""
        assert "watch" in _DENIED_COMMANDS
        assert "watch" in self._hazardous_handlers()

    def test_shell_command_is_refused_with_a_reason(self, server):
        result = repl(server, "shell echo hello")

        assert result["type"] == "repl_error"
        assert "shell" in result["text"].lower()
        # Not the generic miss the old dispatcher produced
        assert "unknown" not in result["text"].lower()

    def test_shell_shorthand_is_refused(self, server):
        result = repl(server, "$ echo hello")

        assert result["type"] == "repl_error"
        assert "shell" in result["text"].lower()

    def test_watch_command_is_refused_with_a_reason(self, server):
        result = repl(server, "watch")

        assert result["type"] == "repl_error"
        assert "terminal" in result["text"].lower()

    def test_external_editor_is_refused(self, server):
        assert repl(server, "edit")["type"] == "repl_error"
        assert repl(server, "edit 1")["type"] == "repl_error"


class TestSharedExecutorReachesWeb:
    """Commands the TUI supports now work in the browser too."""

    @pytest.mark.parametrize(
        "line",
        [
            "record status",  # was "Unknown command: record_status"
            "midi status",    # was "Unknown command: midi_status"
            "osc status",     # was "Unknown command: osc_status"
            "recordings",     # was "Unknown command: list_recordings"
        ],
    )
    def test_previously_missing_commands_are_handled(self, server, line):
        result = repl(server, line)

        assert result, f"{line!r} produced no response"
        text = result.get("text", "")
        assert "Unknown command" not in text, f"{line!r} -> {text!r}"

    def test_parsed_command_types_are_not_rejected_as_unknown(self, server):
        """Sweep the parser's own vocabulary for dispatch holes."""
        parser = CommandParser()
        lines = [
            "status", "^", "?", "shreds", ".", "?a", "?g",
            "clear", "reset", "unwatch all",
            "record status", "midi status", "osc status", "recordings",
        ]
        unknown = []
        for line in lines:
            assert parser.parse(line) is not None, f"parser lost {line!r}"
            text = repl(server, line).get("text", "")
            if "Unknown command" in text:
                unknown.append(line)

        assert not unknown, f"web REPL does not dispatch: {unknown}"


class TestReplBehaviour:
    """End-to-end behaviour of the browser REPL."""

    def test_bare_code_is_compiled(self, server):
        result = repl(server, "SinOsc s => dac; 1::samp => now;")

        assert result["type"] == "repl_output"
        assert "shred" in result["text"]

    def test_invalid_code_reports_an_error(self, server):
        result = repl(server, "this is not chuck code @@@")

        assert result["type"] == "repl_error"

    def test_spork_then_list_then_remove(self, server):
        sporked = repl(server, '+ "SinOsc s => dac; 1::second => now;"')
        assert sporked["type"] == "repl_output"

        listed = repl(server, "?")
        assert listed["type"] == "repl_output"

        removed = repl(server, "- all")
        assert removed["type"] != "repl_error"

    def test_status_reports_vm_state(self, server):
        result = repl(server, "status")

        assert result["type"] == "repl_output"
        assert result["text"]

    def test_help_lists_the_denied_commands(self, server):
        result = repl(server, "help")

        assert result["type"] == "repl_output"
        for name in _DENIED_COMMANDS:
            assert name in result["text"]

    def test_empty_input_is_ignored(self, server):
        assert repl(server, "   ") == {}

    def test_exit_does_not_kill_the_server(self, server):
        result = repl(server, "exit")

        assert result["type"] == "repl_output"

    def test_executor_output_is_returned_not_swallowed(self, server):
        """The shared executor prints through a callback rather than returning.

        The web layer captures that per-thread; if the wiring breaks, commands
        succeed silently and the browser shows nothing.
        """
        repl(server, '+ "SinOsc s => dac; 1::second => now;"')
        result = repl(server, "?g")

        assert result["type"] == "repl_output"
        assert result["text"], "no captured output from the executor"


class TestSharedSessionState:
    """The REST API and the REPL act on one session, not two."""

    def test_shred_sporked_over_repl_appears_in_status(self, server):
        repl(server, '+ "SinOsc s => dac; 1::second => now;"')

        status = json.loads(server._api_status())

        assert status["shreds"], "REPL-sporked shred missing from /api/status"
        assert all("id" in s for s in status["shreds"])

    def test_shred_sporked_over_api_appears_in_repl(self, server):
        status_code, body = server._api_compile(
            {"code": "SinOsc s => dac; 1::second => now;"}
        )
        assert status_code == 200

        listed = repl(server, "?")

        assert str(json.loads(body)["shred_ids"][0]) in listed["text"]

    def test_shred_code_is_recoverable_after_repl_spork(self, server):
        code = "SinOsc osc => dac; 1::second => now;"
        repl(server, f'+ "{code}"')

        status = json.loads(server._api_status())
        shred_id = status["shreds"][0]["id"]
        stored = json.loads(server._api_get_shred_code(shred_id))

        assert "SinOsc" in stored["code"]
