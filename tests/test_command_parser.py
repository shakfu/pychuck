"""
Tests for REPL command parser.

Tests the CommandParser class which parses REPL input into Command objects.
"""

import pytest
from numchuck.tui.parser import CommandParser, Command


@pytest.fixture
def parser():
    """Create a fresh parser instance."""
    return CommandParser()


class TestShredManagement:
    """Tests for shred management commands."""

    def test_add_file(self, parser):
        """Test 'add file.ck' command."""
        cmd = parser.parse("add test.ck")
        assert cmd.type == "spork_file"
        assert cmd.args["path"] == "test.ck"

    def test_add_file_with_path(self, parser):
        """Test 'add path/to/file.ck' command."""
        cmd = parser.parse("add path/to/file.ck")
        assert cmd.type == "spork_file"
        assert cmd.args["path"] == "path/to/file.ck"

    def test_plus_file(self, parser):
        """Test '+ file.ck' shortcut."""
        cmd = parser.parse("+ test.ck")
        assert cmd.type == "spork_file"
        assert cmd.args["path"] == "test.ck"

    def test_plus_code_double_quotes(self, parser):
        """Test '+ "code"' for inline code."""
        cmd = parser.parse('+ "SinOsc s => dac;"')
        assert cmd.type == "spork_code"
        assert cmd.args["code"] == "SinOsc s => dac;"

    def test_plus_code_single_quotes(self, parser):
        """Test "+ 'code'" for inline code."""
        cmd = parser.parse("+ 'SinOsc s => dac;'")
        assert cmd.type == "spork_code"
        assert cmd.args["code"] == "SinOsc s => dac;"

    def test_remove_all(self, parser):
        """Test 'remove all' command."""
        cmd = parser.parse("remove all")
        assert cmd.type == "remove_all"

    def test_minus_all(self, parser):
        """Test '- all' shortcut."""
        cmd = parser.parse("- all")
        assert cmd.type == "remove_all"

    def test_remove_shred(self, parser):
        """Test 'remove 1' command."""
        cmd = parser.parse("remove 1")
        assert cmd.type == "remove_shred"
        assert cmd.args["id"] == 1

    def test_minus_shred_with_space(self, parser):
        """Test '- 1' shortcut with space."""
        cmd = parser.parse("- 1")
        assert cmd.type == "remove_shred"
        assert cmd.args["id"] == 1

    def test_minus_shred_without_space(self, parser):
        """Test '-1' shortcut without space."""
        cmd = parser.parse("-1")
        assert cmd.type == "remove_shred"
        assert cmd.args["id"] == 1

    def test_replace_shred_file(self, parser):
        """Test 'replace 1 file.ck' command."""
        cmd = parser.parse("replace 1 new.ck")
        assert cmd.type == "replace_shred_file"
        assert cmd.args["id"] == 1
        assert cmd.args["path"] == "new.ck"

    def test_replace_shred_code(self, parser):
        """Test '~ 1 "code"' shortcut."""
        cmd = parser.parse('~ 1 "new code"')
        assert cmd.type == "replace_shred"
        assert cmd.args["id"] == 1
        assert cmd.args["code"] == "new code"

    def test_equals_replace_file(self, parser):
        """Test '= 1 file.ck' ChucK-style replace."""
        cmd = parser.parse("= 1 new.ck")
        assert cmd.type == "replace_shred_file"
        assert cmd.args["id"] == 1
        assert cmd.args["path"] == "new.ck"

    def test_equals_replace_file_no_space(self, parser):
        """Test '=1 file.ck' ChucK-style replace without space."""
        cmd = parser.parse("=1 new.ck")
        assert cmd.type == "replace_shred_file"
        assert cmd.args["id"] == 1
        assert cmd.args["path"] == "new.ck"

    def test_equals_replace_code(self, parser):
        """Test '= 1 "code"' ChucK-style replace with code."""
        cmd = parser.parse('= 1 "new code"')
        assert cmd.type == "replace_shred"
        assert cmd.args["id"] == 1
        assert cmd.args["code"] == "new code"

    def test_abort_shred_dot_syntax(self, parser):
        """Test 'abort.shred 1' ChucK-native abort command."""
        cmd = parser.parse("abort.shred 1")
        assert cmd.type == "abort_shred"
        assert cmd.args["id"] == 1

    def test_abort_shred_word(self, parser):
        """Test 'abort 1' abort command."""
        cmd = parser.parse("abort 1")
        assert cmd.type == "abort_shred"
        assert cmd.args["id"] == 1

    def test_exit_command(self, parser):
        """Test 'exit' command."""
        cmd = parser.parse("exit")
        assert cmd.type == "exit"

    def test_quit_command(self, parser):
        """Test 'quit' command."""
        cmd = parser.parse("quit")
        assert cmd.type == "exit"


