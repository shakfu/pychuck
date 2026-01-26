"""Tests for session recording functionality."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from numchuck.recorder import (
    RecordedAction,
    RecordedSession,
    SessionPlayer,
    SessionRecorder,
    get_recording_path,
    list_recordings,
)


class TestRecordedAction:
    """Tests for RecordedAction dataclass."""

    def test_create_action(self) -> None:
        """Test creating a recorded action."""
        action = RecordedAction(
            timestamp=1.5,
            action_type="command",
            content="+ sine.ck",
        )

        assert action.timestamp == 1.5
        assert action.action_type == "command"
        assert action.content == "+ sine.ck"

    def test_to_dict(self) -> None:
        """Test converting action to dictionary."""
        action = RecordedAction(
            timestamp=2.0,
            action_type="code",
            content="SinOsc s => dac;",
        )

        result = action.to_dict()

        assert result["timestamp"] == 2.0
        assert result["action_type"] == "code"
        assert result["content"] == "SinOsc s => dac;"

    def test_from_dict(self) -> None:
        """Test creating action from dictionary."""
        data = {
            "timestamp": 3.0,
            "action_type": "command",
            "content": "?",
        }

        action = RecordedAction.from_dict(data)

        assert action.timestamp == 3.0
        assert action.action_type == "command"
        assert action.content == "?"


class TestRecordedSession:
    """Tests for RecordedSession dataclass."""

    def test_create_session(self) -> None:
        """Test creating a recorded session."""
        session = RecordedSession(name="test_session")

        assert session.name == "test_session"
        assert len(session.actions) == 0
        assert session.created_at is not None

    def test_add_actions(self) -> None:
        """Test adding actions to a session."""
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="+ test.ck")
        )
        session.actions.append(
            RecordedAction(timestamp=1.0, action_type="code", content="SinOsc s => dac;")
        )

        assert session.action_count == 2

    def test_duration(self) -> None:
        """Test session duration calculation."""
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="a")
        )
        session.actions.append(
            RecordedAction(timestamp=5.0, action_type="command", content="b")
        )
        session.actions.append(
            RecordedAction(timestamp=3.0, action_type="command", content="c")
        )

        assert session.duration == 5.0

    def test_duration_empty(self) -> None:
        """Test duration of empty session."""
        session = RecordedSession(name="test")
        assert session.duration == 0.0

    def test_to_dict(self) -> None:
        """Test converting session to dictionary."""
        session = RecordedSession(name="test", metadata={"key": "value"})
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="test")
        )

        result = session.to_dict()

        assert result["name"] == "test"
        assert result["metadata"]["key"] == "value"
        assert len(result["actions"]) == 1

    def test_from_dict(self) -> None:
        """Test creating session from dictionary."""
        data = {
            "name": "test",
            "created_at": "2024-01-01T00:00:00",
            "actions": [
                {"timestamp": 0.0, "action_type": "command", "content": "test"}
            ],
            "metadata": {"version": "1.0"},
        }

        session = RecordedSession.from_dict(data)

        assert session.name == "test"
        assert session.created_at == "2024-01-01T00:00:00"
        assert len(session.actions) == 1
        assert session.metadata["version"] == "1.0"

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Test saving and loading a session."""
        session = RecordedSession(name="test_session")
        session.actions.append(
            RecordedAction(timestamp=1.0, action_type="command", content="+ sine.ck")
        )

        path = tmp_path / "test.json"
        session.save(path)

        loaded = RecordedSession.load(path)

        assert loaded.name == session.name
        assert len(loaded.actions) == 1
        assert loaded.actions[0].content == "+ sine.ck"


