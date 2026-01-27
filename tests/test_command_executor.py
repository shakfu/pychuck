"""Tests for CommandExecutor class."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from numchuck.tui.commands import CommandExecutor
from numchuck.services import ShredService, GlobalsService, FileService, ShredResult, GlobalInfo
from numchuck.services.files import SnippetInfo


class TestCommandExecutorInit:
    """Tests for CommandExecutor initialization."""

    def test_init_with_services(self):
        """Test initialization with provided services."""
        session = MagicMock()
        session.chuck = MagicMock()
        shred_service = MagicMock(spec=ShredService)
        globals_service = MagicMock(spec=GlobalsService)

        executor = CommandExecutor(
            session,
            shred_service=shred_service,
            globals_service=globals_service,
        )

        assert executor.session is session
        assert executor._shred_service is shred_service
        assert executor._globals_service is globals_service

    def test_init_creates_services_when_chuck_available(self):
        """Test services are created when chuck is available."""
        session = MagicMock()
        mock_chuck = MagicMock()
        session.chuck = mock_chuck

        with patch("numchuck.tui.commands.ShredService") as MockShredService:
            with patch("numchuck.tui.commands.GlobalsService") as MockGlobalsService:
                executor = CommandExecutor(session)

                assert MockShredService.call_count == 1
                assert MockGlobalsService.call_count == 1
                assert executor._shred_service is not None
                assert executor._globals_service is not None

    def test_init_no_services_when_chuck_none(self):
        """Test services remain None when chuck is None."""
        session = MagicMock()
        session.chuck = None

        executor = CommandExecutor(session)

        assert executor._shred_service is None
        assert executor._globals_service is None


class TestCommandExecutorProperties:
    """Tests for CommandExecutor properties."""

    def test_chuck_property_returns_chuck(self):
        """Test chuck property returns the ChucK instance."""
        session = MagicMock()
        mock_chuck = MagicMock()
        session.chuck = mock_chuck

        executor = CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

        assert executor.chuck is mock_chuck

    def test_chuck_property_raises_when_none(self):
        """Test chuck property raises RuntimeError when None."""
        session = MagicMock()
        session.chuck = None

        executor = CommandExecutor(session)

        with pytest.raises(RuntimeError, match="ChucK instance not available"):
            _ = executor.chuck

    def test_shred_service_property_returns_service(self):
        """Test shred_service property returns the service."""
        session = MagicMock()
        session.chuck = MagicMock()
        shred_service = MagicMock(spec=ShredService)

        executor = CommandExecutor(session, shred_service=shred_service)

        assert executor.shred_service is shred_service

    def test_shred_service_property_raises_when_none(self):
        """Test shred_service property raises RuntimeError when None."""
        session = MagicMock()
        session.chuck = None

        executor = CommandExecutor(session)

        with pytest.raises(RuntimeError, match="ShredService not available"):
            _ = executor.shred_service

    def test_globals_service_property_returns_service(self):
        """Test globals_service property returns the service."""
        session = MagicMock()
        session.chuck = MagicMock()
        globals_service = MagicMock(spec=GlobalsService)

        executor = CommandExecutor(session, globals_service=globals_service)

        assert executor.globals_service is globals_service

    def test_globals_service_property_raises_when_none(self):
        """Test globals_service property raises RuntimeError when None."""
        session = MagicMock()
        session.chuck = None

        executor = CommandExecutor(session)

        with pytest.raises(RuntimeError, match="GlobalsService not available"):
            _ = executor.globals_service

    def test_file_service_property_returns_service(self):
        """Test file_service property returns the service."""
        session = MagicMock()
        session.chuck = MagicMock()
        file_service = MagicMock(spec=FileService)

        executor = CommandExecutor(session, file_service=file_service)

        assert executor.file_service is file_service

    def test_file_service_property_raises_when_none(self):
        """Test file_service property raises RuntimeError when None."""
        session = MagicMock()
        session.chuck = None

        # Create executor and force _file_service to None
        executor = CommandExecutor(session)
        executor._file_service = None

        with pytest.raises(RuntimeError, match="FileService not available"):
            _ = executor.file_service


class TestCommandExecutorExecute:
    """Tests for CommandExecutor.execute method."""

    def test_execute_dispatches_to_handler(self):
        """Test execute dispatches to correct handler."""
        session = MagicMock()
        session.chuck = MagicMock()
        shred_service = MagicMock(spec=ShredService)
        shred_service.spork_file.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        executor = CommandExecutor(session, shred_service=shred_service)

        cmd = MagicMock()
        cmd.type = "spork_file"
        cmd.args = {"path": "test.ck"}

        result = executor.execute(cmd)

        assert result is None
        shred_service.spork_file.assert_called_once_with("test.ck")

    def test_execute_unknown_command_returns_error(self):
        """Test execute returns error for unknown command."""
        session = MagicMock()
        session.chuck = MagicMock()

        executor = CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

        cmd = MagicMock()
        cmd.type = "unknown_command"
        cmd.args = {}

        result = executor.execute(cmd)

        assert result == "Unknown command type: unknown_command"


class TestShredCommands:
    """Tests for shred-related commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()
        shred_service = MagicMock(spec=ShredService)
        globals_service = MagicMock(spec=GlobalsService)

        return CommandExecutor(
            session,
            shred_service=shred_service,
            globals_service=globals_service,
        )

    def test_spork_file_success(self, executor):
        """Test spork_file returns None on success."""
        executor._shred_service.spork_file.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_spork_file({"path": "test.ck"})

        assert result is None
        executor._shred_service.spork_file.assert_called_once_with("test.ck")

    def test_spork_file_failure(self, executor):
        """Test spork_file returns error on failure."""
        executor._shred_service.spork_file.return_value = ShredResult(
            success=False, shred_ids=[], error="File not found"
        )

        result = executor._cmd_spork_file({"path": "missing.ck"})

        assert result == "File not found"

    def test_spork_code_success(self, executor):
        """Test spork_code returns None on success."""
        executor._shred_service.spork_code.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_spork_code({"code": "SinOsc s => dac;"})

        assert result is None

    def test_remove_shred_success(self, executor):
        """Test remove_shred returns None on success."""
        executor._shred_service.remove_shred.return_value = True

        result = executor._cmd_remove_shred({"id": 1})

        assert result is None
        executor._shred_service.remove_shred.assert_called_once_with(1)

    def test_remove_shred_failure(self, executor):
        """Test remove_shred returns error on failure."""
        executor._shred_service.remove_shred.return_value = False

        result = executor._cmd_remove_shred({"id": 999})

        assert result == "Failed to remove shred 999"

    def test_abort_shred_success(self, executor):
        """Test abort_shred returns None on success."""
        executor._shred_service.remove_shred.return_value = True

        result = executor._cmd_abort_shred({"id": 1})

        assert result is None
        executor._shred_service.remove_shred.assert_called_with(1)

    def test_abort_shred_failure(self, executor):
        """Test abort_shred returns error on failure."""
        executor._shred_service.remove_shred.return_value = False

        result = executor._cmd_abort_shred({"id": 999})

        assert result == "Failed to abort shred 999"

    def test_exit_command(self, executor):
        """Test exit command returns None."""
        result = executor._cmd_exit({})

        assert result is None

    def test_remove_all(self, executor):
        """Test remove_all calls service."""
        result = executor._cmd_remove_all({})

        assert result is None
        executor._shred_service.remove_all.assert_called_once()

    def test_replace_shred_success(self, executor):
        """Test replace_shred returns None on success."""
        executor._shred_service.replace_shred.return_value = ShredResult(
            success=True, shred_ids=[2], error=None
        )

        result = executor._cmd_replace_shred({"id": 1, "code": "TriOsc t => dac;"})

        assert result is None

    def test_replace_shred_file_success(self, executor):
        """Test replace_shred_file returns None on success."""
        executor._shred_service.replace_shred_file.return_value = ShredResult(
            success=True, shred_ids=[2], error=None
        )

        result = executor._cmd_replace_shred_file({"id": 1, "path": "new.ck"})

        assert result is None

    def test_clear_vm_success(self, executor):
        """Test clear_vm returns None on success."""
        executor._shred_service.clear_vm.return_value = True

        result = executor._cmd_clear_vm({})

        assert result is None

    def test_clear_vm_failure(self, executor):
        """Test clear_vm returns error on failure."""
        executor._shred_service.clear_vm.return_value = False

        result = executor._cmd_clear_vm({})

        assert result == "Failed to clear VM"

    def test_reset_id_success(self, executor):
        """Test reset_id returns None on success."""
        executor._shred_service.reset_shred_id.return_value = True

        result = executor._cmd_reset_id({})

        assert result is None

    def test_reset_id_failure(self, executor):
        """Test reset_id returns error on failure."""
        executor._shred_service.reset_shred_id.return_value = False

        result = executor._cmd_reset_id({})

        assert result == "Failed to reset shred ID"

    def test_compile_file_success(self, executor):
        """Test compile_file returns None on success."""
        executor._shred_service.compile_file.return_value = True

        result = executor._cmd_compile_file({"path": "test.ck"})

        assert result is None

    def test_compile_file_failure(self, executor):
        """Test compile_file returns error on failure."""
        executor._shred_service.compile_file.return_value = False

        result = executor._cmd_compile_file({"path": "bad.ck"})

        assert result == "Compilation failed for bad.ck"

    def test_exec_code_success(self, executor):
        """Test exec_code returns None on success."""
        executor._shred_service.exec_code.return_value = True

        result = executor._cmd_exec_code({"code": "<<<\"hello\">>>;"})

        assert result is None

    def test_exec_code_failure(self, executor):
        """Test exec_code returns error on failure."""
        executor._shred_service.exec_code.return_value = False

        result = executor._cmd_exec_code({"code": "bad code"})

        assert result == "Execution failed"


