"""Tests for the TUI session module."""

from unittest.mock import MagicMock, patch

import pytest

from numchuck.tui.session import ChuckSession, REPLSession


class MockChuck:
    """Mock ChucK instance for testing."""

    def __init__(self, now_value: float = 44100.0):
        self._now_value = now_value

    def now(self) -> float:
        return self._now_value


class TestChuckSessionInit:
    """Test ChuckSession initialization."""

    def test_basic_initialization(self):
        """Test basic session creation without project."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        assert session.chuck is mock_chuck
        assert session.shreds == {}
        assert session.audio_running is False
        assert session.project is None

    def test_initialization_with_project_name(self, tmp_path):
        """Test session creation with project name creates Project instance."""
        mock_chuck = MockChuck()

        with patch("numchuck.tui.session.get_projects_dir", return_value=tmp_path):
            session = ChuckSession(mock_chuck, project_name="test_project")

        assert session.project is not None
        assert session.project.name == "test_project"

    def test_initialization_with_custom_logger(self):
        """Test session creation with custom logger."""
        mock_chuck = MockChuck()
        mock_logger = MagicMock()

        session = ChuckSession(mock_chuck, logger=mock_logger)

        assert session._logger is mock_logger


class TestAddShred:
    """Test add_shred method."""

    def test_add_shred_basic(self):
        """Test adding a shred with basic metadata."""
        mock_chuck = MockChuck(now_value=88200.0)
        session = ChuckSession(mock_chuck)

        session.add_shred(1, "test.ck", content="SinOsc s => dac;")

        assert 1 in session.shreds
        assert session.shreds[1]["id"] == 1
        assert session.shreds[1]["name"] == "test.ck"
        assert session.shreds[1]["time"] == 88200.0
        assert session.shreds[1]["type"] == "code"
        assert session.shreds[1]["source"] == "SinOsc s => dac;"

    def test_add_shred_file_type(self):
        """Test adding a shred with file type."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        session.add_shred(2, "/path/to/file.ck", shred_type="file")

        assert session.shreds[2]["type"] == "file"
        assert session.shreds[2]["source"] == "/path/to/file.ck"

    def test_add_shred_without_content_uses_name_as_source(self):
        """Test that source defaults to name when content is None."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        session.add_shred(3, "inline_code")

        assert session.shreds[3]["source"] == "inline_code"

    def test_add_shred_with_chuck_error(self):
        """Test adding shred when chuck.now() raises error."""
        mock_chuck = MagicMock()
        mock_chuck.now.side_effect = RuntimeError("VM not running")
        mock_logger = MagicMock()

        session = ChuckSession(mock_chuck, logger=mock_logger)
        session.add_shred(1, "test.ck")

        # Should still add shred with time=0
        assert session.shreds[1]["time"] == 0.0
        # Should log debug message
        assert mock_logger.debug.called

    def test_add_shred_with_none_chuck(self):
        """Test adding shred when chuck is None."""
        session = ChuckSession(None)
        session.add_shred(1, "test.ck")

        # Should add shred with time=0
        assert session.shreds[1]["time"] == 0.0

    def test_add_shred_saves_to_project(self, tmp_path):
        """Test that add_shred saves content to project."""
        mock_chuck = MockChuck()
        mock_project = MagicMock()

        with patch("numchuck.tui.session.get_projects_dir", return_value=tmp_path):
            session = ChuckSession(mock_chuck, project_name="test_project")
            session.project = mock_project

            session.add_shred(1, "test.ck", content="SinOsc s => dac;")

        # Verify save_on_spork was called with correct arguments
        assert mock_project.save_on_spork.call_count == 1
        call_args = mock_project.save_on_spork.call_args[0]
        assert call_args == ("test.ck", "SinOsc s => dac;", 1)

    def test_add_shred_project_save_error(self, tmp_path):
        """Test that project save errors are logged but don't raise."""
        mock_chuck = MockChuck()
        mock_project = MagicMock()
        mock_project.save_on_spork.side_effect = OSError("Disk full")
        mock_logger = MagicMock()

        with patch("numchuck.tui.session.get_projects_dir", return_value=tmp_path):
            session = ChuckSession(mock_chuck, project_name="test", logger=mock_logger)
            session.project = mock_project

            # Should not raise
            session.add_shred(1, "test.ck", content="code")

        # Should log warning
        assert mock_logger.warning.called
        assert "Failed to save to project" in mock_logger.warning.call_args[0][0]


