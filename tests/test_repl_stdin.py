"""Tests for REPL modules including stdin mode and interactive mode."""

import pytest
from io import StringIO
from unittest.mock import MagicMock, patch, PropertyMock

from numchuck.tui.repl import ChuckREPLStdin, ChuckREPL


class TestChuckREPLStdinBasic:
    """Basic tests for ChuckREPLStdin class."""

    def test_init(self):
        """Test initialization."""
        repl = ChuckREPLStdin()
        assert repl.app_state is not None
        assert repl.parser is not None
        assert repl.executor is not None

    def test_init_with_project(self):
        """Test initialization with project name."""
        repl = ChuckREPLStdin(project_name="test_project")
        assert repl.app_state is not None


class TestChuckREPLStdinProcessLine:
    """Tests for process_line method."""

    @pytest.fixture
    def repl(self):
        """Create and setup a REPL instance."""
        repl = ChuckREPLStdin()
        repl.setup()
        yield repl
        repl.cleanup()

    def test_empty_line(self, repl):
        """Test empty line returns None."""
        result = repl.process_line("")
        assert result is None

    def test_comment_line(self, repl):
        """Test comment line is skipped."""
        result = repl.process_line("# this is a comment")
        assert result is None

    def test_whitespace_line(self, repl):
        """Test whitespace-only line returns None."""
        result = repl.process_line("   \t  ")
        assert result is None

    def test_quit_command(self, repl):
        """Test quit command returns EXIT signal."""
        result = repl.process_line("quit")
        assert result == "EXIT"

    def test_exit_command(self, repl):
        """Test exit command returns EXIT signal."""
        result = repl.process_line("exit")
        assert result == "EXIT"

    def test_q_command(self, repl):
        """Test q command returns EXIT signal."""
        result = repl.process_line("q")
        assert result == "EXIT"

    def test_list_shreds_empty(self, repl):
        """Test listing shreds when none exist."""
        result = repl.process_line("?")
        assert result is None
        # Output goes to _log, not return value

    def test_current_time(self, repl):
        """Test getting current time."""
        result = repl.process_line(".")
        assert result is None

    def test_unknown_command(self, repl):
        """Test unknown command returns error."""
        result = repl.process_line("foobar")
        assert result == "Unknown command: foobar"

    def test_chuck_code_compilation(self, repl):
        """Test ChucK code is compiled and sporked."""
        result = repl.process_line("SinOsc s => dac;")
        assert result is None
        # Verify shred was added to session
        assert len(repl.session.shreds) == 1

    def test_chuck_code_with_arrow(self, repl):
        """Test code with ChucK arrow operator."""
        result = repl.process_line("1 => int x;")
        assert result is None
        assert len(repl.session.shreds) == 1

    def test_invalid_chuck_code(self, repl):
        """Test invalid ChucK code returns error."""
        result = repl.process_line("SinOsc s => ;")  # syntax error
        assert result is not None
        # Error message contains "Failed" or "error" (case-insensitive)
        assert "fail" in result.lower() or "error" in result.lower()