class TestGlobalCommands:
    """Tests for global variable commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()
        shred_service = MagicMock(spec=ShredService)
        globals_service = MagicMock(spec=GlobalsService)

        return CommandExecutor(
            session,
            shred_service=shred_service,
            globals_service=globals_service,
        )

    def test_set_global_success(self, executor):
        """Test set_global returns None on success."""
        executor._globals_service.set_global.return_value = True

        result = executor._cmd_set_global({"name": "freq", "value": 440})

        assert result is None
        executor._globals_service.set_global.assert_called_once_with("freq", 440)

    def test_set_global_failure(self, executor):
        """Test set_global returns error on failure."""
        executor._globals_service.set_global.return_value = False

        result = executor._cmd_set_global({"name": "invalid", "value": 0})

        assert result == "Failed to set global 'invalid'"

    def test_get_global_int_success(self, executor):
        """Test get_global returns None on success for int."""
        executor._globals_service.get_global.return_value = ("int", 440)

        result = executor._cmd_get_global({"name": "freq"})

        assert result is None

    def test_get_global_string_success(self, executor):
        """Test get_global returns None on success for string."""
        executor._globals_service.get_global.return_value = ("string", "hello")

        result = executor._cmd_get_global({"name": "msg"})

        assert result is None

    def test_get_global_not_found(self, executor):
        """Test get_global returns error when not found."""
        executor._globals_service.get_global.return_value = None

        result = executor._cmd_get_global({"name": "missing"})

        assert result == "Global variable 'missing' not found or wrong type"

    def test_list_globals_empty(self, executor):
        """Test list_globals with no globals."""
        executor._globals_service.list_globals.return_value = []

        result = executor._cmd_list_globals({})

        assert result is None

    def test_list_globals_with_items(self, executor):
        """Test list_globals with globals defined."""
        executor._globals_service.list_globals.return_value = [
            GlobalInfo(name="freq", type="int"),
            GlobalInfo(name="gain", type="float"),
        ]

        result = executor._cmd_list_globals({})

        assert result is None

    def test_signal_event_success(self, executor):
        """Test signal_event returns None on success."""
        executor._globals_service.signal_event.return_value = True

        result = executor._cmd_signal_event({"name": "trigger"})

        assert result is None
        executor._globals_service.signal_event.assert_called_once_with("trigger")

    def test_signal_event_failure(self, executor):
        """Test signal_event returns error on failure."""
        executor._globals_service.signal_event.return_value = False

        result = executor._cmd_signal_event({"name": "bad"})

        assert result == "Failed to signal event 'bad'"

    def test_broadcast_event_success(self, executor):
        """Test broadcast_event returns None on success."""
        executor._globals_service.broadcast_event.return_value = True

        result = executor._cmd_broadcast_event({"name": "reset"})

        assert result is None

    def test_broadcast_event_failure(self, executor):
        """Test broadcast_event returns error on failure."""
        executor._globals_service.broadcast_event.return_value = False

        result = executor._cmd_broadcast_event({"name": "bad"})

        assert result == "Failed to broadcast event 'bad'"


class TestAudioCommands:
    """Tests for audio control commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()
        session.audio_running = False

        return CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

    @patch("numchuck.tui.commands.start_audio")
    def test_start_audio_success(self, mock_start, executor):
        """Test start_audio returns None on success."""
        result = executor._cmd_start_audio({})

        assert result is None
        assert executor.session.audio_running is True
        mock_start.assert_called_once()

    @patch("numchuck.tui.commands.start_audio")
    def test_start_audio_failure(self, mock_start, executor):
        """Test start_audio returns error on failure."""
        mock_start.side_effect = RuntimeError("Audio device busy")

        result = executor._cmd_start_audio({})

        assert "Failed to start audio" in result

    @patch("numchuck.tui.commands.stop_audio")
    def test_stop_audio_success(self, mock_stop, executor):
        """Test stop_audio returns None on success."""
        executor.session.audio_running = True

        result = executor._cmd_stop_audio({})

        assert result is None
        assert executor.session.audio_running is False
        mock_stop.assert_called_once()

    @patch("numchuck.tui.commands.stop_audio")
    def test_stop_audio_failure(self, mock_stop, executor):
        """Test stop_audio returns error on failure."""
        mock_stop.side_effect = OSError("Audio not running")

        result = executor._cmd_stop_audio({})

        assert "Failed to stop audio" in result

    @patch("numchuck.tui.commands.shutdown_audio")
    def test_shutdown_audio_success(self, mock_shutdown, executor):
        """Test shutdown_audio returns None on success."""
        result = executor._cmd_shutdown_audio({})

        assert result is None
        mock_shutdown.assert_called_once_with(500)


