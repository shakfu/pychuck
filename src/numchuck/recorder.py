"""
Session recording and playback for numchuck.

Provides the ability to record sessions (commands and code)
and play them back for demonstrations or reproducibility.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    pass


@dataclass
class RecordedAction:
    """A single recorded action in a session.

    Attributes:
        timestamp: Time offset from session start in seconds
        action_type: Type of action - "command" or "code"
        content: The command or code that was executed
    """

    timestamp: float
    action_type: str  # "command" or "code"
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecordedAction":
        """Create from dictionary."""
        return cls(
            timestamp=data["timestamp"],
            action_type=data["action_type"],
            content=data["content"],
        )


@dataclass
class RecordedSession:
    """A complete recorded REPL session.

    Attributes:
        name: Session name
        created_at: When the session was created
        actions: List of recorded actions
        metadata: Optional metadata (e.g., audio settings)
    """

    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    actions: list[RecordedAction] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RecordedSession":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            created_at=data.get("created_at", ""),
            actions=[RecordedAction.from_dict(a) for a in data.get("actions", [])],
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Path) -> None:
        """Save session to a JSON file.

        Args:
            path: Path to save to
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "RecordedSession":
        """Load session from a JSON file.

        Args:
            path: Path to load from

        Returns:
            Loaded RecordedSession

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is invalid JSON
        """
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    @property
    def duration(self) -> float:
        """Get total duration of the recording in seconds."""
        if not self.actions:
            return 0.0
        return max(a.timestamp for a in self.actions)

    @property
    def action_count(self) -> int:
        """Get number of actions in the recording."""
        return len(self.actions)