class TestReplaceShred:
    """Test replace_shred method."""

    def test_replace_shred_with_project(self, tmp_path):
        """Test replacing shred saves to project."""
        mock_chuck = MockChuck()
        mock_project = MagicMock()

        with patch("numchuck.tui.session.get_projects_dir", return_value=tmp_path):
            session = ChuckSession(mock_chuck, project_name="test_project")
            session.project = mock_project

            session.replace_shred(1, "TriOsc t => dac;")

        # Verify save_on_replace was called with correct arguments
        assert mock_project.save_on_replace.call_count == 1
        call_args = mock_project.save_on_replace.call_args[0]
        assert call_args == (1, "TriOsc t => dac;")

    def test_replace_shred_without_project(self):
        """Test replacing shred without project does nothing."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        # Should not raise and project should remain None
        session.replace_shred(1, "code")
        assert session.project is None

    def test_replace_shred_project_save_error(self, tmp_path):
        """Test that project save errors on replace are logged."""
        mock_chuck = MockChuck()
        mock_project = MagicMock()
        mock_project.save_on_replace.side_effect = OSError("Permission denied")
        mock_logger = MagicMock()

        with patch("numchuck.tui.session.get_projects_dir", return_value=tmp_path):
            session = ChuckSession(mock_chuck, project_name="test", logger=mock_logger)
            session.project = mock_project

            # Should not raise
            session.replace_shred(1, "new code")

        # Should log warning
        assert mock_logger.warning.called
        assert "Failed to save replacement" in mock_logger.warning.call_args[0][0]


class TestRemoveShred:
    """Test remove_shred method."""

    def test_remove_existing_shred(self):
        """Test removing an existing shred."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)
        session.add_shred(1, "test.ck")
        session.add_shred(2, "test2.ck")

        session.remove_shred(1)

        assert 1 not in session.shreds
        assert 2 in session.shreds

    def test_remove_nonexistent_shred(self):
        """Test removing a shred that doesn't exist does nothing."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        # Should not raise
        session.remove_shred(999)

        assert session.shreds == {}


class TestClearShreds:
    """Test clear_shreds method."""

    def test_clear_all_shreds(self):
        """Test clearing all shreds."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)
        session.add_shred(1, "test1.ck")
        session.add_shred(2, "test2.ck")
        session.add_shred(3, "test3.ck")

        session.clear_shreds()

        assert session.shreds == {}

    def test_clear_empty_shreds(self):
        """Test clearing when no shreds exist."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        # Should not raise
        session.clear_shreds()

        assert session.shreds == {}


class TestGetShredName:
    """Test get_shred_name method."""

    def test_get_name_existing_shred(self):
        """Test getting name of an existing shred."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)
        session.add_shred(42, "my_synth.ck")

        name = session.get_shred_name(42)

        assert name == "my_synth.ck"

    def test_get_name_nonexistent_shred(self):
        """Test getting name of a nonexistent shred returns default."""
        mock_chuck = MockChuck()
        session = ChuckSession(mock_chuck)

        name = session.get_shred_name(999)

        assert name == "shred-999"


class TestSyncShreds:
    """Test sync_shreds method."""

    def test_discovers_otf_added_shreds(self):
        """Test that shreds present in VM but not session are added."""
        mock_chuck = MagicMock()
        mock_chuck.now.return_value = 44100.0
        mock_chuck.get_all_shred_ids.return_value = [1, 2, 3]
        mock_chuck.get_shred_info.side_effect = lambda sid: {"name": f"otf-{sid}.ck"}

        session = ChuckSession(mock_chuck)
        # Session only knows about shred 1
        session.add_shred(1, "local.ck")

        session.sync_shreds()

        # Shreds 2 and 3 should now be tracked
        assert 1 in session.shreds
        assert 2 in session.shreds
        assert 3 in session.shreds
        assert session.shreds[2]["name"] == "otf-2.ck"
        assert session.shreds[2]["type"] == "otf"
        assert session.shreds[3]["name"] == "otf-3.ck"

    def test_removes_stale_shreds(self):
        """Test that shreds in session but gone from VM are removed."""
        mock_chuck = MagicMock()
        mock_chuck.now.return_value = 44100.0
        mock_chuck.get_all_shred_ids.return_value = [1]

        session = ChuckSession(mock_chuck)
        session.add_shred(1, "alive.ck")
        session.add_shred(2, "finished.ck")
        session.add_shred(3, "removed.ck")

        session.sync_shreds()

        assert 1 in session.shreds
        assert 2 not in session.shreds
        assert 3 not in session.shreds

    def test_noop_when_in_sync(self):
        """Test no changes when session matches VM."""
        mock_chuck = MagicMock()
        mock_chuck.now.return_value = 44100.0
        mock_chuck.get_all_shred_ids.return_value = [1, 2]

        session = ChuckSession(mock_chuck)
        session.add_shred(1, "a.ck")
        session.add_shred(2, "b.ck")

        session.sync_shreds()

        assert len(session.shreds) == 2
        # Names should be unchanged (not overwritten)
        assert session.shreds[1]["name"] == "a.ck"
        assert session.shreds[2]["name"] == "b.ck"

    def test_graceful_on_vm_query_failure(self):
        """Test sync_shreds does not raise when VM query fails."""
        mock_chuck = MagicMock()
        mock_chuck.get_all_shred_ids.side_effect = RuntimeError("VM dead")

        session = ChuckSession(mock_chuck)
        session.add_shred(1, "existing.ck")

        # Should not raise
        session.sync_shreds()

        # Existing shreds should be untouched
        assert 1 in session.shreds

    def test_graceful_on_shred_info_failure(self):
        """Test sync_shreds handles get_shred_info failure gracefully."""
        mock_chuck = MagicMock()
        mock_chuck.now.return_value = 44100.0
        mock_chuck.get_all_shred_ids.return_value = [1, 2]
        mock_chuck.get_shred_info.side_effect = RuntimeError("shred gone")

        session = ChuckSession(mock_chuck)

        session.sync_shreds()

        # Should still add shreds with fallback names
        assert 1 in session.shreds
        assert 2 in session.shreds
        assert session.shreds[1]["name"] == "shred-1"
        assert session.shreds[2]["name"] == "shred-2"

    def test_noop_when_chuck_is_none(self):
        """Test sync_shreds does nothing when chuck is None."""
        session = ChuckSession(None)
        session.shreds[1] = {"id": 1, "name": "ghost.ck", "time": 0, "type": "code", "source": "ghost.ck"}

        session.sync_shreds()

        # Shreds unchanged -- no crash
        assert 1 in session.shreds


class TestBackwardCompatibility:
    """Test backward compatibility alias."""

    def test_repl_session_alias(self):
        """Test that REPLSession is an alias for ChuckSession."""
        assert REPLSession is ChuckSession

    def test_repl_session_creates_chuck_session(self):
        """Test that REPLSession can be used to create sessions."""
        mock_chuck = MockChuck()
        session = REPLSession(mock_chuck)

        assert isinstance(session, ChuckSession)
