"""
Project management for livecoding sessions.

Handles versioning scheme: file.ck → file-1.ck → file-1-1.ck
"""
from pathlib import Path
from typing import Optional, Tuple
import time


class ProjectVersion:
    """Represents a versioned file in a project."""

    def __init__(self, base_name: str, shred_id: Optional[int] = None,
                 replace_version: Optional[int] = None):
        self.base_name = base_name  # e.g., "mysynth.ck"
        self.shred_id = shred_id     # e.g., 1 (from first spork)
        self.replace_version = replace_version  # e.g., 2 (from second replace)

    def filename(self) -> str:
        """Generate filename based on versioning scheme."""
        name, ext = self.base_name.rsplit('.', 1) if '.' in self.base_name else (self.base_name, 'ck')

        if self.shred_id is None:
            return f"{name}.{ext}"
        elif self.replace_version is None:
            return f"{name}-{self.shred_id}.{ext}"
        else:
            return f"{name}-{self.shred_id}-{self.replace_version}.{ext}"

    def next_replace(self) -> 'ProjectVersion':
        """Get next replacement version."""
        next_ver = 1 if self.replace_version is None else self.replace_version + 1
        return ProjectVersion(self.base_name, self.shred_id, next_ver)

    @classmethod
    def from_filename(cls, filename: str) -> 'ProjectVersion':
        """Parse filename to extract version info."""
        # Parse: mysynth-1-2.ck → base="mysynth.ck", shred=1, replace=2
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, 'ck')
        parts = name.split('-')

        if len(parts) == 1:
            return cls(f"{parts[0]}.{ext}", None, None)
        elif len(parts) == 2:
            try:
                return cls(f"{parts[0]}.{ext}", int(parts[1]), None)
            except ValueError:
                # If second part is not a number, treat as part of name
                return cls(f"{name}.{ext}", None, None)
        else:
            try:
                return cls(f"{parts[0]}.{ext}", int(parts[1]), int(parts[2]))
            except ValueError:
                # If parts are not numbers, treat as part of name
                return cls(f"{name}.{ext}", None, None)


class Project:
    """Manages a livecoding project with versioned files."""

    def __init__(self, name: str, projects_dir: Path):
        self.name = name
        self.project_dir = projects_dir / name
        self.project_dir.mkdir(parents=True, exist_ok=True)

        # Track shred ID → current version for each file
        self.shred_versions = {}  # shred_id → ProjectVersion

    def save_on_spork(self, filename: str, content: str, shred_id: int) -> Path:
        """Save file when sporked with new shred ID."""
        version = ProjectVersion(filename, shred_id)
        self.shred_versions[shred_id] = version

        filepath = self.project_dir / version.filename()
        filepath.write_text(content)
        return filepath

    def save_on_replace(self, shred_id: int, content: str) -> Path:
        """Save file when shred is replaced."""
        if shred_id not in self.shred_versions:
            raise ValueError(f"Shred {shred_id} not found in project")

        # Get next replacement version
        current = self.shred_versions[shred_id]
        next_version = current.next_replace()
        self.shred_versions[shred_id] = next_version

        filepath = self.project_dir / next_version.filename()
        filepath.write_text(content)
        return filepath

    def save_original(self, filename: str, content: str) -> Path:
        """Save original file (not yet sporked)."""
        filepath = self.project_dir / filename
        filepath.write_text(content)
        return filepath

    def list_versions(self) -> list[Path]:
        """List all versioned files in project."""
        return sorted(self.project_dir.glob("*.ck"))

    def get_timeline(self) -> list[dict]:
        """Get chronological timeline of all versions."""
        files = []
        for path in self.list_versions():
            version = ProjectVersion.from_filename(path.name)
            files.append({
                'filename': path.name,
                'base': version.base_name,
                'shred_id': version.shred_id,
                'replace_version': version.replace_version,
                'mtime': path.stat().st_mtime
            })

        # Sort by modification time
        return sorted(files, key=lambda x: x['mtime'])