class SessionRecorder:
    """Records REPL session actions.

    Usage:
        >>> recorder = SessionRecorder()
        >>> recorder.start("my_session")
        >>> recorder.record_action("command", "+ sine.ck")
        >>> recorder.record_action("code", "SinOsc s => dac;")
        >>> session = recorder.stop()
        >>> session.save(Path("my_session.json"))
    """

    def __init__(self) -> None:
        """Initialize the recorder."""
        self._session: RecordedSession | None = None
        self._start_time: float = 0.0
        self._is_recording: bool = False

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    @property
    def session_name(self) -> str | None:
        """Get current session name, or None if not recording."""
        return self._session.name if self._session else None

    def start(self, name: str, metadata: dict | None = None) -> None:
        """Start recording a new session.

        Args:
            name: Session name
            metadata: Optional metadata to include

        Raises:
            RuntimeError: If already recording
        """
        if self._is_recording:
            raise RuntimeError("Already recording a session")

        self._session = RecordedSession(
            name=name,
            metadata=metadata or {},
        )
        self._start_time = time.time()
        self._is_recording = True

    def stop(self) -> RecordedSession:
        """Stop recording and return the session.

        Returns:
            The recorded session

        Raises:
            RuntimeError: If not recording
        """
        if not self._is_recording or self._session is None:
            raise RuntimeError("Not currently recording")

        session = self._session
        self._session = None
        self._is_recording = False
        self._start_time = 0.0
        return session

    def record_action(self, action_type: str, content: str) -> None:
        """Record an action.

        Args:
            action_type: Type of action ("command" or "code")
            content: The command or code content

        Raises:
            RuntimeError: If not recording
        """
        if not self._is_recording or self._session is None:
            raise RuntimeError("Not currently recording")

        timestamp = time.time() - self._start_time
        action = RecordedAction(
            timestamp=timestamp,
            action_type=action_type,
            content=content,
        )
        self._session.actions.append(action)

    def record_command(self, command: str) -> None:
        """Convenience method to record a command.

        Args:
            command: The command string
        """
        self.record_action("command", command)

    def record_code(self, code: str) -> None:
        """Convenience method to record ChucK code.

        Args:
            code: The ChucK code string
        """
        self.record_action("code", code)

    def discard(self) -> None:
        """Discard the current recording without saving."""
        self._session = None
        self._is_recording = False
        self._start_time = 0.0

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since recording started."""
        if not self._is_recording:
            return 0.0
        return time.time() - self._start_time

    @property
    def action_count(self) -> int:
        """Get number of actions recorded so far."""
        if self._session is None:
            return 0
        return len(self._session.actions)


class SessionPlayer:
    """Plays back recorded sessions.

    Usage:
        >>> player = SessionPlayer()
        >>> session = RecordedSession.load(Path("my_session.json"))
        >>> player.load(session)
        >>> player.set_action_callback(execute_action)
        >>> player.start()
        >>> while player.is_playing:
        >>>     player.tick()
        >>>     time.sleep(0.01)
    """

    def __init__(self) -> None:
        """Initialize the player."""
        self._session: RecordedSession | None = None
        self._start_time: float = 0.0
        self._speed: float = 1.0
        self._is_playing: bool = False
        self._current_index: int = 0
        self._action_callback: Callable[[RecordedAction], None] | None = None
        self._paused: bool = False
        self._pause_time: float = 0.0

    @property
    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        """Check if playback is paused."""
        return self._paused

    @property
    def speed(self) -> float:
        """Get current playback speed."""
        return self._speed

    @speed.setter
    def speed(self, value: float) -> None:
        """Set playback speed (e.g., 2.0 for 2x speed)."""
        self._speed = max(0.1, min(10.0, value))

    def load(self, session: RecordedSession) -> None:
        """Load a session for playback.

        Args:
            session: Session to load
        """
        self._session = session
        self._current_index = 0

    def set_action_callback(self, callback: Callable[[RecordedAction], None]) -> None:
        """Set the callback for when actions should be executed.

        Args:
            callback: Function to call with each action
        """
        self._action_callback = callback

    def start(self, speed: float = 1.0) -> None:
        """Start playback.

        Args:
            speed: Playback speed multiplier (default: 1.0)

        Raises:
            RuntimeError: If no session loaded
        """
        if self._session is None:
            raise RuntimeError("No session loaded")

        self._speed = speed
        self._start_time = time.time()
        self._current_index = 0
        self._is_playing = True
        self._paused = False

    def stop(self) -> None:
        """Stop playback."""
        self._is_playing = False
        self._paused = False

    def pause(self) -> None:
        """Pause playback."""
        if self._is_playing and not self._paused:
            self._paused = True
            self._pause_time = time.time()

    def resume(self) -> None:
        """Resume paused playback."""
        if self._is_playing and self._paused:
            # Adjust start time to account for pause duration
            pause_duration = time.time() - self._pause_time
            self._start_time += pause_duration
            self._paused = False

    def tick(self) -> bool:
        """Process one tick of playback.

        Should be called regularly (e.g., in a loop or timer).

        Returns:
            True if playback is still active, False if finished
        """
        if not self._is_playing or self._session is None:
            return False

        if self._paused:
            return True

        # Calculate current playback position
        elapsed = (time.time() - self._start_time) * self._speed

        # Execute any actions that should have occurred by now
        while self._current_index < len(self._session.actions):
            action = self._session.actions[self._current_index]
            if action.timestamp <= elapsed:
                if self._action_callback:
                    self._action_callback(action)
                self._current_index += 1
            else:
                break

        # Check if playback is complete
        if self._current_index >= len(self._session.actions):
            self._is_playing = False
            return False

        return True

    def skip_to(self, timestamp: float) -> None:
        """Skip to a specific timestamp in the recording.

        Args:
            timestamp: Target timestamp in seconds
        """
        if self._session is None:
            return

        # Find the appropriate action index
        for i, action in enumerate(self._session.actions):
            if action.timestamp > timestamp:
                self._current_index = i
                break
        else:
            self._current_index = len(self._session.actions)

        # Adjust start time
        self._start_time = time.time() - (timestamp / self._speed)

    @property
    def current_timestamp(self) -> float:
        """Get current playback timestamp."""
        if not self._is_playing:
            return 0.0
        return (time.time() - self._start_time) * self._speed

    @property
    def progress(self) -> float:
        """Get playback progress (0.0 to 1.0)."""
        if self._session is None or self._session.duration == 0:
            return 0.0
        return min(1.0, self.current_timestamp / self._session.duration)

    @property
    def remaining_actions(self) -> int:
        """Get number of remaining actions."""
        if self._session is None:
            return 0
        return len(self._session.actions) - self._current_index


def list_recordings(recordings_dir: Path) -> list[str]:
    """List all available recordings.

    Args:
        recordings_dir: Directory containing recordings

    Returns:
        List of recording names (without .json extension)
    """
    if not recordings_dir.exists():
        return []
    return sorted(f.stem for f in recordings_dir.glob("*.json"))


def get_recording_path(recordings_dir: Path, name: str) -> Path:
    """Get the path for a recording by name.

    Args:
        recordings_dir: Directory containing recordings
        name: Recording name (without .json extension)

    Returns:
        Path to the recording file
    """
    return recordings_dir / f"{name}.json"
