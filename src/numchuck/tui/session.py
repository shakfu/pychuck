from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..paths import get_projects_dir
from ..recorder import SessionRecorder, SessionPlayer
from ..midi import MIDIMappings
from .project import Project
from .logging import get_logger, TUILogger

if TYPE_CHECKING:
    from .._numchuck import ChucK
    from ..osc import OSCServer, OSCController
    from ..watcher import FileWatcher


class ChuckSession:
    """Session managing ChucK instance state with optional project support.

    Tracks:
    - Active shreds with their metadata
    - Audio running state
    - Optional project for file versioning
    """

    def __init__(
        self,
        chuck: ChucK,
        project_name: str | None = None,
        logger: TUILogger | None = None,
    ) -> None:
        """Initialize session.

        Args:
            chuck: ChucK instance to track
            project_name: Optional project name for file versioning
            logger: Optional logger (uses global logger if None)
        """
        self.chuck: ChucK | None = chuck
        self.shreds: dict[int, dict[str, Any]] = {}
        self.audio_running = False
        self.project: Project | None = None
        self._logger = logger or get_logger()
        self._file_watcher: FileWatcher | None = None

        # Recording/playback state
        self.recorder: SessionRecorder = SessionRecorder()
        self.player: SessionPlayer = SessionPlayer()

        # MIDI state
        self.midi_mappings: MIDIMappings = MIDIMappings()
        self.midi_listener_shred_id: int | None = None

        # OSC state
        self.osc_server: OSCServer | None = None
        self.osc_controller: OSCController | None = None

        # Waveform display state
        self.show_waveform: bool = False

        # Initialize project if name provided
        if project_name:
            projects_dir = get_projects_dir()
            self.project = Project(project_name, projects_dir)

    def add_shred(
        self,
        shred_id: int,
        name: str,
        content: str | None = None,
        shred_type: str = "code",
    ) -> None:
        """Add a shred and optionally save to project.

        Args:
            shred_id: ChucK shred ID
            name: File name or description
            content: Optional code content (for project versioning)
            shred_type: Type of shred ('code' or 'file')
        """
        # Capture ChucK VM time when shred was created
        chuck_time = 0.0
        if self.chuck is not None:
            try:
                chuck_time = self.chuck.now()
            except (RuntimeError, AttributeError) as e:
                self._logger.debug(f"Could not get VM time: {e}")

        self.shreds[shred_id] = {
            "id": shred_id,
            "name": name,
            "time": chuck_time,  # ChucK VM time in samples
            "type": shred_type,  # 'code' or 'file'
            "source": content or name,  # Store source code or file path
        }

        # If we have a project and content, save versioned file
        if self.project and content:
            try:
                self.project.save_on_spork(name, content, shred_id)
            except OSError as e:
                self._logger.warning(f"Failed to save to project: {e}")

    def replace_shred(self, shred_id: int, content: str) -> None:
        """Replace shred and save new version to project.

        Args:
            shred_id: ChucK shred ID to replace
            content: New code content
        """
        if self.project:
            try:
                self.project.save_on_replace(shred_id, content)
            except OSError as e:
                self._logger.warning(f"Failed to save replacement to project: {e}")

    def remove_shred(self, shred_id: int) -> None:
        """Remove a shred from tracking."""
        if shred_id in self.shreds:
            self.shreds.pop(shred_id)

    def clear_shreds(self) -> None:
        """Clear all tracked shreds."""
        self.shreds.clear()

    def sync_shreds(self) -> None:
        """Synchronize tracked shreds with the VM's actual shred list.

        Discovers shreds added externally (e.g. via OTF ``chuck --add``)
        and removes stale entries for shreds that have finished or been
        removed outside the session.
        """
        if self.chuck is None:
            return
        try:
            vm_ids = set(self.chuck.get_all_shred_ids())
        except (RuntimeError, AttributeError):
            return

        session_ids = set(self.shreds.keys())

        # New in VM (OTF-added or otherwise external)
        for sid in vm_ids - session_ids:
            try:
                info = self.chuck.get_shred_info(sid)
                name = info.get("name", f"shred-{sid}")
            except (RuntimeError, KeyError):
                name = f"shred-{sid}"
            self.add_shred(sid, name, shred_type="otf")

        # Gone from VM (finished or OTF-removed)
        for sid in session_ids - vm_ids:
            self.remove_shred(sid)

    def get_shred_name(self, shred_id: int) -> str:
        """Get display name for a shred."""
        if shred_id in self.shreds:
            name: str = self.shreds[shred_id]["name"]
            return name
        return f"shred-{shred_id}"


# Backward compatibility alias
REPLSession = ChuckSession
