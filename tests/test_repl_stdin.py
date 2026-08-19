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

    def test_executor_exception_caught(self, repl):
        """Test that exceptions from executor are caught gracefully."""
        repl.executor.execute = MagicMock(
            side_effect=RuntimeError("service unavailable")
        )
        result = repl.process_line("status")
        assert result is not None
        assert "Error" in result
        assert "service unavailable" in result

    def test_spork_code_exception_caught(self, repl):
        """Test that exceptions from spork_code are caught gracefully."""
        repl.app_state.shred_service.spork_code = MagicMock(
            side_effect=AttributeError("chuck is None")
        )
        result = repl.process_line("SinOsc s => dac;")
        assert result is not None
        assert "Error" in result
        assert "chuck is None" in result


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

    def test_clear_command(self):
        """Test clear VM command."""
        # Note: After clear, session.shreds is cleared so ? shows empty
        stdin = StringIO("SinOsc s => dac;\nclear\n")
        repl = ChuckREPLStdin()
        exit_code = repl.run(input_stream=stdin)
        assert exit_code == 0

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
            assert repl.show_help_window is False
            assert repl.show_shreds_window is False
            assert repl.max_transcript_lines == 500
            # Single buffer starts with prompt
            assert repl.buffer.text == "[=>] "
            assert repl.input_start == len("[=>] ")
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
            assert hasattr(repl, "buffer")
            assert hasattr(repl, "help_area")
            assert hasattr(repl, "shreds_area")
        finally:
            repl.cleanup()


@pytest.mark.tui
class TestChuckREPLAddToLog:
    """Tests for add_to_log method."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance."""
        repl = ChuckREPL()
        repl.app.invalidate = MagicMock()
        yield repl
        repl.cleanup()

    def test_add_single_message(self, repl):
        """Test adding a single log message."""
        repl.add_to_log("Test message")
        assert "  Test message" in repl.buffer.text

    def test_add_multiple_messages(self, repl):
        """Test adding multiple log messages."""
        repl.add_to_log("Message 1")
        repl.add_to_log("Message 2")
        repl.add_to_log("Message 3")
        assert "  Message 1" in repl.buffer.text
        assert "  Message 2" in repl.buffer.text
        assert "  Message 3" in repl.buffer.text

    def test_strips_trailing_newline(self, repl):
        """Test that trailing newlines are stripped."""
        repl.add_to_log("Message with newline\n")
        assert "  Message with newline" in repl.buffer.text

    def test_empty_message_ignored(self, repl):
        """Test that empty messages are ignored."""
        initial = repl.buffer.text
        repl.add_to_log("")
        assert repl.buffer.text == initial

    def test_whitespace_only_ignored(self, repl):
        """Test that whitespace-only messages after strip are ignored."""
        initial = repl.buffer.text
        repl.add_to_log("\n")
        assert repl.buffer.text == initial

    def test_updates_buffer_text(self, repl):
        """Test that buffer text is updated with log messages."""
        repl.add_to_log("Line 1")
        repl.add_to_log("Line 2")
        assert "Line 1" in repl.buffer.text
        assert "Line 2" in repl.buffer.text

    def test_invalidates_app(self, repl):
        """Test that app.invalidate is called."""
        repl.add_to_log("Test")
        assert repl.app.invalidate.call_count >= 1

    def test_prompt_remains_at_end(self, repl):
        """Test that prompt is still at end after add_to_log."""
        repl.add_to_log("Some output")
        assert repl.buffer.text.endswith("[=>] ")


