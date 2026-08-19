"""
File operations service.

Provides operations for loading snippets and managing project files.
Used by both CLI and TUI components.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from ..paths import (
    ensure_numchuck_directories,
    get_snippet_path_with_source,
    get_snippets_dir,
    list_all_snippets,
)

if TYPE_CHECKING:
    from ..tui.session import ChuckSession


class Logger(Protocol):
    """Protocol for logger interface."""

    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str, exc: Exception | None = None) -> None: ...


class NullLogger:
    """No-op logger for when no logger is provided."""

    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str, exc: Exception | None = None) -> None:
        pass


@dataclass
class SnippetInfo:
    """Information about a snippet."""

    name: str
    path: Path
    source: str  # "local" or "global"
    content: str | None = None


class FileService:
    """Manages file operations for snippets and projects.

    Provides operations for loading and listing snippets,
    and integrating with project file versioning.

    Usage:
        files = FileService(session)
        snippet = files.load_snippet("sine")
        if snippet:
            print(f"Loaded: {snippet.path}")
    """

    def __init__(
        self,
        session: ChuckSession | None = None,
        logger: Logger | None = None,
    ) -> None:
        """Initialize FileService.

        Args:
            session: Optional session for project integration
            logger: Optional logger for messages
        """
        self._session = session
        self._logger: Logger = logger or NullLogger()

    @property
    def session(self) -> ChuckSession | None:
        """Get the session, if any."""
        return self._session

    def load_snippet(self, name: str) -> SnippetInfo | None:
        """Load a snippet by name.

        Searches local snippets first, then global snippets.

        Args:
            name: Name of the snippet (without .ck extension)

        Returns:
            SnippetInfo or None if not found
        """
        snippet_path, source = get_snippet_path_with_source(name)

        if snippet_path is None:
            return None

        # Read content
        content: str | None = None
        try:
            content = snippet_path.read_text()
        except (OSError, UnicodeDecodeError) as e:
            self._logger.warning(f"Could not read snippet content: {e}")

        return SnippetInfo(
            name=name,
            path=snippet_path,
            source=source or "local",
            content=content,
        )

    def list_snippets(self) -> list[SnippetInfo]:
        """List all available snippets.

        Returns:
            List of SnippetInfo objects
        """
        all_snippets = list_all_snippets()
        result = []

        for snippet_name, source in all_snippets:
            snippet_path, _ = get_snippet_path_with_source(snippet_name)
            if snippet_path:
                result.append(
                    SnippetInfo(
                        name=snippet_name,
                        path=snippet_path,
                        source=source,
                    )
                )

        return result

    def get_snippets_dir(self) -> Path:
        """Get the snippets directory path.

        Returns:
            Path to snippets directory
        """
        return get_snippets_dir()

    def ensure_directories(self) -> bool:
        """Ensure numchuck directories exist.

        Creates snippets and projects directories if needed.

        Returns:
            True if successful
        """
        try:
            ensure_numchuck_directories()
            return True
        except OSError as e:
            self._logger.error(f"Could not create directories: {e}")
            return False

    def save_to_project(self, name: str, content: str, shred_id: int) -> bool:
        """Save content to project with versioning.

        Args:
            name: Name for the file
            content: Content to save
            shred_id: Associated shred ID

        Returns:
            True if saved successfully
        """
        if self._session is None or self._session.project is None:
            return False

        try:
            self._session.project.save_on_spork(name, content, shred_id)
            return True
        except OSError as e:
            self._logger.error(f"Failed to save to project: {e}")
            return False

    def save_replacement_to_project(self, shred_id: int, content: str) -> bool:
        """Save replacement content to project.

        Args:
            shred_id: Shred ID being replaced
            content: New content

        Returns:
            True if saved successfully
        """
        if self._session is None or self._session.project is None:
            return False

        try:
            self._session.project.save_on_replace(shred_id, content)
            return True
        except OSError as e:
            self._logger.error(f"Failed to save replacement to project: {e}")
            return False

    def read_file(self, path: str | Path) -> str | None:
        """Read a file's content.

        Args:
            path: Path to the file

        Returns:
            File content or None if error
        """
        try:
            return Path(path).read_text()
        except (OSError, UnicodeDecodeError) as e:
            self._logger.warning(f"Could not read file {path}: {e}")
            return None
