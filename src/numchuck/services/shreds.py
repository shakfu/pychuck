"""
Shred management service.

Provides operations for sporking, replacing, and removing ChucK shreds.
Used by both CLI and TUI components.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .._numchuck import ChucK
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
class ShredResult:
    """Result of a shred operation."""

    success: bool
    shred_ids: list[int]
    error: str | None = None

    @property
    def shred_id(self) -> int | None:
        """Get the first shred ID, or None if empty."""
        return self.shred_ids[0] if self.shred_ids else None


@dataclass
class ShredInfo:
    """Information about a shred."""

    id: int
    name: str
    is_running: bool
    is_done: bool


class ShredService:
    """Manages shred lifecycle for ChucK instances.

    Provides operations for sporking, replacing, and removing shreds
    with proper session tracking.

    Usage:
        shreds = ShredService(chuck, session)
        result = shreds.spork_code("SinOsc s => dac; second => now;")
        if result.success:
            print(f"Sporked shred {result.shred_id}")
    """

    def __init__(
        self,
        chuck: ChucK,
        session: ChuckSession | None = None,
        logger: Logger | None = None,
    ) -> None:
        """Initialize ShredService.

        Args:
            chuck: ChucK instance to manage
            session: Optional session for shred tracking
            logger: Optional logger for messages
        """
        self._chuck = chuck
        self._session = session
        self._logger: Logger = logger or NullLogger()

    @property
    def chuck(self) -> ChucK:
        """Get the managed ChucK instance."""
        return self._chuck

    @property
    def session(self) -> ChuckSession | None:
        """Get the session, if any."""
        return self._session

    def spork_code(self, code: str, name: str | None = None) -> ShredResult:
        """Spork inline ChucK code.

        Args:
            code: ChucK code to compile and run
            name: Optional name for the shred (defaults to "code-{id}")

        Returns:
            ShredResult with success status and shred IDs
        """
        try:
            success, shred_ids = self._chuck.compile_code(code)
            if success and shred_ids:
                for sid in shred_ids:
                    shred_name = name or f"code-{sid}"
                    if self._session:
                        self._session.add_shred(
                            sid, shred_name, content=code, shred_type="code"
                        )
                    self._logger.info(f"Sporked code -> shred {sid}")
                return ShredResult(success=True, shred_ids=list(shred_ids))
            else:
                return ShredResult(
                    success=False, shred_ids=[], error="Failed to spork code"
                )
        except Exception as e:
            self._logger.error(f"Error sporking code: {e}")
            return ShredResult(success=False, shred_ids=[], error=str(e))

    def spork_file(self, path: str | Path) -> ShredResult:
        """Spork a ChucK file.

        Args:
            path: Path to the ChucK file

        Returns:
            ShredResult with success status and shred IDs
        """
        import os

        path = Path(path)
        abs_path = os.path.abspath(str(path))

        # Read file content for project versioning
        content: str | None = None
        try:
            content = path.read_text()
        except (OSError, UnicodeDecodeError) as e:
            self._logger.warning(f"Could not read file content: {e}")

        try:
            success, shred_ids = self._chuck.compile_file(str(path))
            if success and shred_ids:
                for sid in shred_ids:
                    if self._session:
                        self._session.add_shred(
                            sid, abs_path, content=content, shred_type="file"
                        )
                    self._logger.info(f"Sporked {path} -> shred {sid}")
                return ShredResult(success=True, shred_ids=list(shred_ids))
            else:
                return ShredResult(
                    success=False, shred_ids=[], error=f"Failed to spork {path}"
                )
        except Exception as e:
            self._logger.error(f"Error sporking file {path}: {e}")
            return ShredResult(success=False, shred_ids=[], error=str(e))

    def replace_shred(
        self, shred_id: int, code: str, name: str | None = None
    ) -> ShredResult:
        """Replace a shred with new code.

        Args:
            shred_id: ID of the shred to replace
            code: New ChucK code
            name: Optional name for the new shred

        Returns:
            ShredResult with success status and new shred ID
        """
        try:
            new_id = self._chuck.replace_shred(shred_id, code)
            if new_id > 0:
                # Save replacement to project if available
                if self._session and self._session.project:
                    self._session.replace_shred(shred_id, code)

                if self._session:
                    self._session.remove_shred(shred_id)
                    shred_name = name or f"code-{new_id}"
                    self._session.add_shred(
                        new_id, shred_name, content=code, shred_type="code"
                    )

                self._logger.info(f"Replaced shred {shred_id} -> {new_id}")
                return ShredResult(success=True, shred_ids=[new_id])
            else:
                return ShredResult(
                    success=False,
                    shred_ids=[],
                    error=f"Failed to replace shred {shred_id}",
                )
        except RuntimeError as e:
            self._logger.error(f"Error replacing shred {shred_id}: {e}")
            return ShredResult(success=False, shred_ids=[], error=str(e))

    def replace_shred_file(
        self, shred_id: int, path: str | Path, name: str | None = None
    ) -> ShredResult:
        """Replace a shred with code from a file.

        Args:
            shred_id: ID of the shred to replace
            path: Path to the ChucK file with new code
            name: Optional name for the new shred (defaults to filepath)

        Returns:
            ShredResult with success status and new shred ID
        """
        try:
            path = Path(path)
            code = path.read_text()
            shred_name = name or str(path)

            new_id = self._chuck.replace_shred(shred_id, code)
            if new_id > 0:
                if self._session:
                    self._session.remove_shred(shred_id)
                    # Save to project if available
                    if self._session.project:
                        self._session.replace_shred(new_id, code)
                    self._session.add_shred(new_id, shred_name, shred_type="file")

                self._logger.info(f"Replaced shred {shred_id} with {path} -> {new_id}")
                return ShredResult(success=True, shred_ids=[new_id])
            else:
                return ShredResult(
                    success=False,
                    shred_ids=[],
                    error=f"Failed to replace shred {shred_id}",
                )
        except (RuntimeError, OSError) as e:
            self._logger.error(f"Error replacing shred {shred_id} with {path}: {e}")
            return ShredResult(success=False, shred_ids=[], error=str(e))

    def remove_shred(self, shred_id: int) -> bool:
        """Remove a shred by ID.

        Args:
            shred_id: ID of the shred to remove

        Returns:
            True if removed successfully
        """
        try:
            self._chuck.remove_shred(shred_id)
            if self._session:
                self._session.remove_shred(shred_id)
            self._logger.info(f"Removed shred {shred_id}")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to remove shred {shred_id}: {e}")
            return False

    def remove_all(self) -> bool:
        """Remove all shreds.

        Returns:
            True if successful
        """
        try:
            self._chuck.remove_all_shreds()
            if self._session:
                self._session.clear_shreds()
            self._logger.info("Removed all shreds")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to remove all shreds: {e}")
            return False

    def clear_vm(self) -> bool:
        """Clear the VM (remove all shreds).

        Returns:
            True if successful
        """
        try:
            self._chuck.clear_vm()
            if self._session:
                self._session.clear_shreds()
            self._logger.info("VM cleared")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to clear VM: {e}")
            return False

    def reset_shred_id(self) -> bool:
        """Reset the shred ID counter.

        Returns:
            True if successful
        """
        try:
            self._chuck.reset_shred_id()
            self._logger.info("Shred ID reset")
            return True
        except RuntimeError as e:
            self._logger.error(f"Failed to reset shred ID: {e}")
            return False

    def list_shreds(self) -> list[int]:
        """Get list of all running shred IDs.

        Returns:
            List of shred IDs
        """
        try:
            return list(self._chuck.get_all_shred_ids())
        except RuntimeError:
            return []

    def get_shred_info(self, shred_id: int) -> ShredInfo | None:
        """Get information about a specific shred.

        Args:
            shred_id: ID of the shred

        Returns:
            ShredInfo or None if not found
        """
        try:
            info = self._chuck.get_shred_info(shred_id)
            return ShredInfo(
                id=info["id"],
                name=info["name"],
                is_running=info["is_running"],
                is_done=info["is_done"],
            )
        except RuntimeError:
            return None

    def compile_file(self, path: str | Path) -> bool:
        """Compile a file without running (syntax check).

        Args:
            path: Path to the ChucK file

        Returns:
            True if compilation successful
        """
        try:
            success, _ = self._chuck.compile_file(str(path), count=0)
            return success
        except RuntimeError:
            return False

    def exec_code(self, code: str) -> bool:
        """Execute code immediately (no shred created).

        Args:
            code: ChucK code to execute

        Returns:
            True if execution successful
        """
        try:
            success, _ = self._chuck.compile_code(code, immediate=True)
            return success
        except RuntimeError:
            return False