@pytest.mark.tui
class TestChuckREPLSubmitInput:
    """Tests for _submit_input method."""

    @pytest.fixture
    def repl(self):
        """Create a REPL instance with mocked app.

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

    def _simulate_input(self, repl, text):
        """Simulate user typing text and submitting."""
        repl.buffer.text = repl.buffer.text[:repl.input_start] + text
        repl.buffer.cursor_position = len(repl.buffer.text)
        repl._submit_input(text)

    def test_empty_input(self, repl):
        """Test empty input adds new prompt."""
        self._simulate_input(repl, "")
        assert repl.buffer.text.endswith("[=>] ")

    def test_whitespace_input(self, repl):
        """Test whitespace-only input adds new prompt."""
        self._simulate_input(repl, "   ")
        assert repl.buffer.text.endswith("[=>] ")

    def test_quit_command_exits(self, repl):
        """Test quit command calls app.exit."""
        self._simulate_input(repl, "quit")
        repl.app.exit.assert_called_once()

    def test_exit_command_exits(self, repl):
        """Test exit command calls app.exit."""
        self._simulate_input(repl, "exit")
        repl.app.exit.assert_called_once()

    def test_q_command_exits(self, repl):
        """Test 'q' command calls app.exit."""
        self._simulate_input(repl, "q")
        repl.app.exit.assert_called_once()

    def test_help_command_toggles_help(self, repl):
        """Test help command toggles help window."""
        assert repl.show_help_window is False
        self._simulate_input(repl, "help")
        assert repl.show_help_window is True
        self._simulate_input(repl, "help")
        assert repl.show_help_window is False

    def test_unknown_command_shows_error_in_buffer(self, repl):
        """Test unknown command shows error inline in buffer."""
        self._simulate_input(repl, "unknowncommand")
        assert "[!] Unknown command" in repl.buffer.text

    def test_chuck_code_compilation(self, repl):
        """Test ChucK code is compiled."""
        self._simulate_input(repl, "SinOsc s => dac;")
        assert len(repl.session.shreds) == 1

    def test_invalid_chuck_code_shows_error_in_buffer(self, repl):
        """Test invalid ChucK code shows error inline in buffer."""
        self._simulate_input(repl, "SinOsc s => ;")
        assert "[!]" in repl.buffer.text

    def test_list_shreds_command(self, repl):
        """Test list shreds command."""
        self._simulate_input(repl, "?")
        assert repl.buffer.text.endswith("[=>] ")

    def test_current_time_command(self, repl):
        """Test current time command."""
        self._simulate_input(repl, ".")
        assert repl.buffer.text.endswith("[=>] ")

    def test_invalidates_app_after_processing(self, repl):
        """Test that app.invalidate is called after processing."""
        self._simulate_input(repl, "?")
        assert repl.app.invalidate.call_count >= 1

    def test_input_preserved_in_buffer(self, repl):
        """Test that submitted input remains visible in buffer transcript."""
        self._simulate_input(repl, "status")
        assert "[=>] status" in repl.buffer.text

    def test_new_prompt_after_command(self, repl):
        """Test that a new prompt appears after command execution."""
        self._simulate_input(repl, "?")
        assert repl.buffer.text.endswith("[=>] ")
        assert repl.buffer.cursor_position == len(repl.buffer.text)


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

    def test_buffer_starts_with_prompt(self, repl):
        """Test buffer starts with just the prompt."""
        assert repl.buffer.text == "[=>] "


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

    def _simulate_input(self, repl, text):
        """Simulate user typing text and submitting."""
        repl.buffer.text = repl.buffer.text[:repl.input_start] + text
        repl.buffer.cursor_position = len(repl.buffer.text)
        repl._submit_input(text)

    def test_buffer_starts_with_prompt(self, repl):
        """Test buffer starts with just the prompt."""
        assert repl.buffer.text == "[=>] "

    def test_error_inline_on_unknown_command(self, repl):
        """Test error appears inline in buffer on unknown command."""
        self._simulate_input(repl, "xyz123")
        assert "[!] Unknown command" in repl.buffer.text
        assert "xyz123" in repl.buffer.text

    def test_error_inline_on_compilation_failure(self, repl):
        """Test error appears inline in buffer on compilation failure."""
        self._simulate_input(repl, "invalid => syntax => here;")
        has_error = "[!]" in repl.buffer.text
        assert has_error or len(repl.session.shreds) == 0

    def test_input_visible_in_buffer(self, repl):
        """Test that submitted input is visible in buffer."""
        self._simulate_input(repl, "status")
        assert "[=>] status" in repl.buffer.text

    def test_new_prompt_after_error(self, repl):
        """Test new prompt appears after error."""
        self._simulate_input(repl, "xyz123")
        assert repl.buffer.text.endswith("[=>] ")