class TestStatusCommands:
    """Tests for status and info commands."""

    def test_status(self, parser):
        """Test 'status' command."""
        cmd = parser.parse("status")
        assert cmd.type == "status"

    def test_caret_status(self, parser):
        """Test '^' ChucK-style status shortcut."""
        cmd = parser.parse("^")
        assert cmd.type == "status"

    def test_time(self, parser):
        """Test 'time' command."""
        cmd = parser.parse("time")
        assert cmd.type == "current_time"

    def test_dot_current_time(self, parser):
        """Test '.' shortcut for current time."""
        cmd = parser.parse(".")
        assert cmd.type == "current_time"

    def test_question_list_shreds(self, parser):
        """Test '?' shortcut for listing shreds."""
        cmd = parser.parse("?")
        assert cmd.type == "list_shreds"

    def test_question_shred_info(self, parser):
        """Test '? 1' for shred info."""
        cmd = parser.parse("? 1")
        assert cmd.type == "shred_info"
        assert cmd.args["id"] == 1

    def test_question_g_list_globals(self, parser):
        """Test '?g' for listing globals."""
        cmd = parser.parse("?g")
        assert cmd.type == "list_globals"

    def test_question_a_audio_info(self, parser):
        """Test '?a' for audio info."""
        cmd = parser.parse("?a")
        assert cmd.type == "audio_info"


class TestGlobalVariables:
    """Tests for global variable commands."""

    def test_set_global_int(self, parser):
        """Test 'name::123' for setting int."""
        cmd = parser.parse("myvar::42")
        assert cmd.type == "set_global"
        assert cmd.args["name"] == "myvar"
        assert cmd.args["value"] == 42

    def test_set_global_float(self, parser):
        """Test 'name::1.5' for setting float."""
        cmd = parser.parse("freq::440.0")
        assert cmd.type == "set_global"
        assert cmd.args["name"] == "freq"
        assert cmd.args["value"] == 440.0

    def test_set_global_string(self, parser):
        """Test 'name::"value"' for setting string."""
        cmd = parser.parse('msg::"hello"')
        assert cmd.type == "set_global"
        assert cmd.args["name"] == "msg"
        assert cmd.args["value"] == "hello"

    def test_set_global_array(self, parser):
        """Test 'name::[1,2,3]' for setting array."""
        cmd = parser.parse("arr::[1, 2, 3]")
        assert cmd.type == "set_global"
        assert cmd.args["name"] == "arr"
        assert cmd.args["value"] == [1, 2, 3]

    def test_get_global(self, parser):
        """Test 'name?' for getting global."""
        cmd = parser.parse("myvar?")
        assert cmd.type == "get_global"
        assert cmd.args["name"] == "myvar"


class TestEvents:
    """Tests for event signaling commands."""

    def test_signal_event(self, parser):
        """Test 'name!' for signaling event."""
        cmd = parser.parse("trigger!")
        assert cmd.type == "signal_event"
        assert cmd.args["name"] == "trigger"

    def test_broadcast_event(self, parser):
        """Test 'name!!' for broadcasting event."""
        cmd = parser.parse("trigger!!")
        assert cmd.type == "broadcast_event"
        assert cmd.args["name"] == "trigger"


