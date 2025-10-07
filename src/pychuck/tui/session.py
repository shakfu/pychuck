from typing import Dict, List, Optional

class ChuckSession:
    """Session managing ChucK instance state with optional project support."""

    def __init__(self, chuck, project_name: Optional[str] = None):
        self.chuck = chuck
        self.shreds: Dict[int, Dict] = {}  # id -> {'name': 'file.ck', 'time': samples}
        self.audio_running = False
        self.project = None

        # Initialize project if name provided
        if project_name:
            from .project import Project
            from .paths import get_projects_dir
            projects_dir = get_projects_dir()
            self.project = Project(project_name, projects_dir)

    def add_shred(self, shred_id: int, name: str, content: Optional[str] = None, shred_type: str = 'code'):
        """Add a shred and optionally save to project.

        Args:
            shred_id: ChucK shred ID
            name: File name or description
            content: Optional code content (for project versioning)
            shred_type: Type of shred ('code' or 'file')
        """
        # Capture ChucK VM time when shred was created
        try:
            chuck_time = self.chuck.now()
        except:
            chuck_time = 0.0

        self.shreds[shred_id] = {
            'id': shred_id,
            'name': name,
            'time': chuck_time,  # ChucK VM time in samples
            'type': shred_type,  # 'code' or 'file'
            'source': content or name  # Store source code or file path
        }

        # If we have a project and content, save versioned file
        if self.project and content:
            try:
                self.project.save_on_spork(name, content, shred_id)
            except Exception as e:
                # Don't fail if project save fails
                print(f"Warning: Failed to save to project: {e}")

    def replace_shred(self, shred_id: int, content: str):
        """Replace shred and save new version to project.

        Args:
            shred_id: ChucK shred ID to replace
            content: New code content
        """
        if self.project:
            try:
                self.project.save_on_replace(shred_id, content)
            except Exception as e:
                print(f"Warning: Failed to save replacement to project: {e}")

    def remove_shred(self, shred_id: int):
        """Remove a shred from tracking."""
        if shred_id in self.shreds:
            self.shreds.pop(shred_id)

    def clear_shreds(self):
        """Clear all tracked shreds."""
        self.shreds.clear()

    def get_shred_name(self, shred_id: int) -> str:
        """Get display name for a shred."""
        if shred_id in self.shreds:
            return self.shreds[shred_id]['name']
        return f"shred-{shred_id}"


# Backward compatibility alias
REPLSession = ChuckSession