class TestInfoCommands:
    """Tests for info/status commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        mock_chuck = MagicMock()
        session.chuck = mock_chuck
        session.audio_running = False
        session.get_shred_name.return_value = "test.ck"

        return CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

    def test_status(self, executor):
        """Test status command."""
        executor._chuck.get_all_shred_ids.return_value = [1, 2]
        executor._chuck.now.return_value = 44100.0

        result = executor._cmd_status({})

        assert result is None

    def test_list_shreds_empty(self, executor):
        """Test list_shreds with no shreds."""
        executor._chuck.get_all_shred_ids.return_value = []

        result = executor._cmd_list_shreds({})

        assert result is None

    def test_list_shreds_with_items(self, executor):
        """Test list_shreds with shreds running."""
        executor._chuck.get_all_shred_ids.return_value = [1, 2]

        result = executor._cmd_list_shreds({})

        assert result is None

    def test_shred_info_success(self, executor):
        """Test shred_info returns None on success."""
        executor._chuck.get_shred_info.return_value = {
            "id": 1,
            "name": "test.ck",
            "is_running": True,
            "is_done": False,
        }

        result = executor._cmd_shred_info({"id": 1})

        assert result is None

    def test_shred_info_failure(self, executor):
        """Test shred_info returns error on failure."""
        executor._chuck.get_shred_info.side_effect = RuntimeError("Shred not found")

        result = executor._cmd_shred_info({"id": 999})

        assert "Error getting shred info" in result

    def test_current_time(self, executor):
        """Test current_time command."""
        executor._chuck.now.return_value = 88200.0

        result = executor._cmd_current_time({})

        assert result is None

    @patch("numchuck.tui.commands.audio_info")
    def test_audio_info(self, mock_audio_info, executor):
        """Test audio_info command."""
        mock_audio_info.return_value = {
            "sample_rate": 44100,
            "num_channels_out": 2,
            "num_channels_in": 0,
            "buffer_size": 512,
        }

        result = executor._cmd_audio_info({})

        assert result is None

    def test_clear_screen(self, executor, capsys):
        """Test clear_screen command."""
        result = executor._cmd_clear_screen({})

        assert result is None
        captured = capsys.readouterr()
        assert "\033[2J\033[H" in captured.out


class TestSnippetCommands:
    """Tests for snippet-related commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        from pathlib import Path

        session = MagicMock()
        session.chuck = MagicMock()
        session.shreds = {}
        shred_service = MagicMock(spec=ShredService)
        globals_service = MagicMock(spec=GlobalsService)
        file_service = MagicMock(spec=FileService)

        return CommandExecutor(
            session,
            shred_service=shred_service,
            globals_service=globals_service,
            file_service=file_service,
        )

    def test_load_snippet_not_found(self, executor):
        """Test load_snippet when snippet not found."""
        from pathlib import Path

        executor._file_service.load_snippet.return_value = None
        executor._file_service.get_snippets_dir.return_value = MagicMock(
            exists=MagicMock(return_value=True)
        )
        executor._file_service.list_snippets.return_value = []

        result = executor._cmd_load_snippet({"name": "missing"})

        assert result is None  # Returns None but logs error message
        executor._file_service.load_snippet.assert_called_once_with("missing")

    def test_load_snippet_success(self, executor):
        """Test load_snippet when snippet found."""
        from pathlib import Path

        mock_path = Path("/test/snippets/sine.ck")
        executor._file_service.load_snippet.return_value = SnippetInfo(
            name="sine", path=mock_path, source="local"
        )

        executor._shred_service.spork_file.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_load_snippet({"name": "sine"})

        assert result is None
        executor._shred_service.spork_file.assert_called_once_with(mock_path)

    def test_load_snippet_failure(self, executor):
        """Test load_snippet when sporking fails."""
        from pathlib import Path

        mock_path = Path("/test/snippets/broken.ck")
        executor._file_service.load_snippet.return_value = SnippetInfo(
            name="broken", path=mock_path, source="local"
        )

        executor._shred_service.spork_file.return_value = ShredResult(
            success=False, shred_ids=[], error="Syntax error"
        )

        result = executor._cmd_load_snippet({"name": "broken"})

        assert result == "Failed to spork snippet @broken"