class TestSessionRecorder:
    """Tests for SessionRecorder class."""

    def test_recorder_creation(self) -> None:
        """Test creating a recorder."""
        recorder = SessionRecorder()

        assert not recorder.is_recording
        assert recorder.session_name is None

    def test_start_recording(self) -> None:
        """Test starting a recording."""
        recorder = SessionRecorder()
        recorder.start("test_session")

        assert recorder.is_recording
        assert recorder.session_name == "test_session"

    def test_start_with_metadata(self) -> None:
        """Test starting a recording with metadata."""
        recorder = SessionRecorder()
        recorder.start("test", metadata={"version": "1.0"})

        session = recorder.stop()
        assert session.metadata["version"] == "1.0"

    def test_start_already_recording_raises(self) -> None:
        """Test that starting while recording raises error."""
        recorder = SessionRecorder()
        recorder.start("test1")

        with pytest.raises(RuntimeError, match="Already recording"):
            recorder.start("test2")

        recorder.stop()

    def test_stop_recording(self) -> None:
        """Test stopping a recording."""
        recorder = SessionRecorder()
        recorder.start("test")
        session = recorder.stop()

        assert not recorder.is_recording
        assert session.name == "test"

    def test_stop_not_recording_raises(self) -> None:
        """Test that stopping when not recording raises error."""
        recorder = SessionRecorder()

        with pytest.raises(RuntimeError, match="Not currently recording"):
            recorder.stop()

    def test_record_action(self) -> None:
        """Test recording an action."""
        recorder = SessionRecorder()
        recorder.start("test")
        recorder.record_action("command", "+ sine.ck")
        session = recorder.stop()

        assert len(session.actions) == 1
        assert session.actions[0].action_type == "command"
        assert session.actions[0].content == "+ sine.ck"

    def test_record_multiple_actions(self) -> None:
        """Test recording multiple actions."""
        recorder = SessionRecorder()
        recorder.start("test")
        recorder.record_command("+ test.ck")
        recorder.record_code("SinOsc s => dac;")
        session = recorder.stop()

        assert len(session.actions) == 2
        assert session.actions[0].action_type == "command"
        assert session.actions[1].action_type == "code"

    def test_record_action_not_recording_raises(self) -> None:
        """Test that recording action when not recording raises error."""
        recorder = SessionRecorder()

        with pytest.raises(RuntimeError, match="Not currently recording"):
            recorder.record_action("command", "test")

    def test_discard(self) -> None:
        """Test discarding a recording."""
        recorder = SessionRecorder()
        recorder.start("test")
        recorder.record_action("command", "test")
        recorder.discard()

        assert not recorder.is_recording
        assert recorder.action_count == 0

    def test_elapsed_time(self) -> None:
        """Test elapsed time tracking."""
        recorder = SessionRecorder()

        # Not recording - should be 0
        assert recorder.elapsed_time == 0.0

        recorder.start("test")
        time.sleep(0.1)

        # Recording - should be > 0
        assert recorder.elapsed_time > 0.05

        recorder.stop()

    def test_action_count(self) -> None:
        """Test action count tracking."""
        recorder = SessionRecorder()

        assert recorder.action_count == 0

        recorder.start("test")
        assert recorder.action_count == 0

        recorder.record_action("command", "a")
        assert recorder.action_count == 1

        recorder.record_action("command", "b")
        assert recorder.action_count == 2

        recorder.stop()


