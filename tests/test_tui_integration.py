"""Integration tests for TUI components.

Tests the integration between TUI (editor/REPL) and the service layer,
verifying that UI actions correctly call services and update state.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from numchuck.services import ShredService, GlobalsService, FileService, ShredResult
from numchuck.services.files import SnippetInfo


class TestEditorServiceIntegration:
    """Test editor integration with services.

    Note: Full UI key binding tests require a complete prompt_toolkit setup.
    These tests focus on verifying the service layer integration through
    direct method calls and mock objects.
    """

    @pytest.fixture
    def mock_chuck_app(self):
        """Create a mocked ChuckApplication with services."""
        with patch("numchuck.tui.common.ChucK") as mock_chuck_class:
            with patch("numchuck.tui.common.get_logger"):
                mock_chuck = MagicMock()
                mock_chuck_class.return_value = mock_chuck

                from numchuck.tui.common import ChuckApplication

                app = ChuckApplication()

                # Mock the services
                app._shred_service = MagicMock(spec=ShredService)
                app._globals_service = MagicMock(spec=GlobalsService)
                app._file_service = MagicMock(spec=FileService)

                yield app

    def test_shred_service_spork_code(self, mock_chuck_app):
        """Test ShredService.spork_code integration."""
        mock_chuck_app._shred_service.spork_code.return_value = ShredResult(
            success=True, shred_ids=[42], error=None
        )

        result = mock_chuck_app.shred_service.spork_code(
            "SinOsc s => dac;", name="test.ck"
        )

        assert result.success
        assert result.shred_id == 42
        mock_chuck_app._shred_service.spork_code.assert_called_once_with(
            "SinOsc s => dac;", name="test.ck"
        )

    def test_shred_service_spork_failure(self, mock_chuck_app):
        """Test ShredService.spork_code failure handling."""
        mock_chuck_app._shred_service.spork_code.return_value = ShredResult(
            success=False, shred_ids=[], error="Syntax error line 1"
        )

        result = mock_chuck_app.shred_service.spork_code(
            "invalid code", name="broken.ck"
        )

        assert not result.success
        assert result.shred_id is None
        assert "Syntax error" in result.error

    def test_shred_service_replace_shred(self, mock_chuck_app):
        """Test ShredService.replace_shred integration."""
        mock_chuck_app._shred_service.replace_shred.return_value = ShredResult(
            success=True, shred_ids=[43], error=None
        )

        result = mock_chuck_app.shred_service.replace_shred(
            42, "SinOsc s => dac; 440 => s.freq;", name="test.ck"
        )

        assert result.success
        assert result.shred_id == 43
        mock_chuck_app._shred_service.replace_shred.assert_called_once_with(
            42, "SinOsc s => dac; 440 => s.freq;", name="test.ck"
        )


class TestREPLServiceIntegration:
    """Test REPL integration with services."""

    @pytest.fixture
    def mock_chuck_app(self):
        """Create a mocked ChuckApplication with services."""
        with patch("numchuck.tui.common.ChucK") as mock_chuck_class:
            with patch("numchuck.tui.common.get_logger"):
                mock_chuck = MagicMock()
                mock_chuck_class.return_value = mock_chuck

                from numchuck.tui.common import ChuckApplication

                app = ChuckApplication()

                # Mock the services
                app._shred_service = MagicMock(spec=ShredService)
                app._globals_service = MagicMock(spec=GlobalsService)
                app._file_service = MagicMock(spec=FileService)

                yield app

    def test_shred_service_accessible(self, mock_chuck_app):
        """Test that ShredService is accessible through ChuckApplication."""
        # Test through the shred_service property
        service = mock_chuck_app.shred_service

        assert service is mock_chuck_app._shred_service


class TestChuckApplicationServiceAccess:
    """Test ChuckApplication service property access patterns."""

    @pytest.fixture
    def app(self):
        """Create ChuckApplication with mocked ChucK."""
        with patch("numchuck.tui.common.ChucK") as mock_chuck_class:
            with patch("numchuck.tui.common.get_logger"):
                mock_chuck = MagicMock()
                mock_chuck_class.return_value = mock_chuck

                from numchuck.tui.common import ChuckApplication

                yield ChuckApplication()

    def test_all_services_lazily_created(self, app):
        """Test that all services are None until accessed."""
        assert app._shred_service is None
        assert app._globals_service is None
        assert app._file_service is None

    def test_services_created_on_access(self, app):
        """Test that services are created when properties accessed."""
        # Access each service
        shred = app.shred_service
        globals_ = app.globals_service
        files = app.file_service

        # All should now exist
        assert app._shred_service is not None
        assert app._globals_service is not None
        assert app._file_service is not None

        # Should be the same instances
        assert shred is app._shred_service
        assert globals_ is app._globals_service
        assert files is app._file_service

    def test_services_cached_between_accesses(self, app):
        """Test that services are cached and reused."""
        shred1 = app.shred_service
        shred2 = app.shred_service

        globals1 = app.globals_service
        globals2 = app.globals_service

        files1 = app.file_service
        files2 = app.file_service

        assert shred1 is shred2
        assert globals1 is globals2
        assert files1 is files2


class TestCommandExecutorServiceIntegration:
    """Test CommandExecutor integration with services."""

    @pytest.fixture
    def executor(self):
        """Create CommandExecutor with mocked services."""
        from numchuck.tui.commands import CommandExecutor

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

    def test_spork_file_uses_shred_service(self, executor):
        """Test spork_file command uses ShredService."""
        executor._shred_service.spork_file.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_spork_file({"path": "test.ck"})

        assert result is None
        executor._shred_service.spork_file.assert_called_once()

    def test_spork_code_uses_shred_service(self, executor):
        """Test spork_code command uses ShredService."""
        executor._shred_service.spork_code.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_spork_code({"code": "SinOsc s => dac;"})

        assert result is None
        # _cmd_spork_code calls spork_code without name parameter
        executor._shred_service.spork_code.assert_called_once_with("SinOsc s => dac;")

    def test_remove_shred_uses_shred_service(self, executor):
        """Test remove_shred command uses ShredService."""
        executor._shred_service.remove_shred.return_value = True

        # _cmd_remove_shred uses args["id"] not args["shred_id"]
        result = executor._cmd_remove_shred({"id": 42})

        assert result is None
        executor._shred_service.remove_shred.assert_called_once_with(42)

    def test_set_global_uses_globals_service(self, executor):
        """Test set_global command uses GlobalsService."""
        executor._globals_service.set_global.return_value = True

        result = executor._cmd_set_global({"name": "volume", "value": 100})

        assert result is None
        # _cmd_set_global calls set_global (not set_global_int)
        executor._globals_service.set_global.assert_called_once_with("volume", 100)

    def test_load_snippet_uses_file_service(self, executor):
        """Test load_snippet command uses FileService."""
        mock_path = Path("/test/snippets/sine.ck")
        executor._file_service.load_snippet.return_value = SnippetInfo(
            name="sine", path=mock_path, source="local"
        )
        executor._shred_service.spork_file.return_value = ShredResult(
            success=True, shred_ids=[1], error=None
        )

        result = executor._cmd_load_snippet({"name": "sine"})

        assert result is None
        executor._file_service.load_snippet.assert_called_once_with("sine")
        executor._shred_service.spork_file.assert_called_once_with(mock_path)


class TestEditorTabIntegration:
    """Test EditorTab integration patterns."""

    def test_tab_tracks_shred_id(self):
        """Test that EditorTab properly tracks shred ID."""
        from numchuck.tui.editor import EditorTab

        with patch.object(Path, "exists", return_value=False):
            tab = EditorTab()

        assert tab.shred_id is None

        # Simulate sporking
        tab.shred_id = 42

        assert tab.shred_id == 42
        # Display name format is "untitled-{shred_id}.ck"
        assert "-42." in tab.display_name
        assert tab.display_name == "untitled-42.ck"

    def test_tab_tracks_modified_state(self):
        """Test that EditorTab tracks modified state."""
        from numchuck.tui.editor import EditorTab

        with patch.object(Path, "exists", return_value=False):
            tab = EditorTab()

        assert tab.modified is False

        # Simulate edit
        tab.text_area.buffer.text = "modified content"

        assert tab.modified is True