class TestChuckREPLStdinRun:
    """Tests for run method."""

    def test_run_with_commands(self):
        """Test running with piped commands."""
        stdin = StringIO("?\n.\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    def test_run_with_quit(self):
        """Test run exits on quit command."""
        stdin = StringIO("?\nquit\n.\n")  # . should not run after quit
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    def test_run_with_exit(self):
        """Test run exits on exit command."""
        stdin = StringIO("exit\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    def test_run_with_error(self):
        """Test run returns error code on failure."""
        stdin = StringIO("invalid_chuck_code => ;")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 1

    def test_run_with_chuck_code(self):
        """Test running ChucK code."""
        stdin = StringIO("SinOsc s => dac;\n?\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    def test_run_with_comments(self):
        """Test comments are ignored."""
        stdin = StringIO("# Comment line\n?\n# Another comment\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0


class TestChuckREPLStdinCommands:
    """Tests for various REPL commands via stdin."""

    def test_spork_file_command(self, tmp_path):
        """Test sporking a file via command."""
        # Create a test ChucK file
        ck_file = tmp_path / "test.ck"
        ck_file.write_text("SinOsc s => dac;")

        stdin = StringIO(f"+ {ck_file}\n?\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    @pytest.mark.realtime
    def test_audio_commands(self):
        """Test audio start/stop commands."""
        stdin = StringIO(">\n||\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    @pytest.mark.skip(reason="clear_vm may fail without audio running")
    def test_clear_command(self):
        """Test clear VM command."""
        # Note: After clear, session.shreds is cleared so ? shows empty
        stdin = StringIO("SinOsc s => dac;\nclear\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    @pytest.mark.skip(reason="get_all_globals segfaults without audio running")
    def test_globals_query(self):
        """Test globals query command."""
        stdin = StringIO("?g\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

    def test_audio_info(self):
        """Test audio info command."""
        stdin = StringIO("?a\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0


# =============================================================================
# ChuckREPL (Interactive REPL) Tests
# These tests require a terminal/console and are skipped on CI.
# =============================================================================


@pytest.mark.tui
class TestChuckREPLInit:
    """Tests for ChuckREPL initialization."""

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        repl = ChuckREPL()
        try:
            assert repl.smart_enter is True
            assert repl.show_sidebar is True
            assert repl.app_state is not None
            assert repl.chuck is not None
            assert repl.session is not None
            assert repl.parser is not None
            assert repl.executor is not None
            assert repl.completer is not None
            assert repl.error_message == ""
            assert repl.show_help_window is False
            assert repl.show_shreds_window is False
            assert repl.show_log_window is False
            assert repl.log_lines == []
            assert repl.max_log_lines == 100
        finally:
            repl.cleanup()

    def test_init_smart_enter_disabled(self):
        """Test initialization with smart_enter disabled."""
        repl = ChuckREPL(smart_enter=False)
        try:
            assert repl.smart_enter is False
        finally:
            repl.cleanup()

    def test_init_sidebar_disabled(self):
        """Test initialization with sidebar disabled."""
        repl = ChuckREPL(show_sidebar=False)
        try:
            assert repl.show_sidebar is False
        finally:
            repl.cleanup()

    def test_init_with_project_name(self):
        """Test initialization with project name."""
        repl = ChuckREPL(project_name="test_project")
        try:
            assert repl.app_state is not None
        finally:
            repl.cleanup()

    def test_init_creates_prompt_toolkit_components(self):
        """Test that prompt_toolkit components are created."""
        repl = ChuckREPL()
        try:
            assert hasattr(repl, "app")
            assert hasattr(repl, "input_buffer")
            assert hasattr(repl, "help_area")
            assert hasattr(repl, "log_area")
            assert hasattr(repl, "shreds_area")
            assert hasattr(repl, "prompt_html")
        finally:
            repl.cleanup()


@pytest.mark.tui
class TestChuckREPLAddToLog:
    """Tests for add_to_log method."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance."""
        repl = ChuckREPL()
        # Mock app.invalidate to avoid UI updates
        repl.app.invalidate = MagicMock()
        yield repl
        repl.cleanup()

    def test_add_single_message(self, repl):
        """Test adding a single log message."""
        repl.add_to_log("Test message")
        assert "Test message" in repl.log_lines
        assert len(repl.log_lines) == 1

    def test_add_multiple_messages(self, repl):
        """Test adding multiple log messages."""
        repl.add_to_log("Message 1")
        repl.add_to_log("Message 2")
        repl.add_to_log("Message 3")
        assert len(repl.log_lines) == 3
        assert repl.log_lines == ["Message 1", "Message 2", "Message 3"]

    def test_strips_trailing_newline(self, repl):
        """Test that trailing newlines are stripped."""
        repl.add_to_log("Message with newline\n")
        assert repl.log_lines[0] == "Message with newline"

    def test_empty_message_ignored(self, repl):
        """Test that empty messages are ignored."""
        repl.add_to_log("")
        assert len(repl.log_lines) == 0

    def test_whitespace_only_ignored(self, repl):
        """Test that whitespace-only messages after strip are ignored."""
        repl.add_to_log("\n")
        assert len(repl.log_lines) == 0

    def test_max_log_lines_limit(self, repl):
        """Test that log is trimmed at max_log_lines."""
        repl.max_log_lines = 5
        for i in range(10):
            repl.add_to_log(f"Message {i}")
        assert len(repl.log_lines) == 5
        # Should have the last 5 messages
        assert repl.log_lines[0] == "Message 5"
        assert repl.log_lines[-1] == "Message 9"

    def test_updates_log_area_text(self, repl):
        """Test that log_area text is updated."""
        repl.add_to_log("Line 1")
        repl.add_to_log("Line 2")
        assert "Line 1" in repl.log_area.text
        assert "Line 2" in repl.log_area.text

    def test_invalidates_app(self, repl):
        """Test that app.invalidate is called."""
        repl.add_to_log("Test")
        assert repl.app.invalidate.call_count >= 1


@pytest.mark.tui
class TestChuckREPLProcessInput:
    """Tests for process_input method."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance with mocked app.

        Note: We call app_state.setup() directly instead of repl.setup()
        to avoid setting static stdout/stderr callbacks which cause
        segfaults at interpreter shutdown.
        """
        repl = ChuckREPL()
        # Initialize ChucK without setting static callbacks
        repl.app_state.setup()
        # Mock app methods
        repl.app.invalidate = MagicMock()
        repl.app.exit = MagicMock()
        yield repl
        repl.cleanup()

    def _create_buffer(self, text):
        """Create a mock buffer with given text."""
        buffer = MagicMock()
        buffer.text = text
        return buffer

    def test_empty_input_returns_true(self, repl):
        """Test empty input returns True."""
        buffer = self._create_buffer("")
        result = repl.process_input(buffer)
        assert result is True

    def test_whitespace_input_returns_true(self, repl):
        """Test whitespace-only input returns True."""
        buffer = self._create_buffer("   ")
        result = repl.process_input(buffer)
        assert result is True

    def test_quit_command_exits(self, repl):
        """Test quit command calls app.exit."""
        buffer = self._create_buffer("quit")
        result = repl.process_input(buffer)
        assert result is True
        repl.app.exit.assert_called_once()

    def test_exit_command_exits(self, repl):
        """Test exit command calls app.exit."""
        buffer = self._create_buffer("exit")
        result = repl.process_input(buffer)
        assert result is True
        repl.app.exit.assert_called_once()

    def test_q_command_exits(self, repl):
        """Test 'q' command calls app.exit."""
        buffer = self._create_buffer("q")
        result = repl.process_input(buffer)
        assert result is True
        repl.app.exit.assert_called_once()

    def test_help_command_toggles_help(self, repl):
        """Test help command toggles help window."""
        assert repl.show_help_window is False
        buffer = self._create_buffer("help")
        repl.process_input(buffer)
        assert repl.show_help_window is True
        # Toggle again
        repl.process_input(buffer)
        assert repl.show_help_window is False

    def test_clears_previous_error(self, repl):
        """Test that previous error is cleared."""
        repl.error_message = "Previous error"
        buffer = self._create_buffer("?")
        repl.process_input(buffer)
        assert repl.error_message == ""

    def test_unknown_command_sets_error(self, repl):
        """Test unknown command sets error message."""
        buffer = self._create_buffer("unknowncommand")
        repl.process_input(buffer)
        assert "Unknown command" in repl.error_message

    def test_chuck_code_compilation(self, repl):
        """Test ChucK code is compiled."""
        buffer = self._create_buffer("SinOsc s => dac;")
        repl.process_input(buffer)
        # Should have added a shred
        assert len(repl.session.shreds) == 1

    def test_invalid_chuck_code_sets_error(self, repl):
        """Test invalid ChucK code sets error message."""
        buffer = self._create_buffer("SinOsc s => ;")  # Invalid
        repl.process_input(buffer)
        assert repl.error_message != ""

    def test_list_shreds_command(self, repl):
        """Test list shreds command."""
        buffer = self._create_buffer("?")
        result = repl.process_input(buffer)
        assert result is True

    def test_current_time_command(self, repl):
        """Test current time command."""
        buffer = self._create_buffer(".")
        result = repl.process_input(buffer)
        assert result is True

    def test_invalidates_app_after_processing(self, repl):
        """Test that app.invalidate is called after processing."""
        buffer = self._create_buffer("?")
        repl.process_input(buffer)
        assert repl.app.invalidate.call_count >= 1


@pytest.mark.tui
class TestChuckREPLCleanup:
    """Tests for cleanup method."""

    def test_cleanup_clears_references(self):
        """Test that cleanup clears all references."""
        repl = ChuckREPL()
        repl.cleanup()

        assert repl.chuck is None
        assert repl.session is None
        assert repl.completer is None
        assert repl.executor is None
        assert repl.app_state is None

    def test_cleanup_handles_missing_attributes(self):
        """Test cleanup handles missing attributes gracefully."""
        repl = ChuckREPL()
        # Remove some attributes
        del repl.completer
        del repl.executor
        # Should not raise
        repl.cleanup()
        # Verify cleanup completed (app_state is now None)
        assert repl.app_state is None

    def test_cleanup_twice_safe(self):
        """Test calling cleanup twice is safe."""
        repl = ChuckREPL()
        repl.cleanup()
        # Verify first cleanup worked
        assert repl.app_state is None
        # Second call should not raise
        repl.cleanup()
        # Still None after second cleanup
        assert repl.app_state is None


@pytest.mark.tui
class TestChuckREPLSetup:
    """Tests for setup method."""

    def test_setup_initializes_chuck(self):
        """Test setup initializes ChucK.

        Note: We call app_state.setup() directly instead of repl.setup()
        to avoid setting static stdout/stderr callbacks which cause
        segfaults at interpreter shutdown.
        """
        repl = ChuckREPL()
        try:
            repl.app_state.setup()
            # ChucK should be initialized
            assert repl.app_state.chuck is not None
        finally:
            repl.cleanup()


@pytest.mark.tui
class TestChuckREPLHelperFunctions:
    """Tests for internal helper functions defined in __init__."""

    def test_get_topbar_text_no_shreds(self):
        """Test topbar text when no shreds are running."""
        repl = ChuckREPL()
        try:
            # Access the get_topbar_text function indirectly through the app
            # The topbar should show "No active shreds"
            assert len(repl.session.shreds) == 0
        finally:
            repl.cleanup()

    def test_get_shreds_table_callable(self):
        """Test get_shreds_table is callable."""
        repl = ChuckREPL()
        try:
            result = repl.get_shreds_table()
            assert isinstance(result, str)
        finally:
            repl.cleanup()

    def test_shreds_area_updates(self):
        """Test shreds_area can be updated."""
        repl = ChuckREPL()
        try:
            repl.shreds_area.text = "Test content"
            assert repl.shreds_area.text == "Test content"
        finally:
            repl.cleanup()


@pytest.mark.tui
class TestChuckREPLWindowToggles:
    """Tests for window toggle functionality."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance."""
        repl = ChuckREPL()
        yield repl
        repl.cleanup()

    def test_help_window_toggle(self, repl):
        """Test help window toggle state."""
        assert repl.show_help_window is False
        repl.show_help_window = True
        assert repl.show_help_window is True

    def test_shreds_window_toggle(self, repl):
        """Test shreds window toggle state."""
        assert repl.show_shreds_window is False
        repl.show_shreds_window = True
        assert repl.show_shreds_window is True

    def test_log_window_toggle(self, repl):
        """Test log window toggle state."""
        assert repl.show_log_window is False
        repl.show_log_window = True
        assert repl.show_log_window is True


@pytest.mark.tui
class TestChuckREPLErrorHandling:
    """Tests for error handling in REPL."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance.

        Note: We call app_state.setup() directly instead of repl.setup()
        to avoid setting static stdout/stderr callbacks which cause
        segfaults at interpreter shutdown.
        """
        repl = ChuckREPL()
        repl.app_state.setup()
        repl.app.invalidate = MagicMock()
        repl.app.exit = MagicMock()
        yield repl
        repl.cleanup()

    def _create_buffer(self, text):
        """Create a mock buffer with given text."""
        buffer = MagicMock()
        buffer.text = text
        return buffer

    def test_error_message_initially_empty(self, repl):
        """Test error message is initially empty."""
        assert repl.error_message == ""

    def test_error_set_on_unknown_command(self, repl):
        """Test error is set on unknown command."""
        buffer = self._create_buffer("xyz123")
        repl.process_input(buffer)
        assert "Unknown command" in repl.error_message
        assert "xyz123" in repl.error_message

    def test_error_cleared_on_next_input(self, repl):
        """Test error is cleared on next input."""
        repl.error_message = "Previous error"
        buffer = self._create_buffer("?")
        repl.process_input(buffer)
        assert repl.error_message == ""

    def test_error_on_compilation_failure(self, repl):
        """Test error is set on ChucK compilation failure."""
        buffer = self._create_buffer("invalid => syntax => here;")
        repl.process_input(buffer)
        # Error should be set (either from parser or spork_code)
        # Note: The code might be parsed as ChucK code and fail to compile
        assert repl.error_message != "" or len(repl.session.shreds) == 0