class TestSessionPlayer:
    """Tests for SessionPlayer class."""

    def test_player_creation(self) -> None:
        """Test creating a player."""
        player = SessionPlayer()

        assert not player.is_playing
        assert not player.is_paused

    def test_load_session(self) -> None:
        """Test loading a session."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        player.load(session)

        # Should not be playing until start is called
        assert not player.is_playing

    def test_start_playback(self) -> None:
        """Test starting playback."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="test")
        )
        player.load(session)
        player.start()

        assert player.is_playing

    def test_start_no_session_raises(self) -> None:
        """Test that starting without a session raises error."""
        player = SessionPlayer()

        with pytest.raises(RuntimeError, match="No session loaded"):
            player.start()

    def test_stop_playback(self) -> None:
        """Test stopping playback."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="test")
        )
        player.load(session)
        player.start()
        player.stop()

        assert not player.is_playing

    def test_pause_resume(self) -> None:
        """Test pausing and resuming playback."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=1.0, action_type="command", content="test")
        )
        player.load(session)
        player.start()

        player.pause()
        assert player.is_paused

        player.resume()
        assert not player.is_paused

    def test_speed_setting(self) -> None:
        """Test playback speed setting."""
        player = SessionPlayer()

        player.speed = 2.0
        assert player.speed == 2.0

        # Should clamp to valid range
        player.speed = 0.01
        assert player.speed == 0.1

        player.speed = 100.0
        assert player.speed == 10.0

    def test_tick_executes_actions(self) -> None:
        """Test that tick executes actions at correct time."""
        executed = []

        def callback(action: RecordedAction) -> None:
            executed.append(action.content)

        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="first")
        )
        player.load(session)
        player.set_action_callback(callback)
        player.start(speed=10.0)  # Fast playback

        # Tick should execute immediate actions
        player.tick()

        assert "first" in executed

    def test_progress(self) -> None:
        """Test progress tracking."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="a")
        )
        session.actions.append(
            RecordedAction(timestamp=1.0, action_type="command", content="b")
        )
        player.load(session)

        assert player.progress == 0.0

        player.start(speed=10.0)
        time.sleep(0.2)

        # Should have made progress
        assert player.progress > 0.0

        player.stop()

    def test_remaining_actions(self) -> None:
        """Test remaining actions count."""
        player = SessionPlayer()
        session = RecordedSession(name="test")
        session.actions.append(
            RecordedAction(timestamp=0.0, action_type="command", content="a")
        )
        session.actions.append(
            RecordedAction(timestamp=1.0, action_type="command", content="b")
        )
        player.load(session)
        player.start(speed=10.0)

        # Execute first action
        player.tick()

        assert player.remaining_actions >= 0

        player.stop()


class TestRecordingHelpers:
    """Tests for recording helper functions."""

    def test_list_recordings_empty(self, tmp_path: Path) -> None:
        """Test listing recordings in empty directory."""
        result = list_recordings(tmp_path)
        assert result == []

    def test_list_recordings(self, tmp_path: Path) -> None:
        """Test listing recordings."""
        # Create some recording files
        (tmp_path / "session1.json").write_text("{}")
        (tmp_path / "session2.json").write_text("{}")
        (tmp_path / "not_json.txt").write_text("")

        result = list_recordings(tmp_path)

        assert "session1" in result
        assert "session2" in result
        assert "not_json" not in result

    def test_list_recordings_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test listing recordings in nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        result = list_recordings(nonexistent)
        assert result == []

    def test_get_recording_path(self, tmp_path: Path) -> None:
        """Test getting recording path."""
        result = get_recording_path(tmp_path, "my_session")
        assert result == tmp_path / "my_session.json"


class TestCommandParserRecordingCommands:
    """Tests for recording command parsing."""

    def test_parse_record_start(self) -> None:
        """Test parsing 'record start' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record start")

        assert cmd is not None
        assert cmd.type == "record_start"
        assert cmd.args["name"] is None

    def test_parse_record_start_with_name(self) -> None:
        """Test parsing 'record start name' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record start mysession")

        assert cmd is not None
        assert cmd.type == "record_start"
        assert cmd.args["name"] == "mysession"

    def test_parse_record_stop(self) -> None:
        """Test parsing 'record stop' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record stop")

        assert cmd is not None
        assert cmd.type == "record_stop"

    def test_parse_record_save(self) -> None:
        """Test parsing 'record save name' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record save mysession")

        assert cmd is not None
        assert cmd.type == "record_save"
        assert cmd.args["name"] == "mysession"

    def test_parse_record_discard(self) -> None:
        """Test parsing 'record discard' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record discard")

        assert cmd is not None
        assert cmd.type == "record_discard"

    def test_parse_record_status(self) -> None:
        """Test parsing 'record status' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("record status")

        assert cmd is not None
        assert cmd.type == "record_status"

    def test_parse_playback(self) -> None:
        """Test parsing 'playback name' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("playback mysession")

        assert cmd is not None
        assert cmd.type == "playback"
        assert cmd.args["name"] == "mysession"
        assert cmd.args["speed"] == 1.0

    def test_parse_playback_with_speed(self) -> None:
        """Test parsing 'playback name speed' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("playback mysession 2.0")

        assert cmd is not None
        assert cmd.type == "playback"
        assert cmd.args["name"] == "mysession"
        assert cmd.args["speed"] == 2.0

    def test_parse_playback_pause(self) -> None:
        """Test parsing 'playback pause' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("playback pause")

        assert cmd is not None
        assert cmd.type == "playback_pause"

    def test_parse_playback_resume(self) -> None:
        """Test parsing 'playback resume' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("playback resume")

        assert cmd is not None
        assert cmd.type == "playback_resume"

    def test_parse_playback_stop(self) -> None:
        """Test parsing 'playback stop' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("playback stop")

        assert cmd is not None
        assert cmd.type == "playback_stop"

    def test_parse_recordings_list(self) -> None:
        """Test parsing 'recordings' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("recordings")

        assert cmd is not None
        assert cmd.type == "list_recordings"