class TestAudioControl:
    """Tests for audio control commands."""

    def test_start_audio(self, parser):
        """Test '>' for start audio."""
        cmd = parser.parse(">")
        assert cmd.type == "start_audio"

    def test_stop_audio(self, parser):
        """Test '||' for stop audio."""
        cmd = parser.parse("||")
        assert cmd.type == "stop_audio"

    def test_shutdown_audio(self, parser):
        """Test 'X' for shutdown audio."""
        cmd = parser.parse("X")
        assert cmd.type == "shutdown_audio"


class TestVMControl:
    """Tests for VM control commands."""

    def test_clear_vm(self, parser):
        """Test 'clear' command."""
        cmd = parser.parse("clear")
        assert cmd.type == "clear_vm"

    def test_reset_id(self, parser):
        """Test 'reset' command."""
        cmd = parser.parse("reset")
        assert cmd.type == "reset_id"


class TestScreenControl:
    """Tests for screen control commands."""

    def test_clear_screen(self, parser):
        """Test 'cls' command."""
        cmd = parser.parse("cls")
        assert cmd.type == "clear_screen"


class TestFileOperations:
    """Tests for file operation commands."""

    def test_compile_file(self, parser):
        """Test ': file.ck' for compile file."""
        cmd = parser.parse(": test.ck")
        assert cmd.type == "compile_file"
        assert cmd.args["path"] == "test.ck"

    def test_exec_code(self, parser):
        """Test '! "code"' for exec code."""
        cmd = parser.parse('! "<<< 1 >>>"')
        assert cmd.type == "exec_code"
        assert cmd.args["code"] == "<<< 1 >>>"

    def test_load_snippet(self, parser):
        """Test '@name' for loading snippet."""
        cmd = parser.parse("@sine")
        assert cmd.type == "load_snippet"
        assert cmd.args["name"] == "sine"


class TestEditCommands:
    """Tests for edit commands."""

    def test_edit_shred(self, parser):
        """Test 'edit 1' for editing shred."""
        cmd = parser.parse("edit 1")
        assert cmd.type == "edit_shred"
        assert cmd.args["id"] == 1

    def test_edit_shred_no_space(self, parser):
        """Test 'edit1' works too."""
        cmd = parser.parse("edit1")
        assert cmd.type == "edit_shred"
        assert cmd.args["id"] == 1

    def test_open_editor(self, parser):
        """Test 'edit' alone opens editor."""
        cmd = parser.parse("edit")
        assert cmd.type == "open_editor"


class TestMiscCommands:
    """Tests for miscellaneous commands."""

    def test_shell(self, parser):
        """Test '$ cmd' for shell command."""
        cmd = parser.parse("$ ls -la")
        assert cmd.type == "shell"
        assert cmd.args["cmd"] == "ls -la"

    def test_watch(self, parser):
        """Test 'watch' command."""
        cmd = parser.parse("watch")
        assert cmd.type == "watch"


class TestUnknownInput:
    """Tests for unknown/ChucK code input."""

    def test_chuck_code_returns_none(self, parser):
        """Test that ChucK code returns None (handled by REPL)."""
        cmd = parser.parse("SinOsc s => dac;")
        assert cmd is None

    def test_multiline_chuck_code(self, parser):
        """Test multiline ChucK code returns None."""
        cmd = parser.parse("fun void foo() {\n  <<< 1 >>>;\n}")
        assert cmd is None

    def test_empty_input(self, parser):
        """Test empty input returns None."""
        cmd = parser.parse("")
        assert cmd is None

    def test_whitespace_only(self, parser):
        """Test whitespace-only input returns None."""
        cmd = parser.parse("   ")
        assert cmd is None