class TestShellCommand:
    """Tests for shell command."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()

        return CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

    @patch("subprocess.run")
    def test_shell_command(self, mock_run, executor):
        """Test shell command execution."""
        result = executor._cmd_shell({"cmd": "echo hello"})

        assert result is None
        mock_run.assert_called_once_with("echo hello", shell=True)


class TestWatchCommands:
    """Tests for file watching commands."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()
        # No _file_watcher initially
        del session._file_watcher

        return CommandExecutor(
            session,
            shred_service=MagicMock(),
            globals_service=MagicMock(),
        )

    def test_unwatch_file_no_watcher(self, executor):
        """Test unwatch_file when no watcher exists."""
        result = executor._cmd_unwatch_file({"path": "test.ck"})

        assert result == "No files are being watched"

    def test_unwatch_all_no_watcher(self, executor):
        """Test unwatch_all when no watcher exists."""
        result = executor._cmd_unwatch_all({})

        assert result == "No files are being watched"

    def test_list_watched_no_watcher(self, executor):
        """Test list_watched when no watcher exists."""
        result = executor._cmd_list_watched({})

        assert result is None  # Returns None but logs info

    def test_list_watched_with_watcher_empty(self, executor):
        """Test list_watched with watcher but no files."""
        mock_watcher = MagicMock()
        mock_watcher.get_watched_files.return_value = []
        executor.session._file_watcher = mock_watcher

        result = executor._cmd_list_watched({})

        assert result is None

    def test_list_watched_with_files(self, executor):
        """Test list_watched with watched files."""
        from pathlib import Path

        mock_watcher = MagicMock()
        watched_file = MagicMock()
        watched_file.filepath = Path("/test/file.ck")
        watched_file.shred_id = 1
        mock_watcher.get_watched_files.return_value = [watched_file]
        mock_watcher.is_running = True
        executor.session._file_watcher = mock_watcher

        result = executor._cmd_list_watched({})

        assert result is None

    def test_unwatch_file_with_watcher(self, executor):
        """Test unwatch_file with existing watcher."""
        from pathlib import Path

        mock_watcher = MagicMock()
        mock_watcher.unwatch_file.return_value = True
        executor.session._file_watcher = mock_watcher

        result = executor._cmd_unwatch_file({"path": "test.ck"})

        assert result is None
        mock_watcher.unwatch_file.assert_called_once()

    def test_unwatch_all_with_files(self, executor):
        """Test unwatch_all with watched files."""
        from pathlib import Path

        mock_watcher = MagicMock()
        watched_file = MagicMock()
        watched_file.filepath = Path("/test/file.ck")
        mock_watcher.get_watched_files.return_value = [watched_file]
        mock_watcher.is_running = True
        executor.session._file_watcher = mock_watcher

        result = executor._cmd_unwatch_all({})

        assert result is None
        mock_watcher.unwatch_file.assert_called_once()
        mock_watcher.stop.assert_called_once()


class TestEditShredCommand:
    """Tests for edit_shred command."""

    @pytest.fixture
    def executor(self):
        """Create executor with mocked services."""
        session = MagicMock()
        session.chuck = MagicMock()
        session.shreds = {}
        shred_service = MagicMock(spec=ShredService)

        return CommandExecutor(
            session,
            shred_service=shred_service,
            globals_service=MagicMock(),
        )

    def test_edit_shred_not_found(self, executor):
        """Test edit_shred when shred not found."""
        result = executor._cmd_edit_shred({"id": 999})

        assert result == "Shred 999 not found"

    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    def test_edit_shred_no_changes(self, mock_tempfile, mock_run, executor):
        """Test edit_shred when no changes made."""
        import tempfile
        from unittest.mock import mock_open

        executor.session.shreds = {
            1: {"source": "SinOsc s => dac;", "name": "test.ck"}
        }

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test.ck"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        with patch("builtins.open", mock_open(read_data="SinOsc s => dac;")):
            with patch("os.unlink"):
                result = executor._cmd_edit_shred({"id": 1})

        assert result is None  # No changes, no error
