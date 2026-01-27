from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._numchuck import start_audio, stop_audio, shutdown_audio, audio_info
from ..paths import (
    get_snippet_path_with_source,
    get_snippets_dir,
    ensure_numchuck_directories,
    list_all_snippets,
)
from ..services import ShredService, GlobalsService
from .logging import get_logger, TUILogger

if TYPE_CHECKING:
    from .._numchuck import ChucK
    from .parser import Command
    from .session import ChuckSession


class CommandExecutor:
    """Executes REPL commands with consistent error handling.

    All command methods follow the pattern:
    - Return None on success
    - Return error message string on failure
    - Log output via logger for UI integration
    """

    def __init__(
        self,
        session: ChuckSession,
        logger: TUILogger | None = None,
        shred_service: ShredService | None = None,
        globals_service: GlobalsService | None = None,
    ) -> None:
        """Initialize CommandExecutor.

        Args:
            session: ChuckSession for state tracking
            logger: Optional logger (uses global logger if None)
            shred_service: Optional ShredService (created if None)
            globals_service: Optional GlobalsService (created if None)
        """
        self.session = session
        self._chuck = session.chuck
        self._logger = logger or get_logger()

        # Create ShredService if not provided
        self._shred_service: ShredService | None
        if shred_service is None and self._chuck is not None:
            self._shred_service = ShredService(self._chuck, session, self._logger)
        else:
            self._shred_service = shred_service

        # Create GlobalsService if not provided
        self._globals_service: GlobalsService | None
        if globals_service is None and self._chuck is not None:
            self._globals_service = GlobalsService(self._chuck, self._logger)
        else:
            self._globals_service = globals_service

    @property
    def chuck(self) -> ChucK:
        """Get ChucK instance, raising if not available."""
        if self._chuck is None:
            raise RuntimeError("ChucK instance not available")
        return self._chuck

    @property
    def shred_service(self) -> ShredService:
        """Get ShredService, raising if not available."""
        if self._shred_service is None:
            raise RuntimeError("ShredService not available")
        return self._shred_service

    @property
    def globals_service(self) -> GlobalsService:
        """Get GlobalsService, raising if not available."""
        if self._globals_service is None:
            raise RuntimeError("GlobalsService not available")
        return self._globals_service

    def execute(self, cmd: Command) -> str | None:
        """Execute command and return error message if any.

        Args:
            cmd: Parsed command object

        Returns:
            None on success, error message string on failure
        """
        handler = getattr(self, f"_cmd_{cmd.type}", None)
        if handler:
            return handler(cmd.args)
        else:
            return f"Unknown command type: {cmd.type}"

    def _cmd_spork_file(self, args: dict[str, Any]) -> str | None:
        """Spork a ChucK file."""
        result = self.shred_service.spork_file(args["path"])
        return result.error

    def _cmd_spork_code(self, args: dict[str, Any]) -> str | None:
        """Spork inline ChucK code."""
        result = self.shred_service.spork_code(args["code"])
        return result.error

    def _cmd_remove_shred(self, args: dict[str, Any]) -> str | None:
        """Remove a shred by ID."""
        sid = args["id"]
        if self.shred_service.remove_shred(sid):
            return None
        return f"Failed to remove shred {sid}"

    def _cmd_remove_all(self, args: dict[str, Any]) -> str | None:
        """Remove all shreds."""
        self.shred_service.remove_all()
        return None

    def _cmd_replace_shred(self, args: dict[str, Any]) -> str | None:
        """Replace a shred with new code."""
        result = self.shred_service.replace_shred(args["id"], args["code"])
        return result.error

    def _cmd_replace_shred_file(self, args: dict[str, Any]) -> str | None:
        """Replace shred with code from file."""
        result = self.shred_service.replace_shred_file(args["id"], args["path"])
        return result.error

    def _cmd_status(self, args: dict[str, Any]) -> str | None:
        """Show VM status (Chuck-style)."""
        all_ids = self.chuck.get_all_shred_ids()
        now = self.chuck.now()
        audio = "running" if self.session.audio_running else "stopped"

        self._log("[chuck](VM): status")
        self._log(f"  shreds: {len(all_ids)}")
        self._log(f"  audio: {audio}")
        self._log(f"  now: {now} samples")
        if all_ids:
            self._log(f"  shred IDs: {all_ids}")
        return None

    def _cmd_list_shreds(self, args: dict[str, Any]) -> str | None:
        """List all running shreds."""
        shreds = self.chuck.get_all_shred_ids()
        if not shreds:
            self._log("no shreds running")
            return None

        self._log(f"{'ID':<8} {'Name':<40}")
        self._log("-" * 50)
        for sid in shreds:
            name = self.session.get_shred_name(sid)
            self._log(f"{sid:<8} {name:<40}")
        return None

    def _cmd_shred_info(self, args: dict[str, Any]) -> str | None:
        """Show info for a specific shred."""
        try:
            info = self.chuck.get_shred_info(args["id"])
            self._log(f"Shred {info['id']}:")
            self._log(f"  name: {info['name']}")
            self._log(f"  running: {info['is_running']}")
            self._log(f"  done: {info['is_done']}")
            return None
        except RuntimeError as e:
            return f"Error getting shred info: {e}"

    def _cmd_list_globals(self, args: dict[str, Any]) -> str | None:
        """List all global variables."""
        globals_list = self.globals_service.list_globals()
        if not globals_list:
            self._log("no globals defined")
            return None

        self._log(f"{'Type':<20} {'Name':<30}")
        self._log("-" * 52)
        for info in globals_list:
            self._log(f"{info.type:<20} {info.name:<30}")
        return None

    def _cmd_audio_info(self, args: dict[str, Any]) -> str | None:
        """Show audio system info."""
        info = audio_info()
        self._log(f"Sample rate: {info['sample_rate']} Hz")
        self._log(f"Channels out: {info['num_channels_out']}")
        self._log(f"Channels in: {info['num_channels_in']}")
        self._log(f"Buffer size: {info['buffer_size']}")
        return None

    def _cmd_current_time(self, args: dict[str, Any]) -> str | None:
        """Show current ChucK time."""
        self._log(f"now: {self.chuck.now()}")
        return None

    def _log(self, message: str) -> None:
        """Log output message (goes to UI or stdout)."""
        # For now, print to stdout; UI can capture via callbacks
        print(message)

    def _cmd_set_global(self, args: dict[str, Any]) -> str | None:
        """Set a global variable."""
        val = args["value"]
        name = args["name"]

        if self.globals_service.set_global(name, val):
            self._log(f"set {name} = {val}")
            return None
        return f"Failed to set global '{name}'"

    def _cmd_get_global(self, args: dict[str, Any]) -> str | None:
        """Get a global variable value."""
        name = args["name"]

        result = self.globals_service.get_global(name)
        if result is not None:
            typ, val = result
            if typ == "string":
                self._log(f'{name} = "{val}"')
            else:
                self._log(f"{name} = {val}")
            return None
        return f"Global variable '{name}' not found or wrong type"

    def _cmd_signal_event(self, args: dict[str, Any]) -> str | None:
        """Signal a global event."""
        name = args["name"]
        if self.globals_service.signal_event(name):
            self._log(f"signaled event '{name}'")
            return None
        return f"Failed to signal event '{name}'"

    def _cmd_broadcast_event(self, args: dict[str, Any]) -> str | None:
        """Broadcast a global event."""
        name = args["name"]
        if self.globals_service.broadcast_event(name):
            self._log(f"broadcast event '{name}'")
            return None
        return f"Failed to broadcast event '{name}'"

    def _cmd_start_audio(self, args: dict[str, Any]) -> str | None:
        """Start real-time audio playback."""
        try:
            start_audio(self.chuck)
            self.session.audio_running = True
            self._logger.info("Audio started")
            return None
        except (RuntimeError, OSError) as e:
            return f"Failed to start audio: {e}"

    def _cmd_stop_audio(self, args: dict[str, Any]) -> str | None:
        """Stop real-time audio playback."""
        try:
            stop_audio()
            self.session.audio_running = False
            self._logger.info("Audio stopped")
            return None
        except (RuntimeError, OSError) as e:
            return f"Failed to stop audio: {e}"

    def _cmd_shutdown_audio(self, args: dict[str, Any]) -> str | None:
        """Shutdown audio system."""
        try:
            shutdown_audio(500)
            self.session.audio_running = False
            self._logger.info("Audio shutdown")
            return None
        except (RuntimeError, OSError) as e:
            return f"Failed to shutdown audio: {e}"

    def _cmd_clear_vm(self, args: dict[str, Any]) -> str | None:
        """Clear all shreds from VM."""
        if self.shred_service.clear_vm():
            self._log("VM cleared")
            return None
        return "Failed to clear VM"

    def _cmd_reset_id(self, args: dict[str, Any]) -> str | None:
        """Reset shred ID counter."""
        if self.shred_service.reset_shred_id():
            self._log("shred ID reset")
            return None
        return "Failed to reset shred ID"

    def _cmd_clear_screen(self, args: dict[str, Any]) -> str | None:
        """Clear the terminal screen."""
        sys.stdout.write("\033[2J\033[H")  # Clear screen and move cursor to home
        sys.stdout.flush()
        return None

    def _cmd_compile_file(self, args: dict[str, Any]) -> str | None:
        """Compile a file without running."""
        if self.shred_service.compile_file(args["path"]):
            self._log(f"compiled {args['path']}")
            return None
        return f"Compilation failed for {args['path']}"

    def _cmd_exec_code(self, args: dict[str, Any]) -> str | None:
        """Execute code immediately."""
        if self.shred_service.exec_code(args["code"]):
            self._log("executed")
            return None
        return "Execution failed"

    def _cmd_edit_shred(self, args: dict[str, Any]) -> str | None:
        """Edit and replace a shred by ID."""
        shred_id = args["id"]

        if shred_id not in self.session.shreds:
            return f"Shred {shred_id} not found"

        shred_info = self.session.shreds[shred_id]
        source = shred_info["source"]
        name = shred_info["name"]

        # Get editor from environment or use default
        editor = os.environ.get("EDITOR", "nano")

        # Create temp file with current content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ck", delete=False) as f:
            f.write(source)
            temp_path = f.name

        try:
            # Open editor
            subprocess.run([editor, temp_path])

            # Read the modified file
            with open(temp_path, "r") as f:
                new_code = f.read()

            # Replace the shred if content changed
            if new_code.strip() and new_code != source:
                result = self.shred_service.replace_shred(shred_id, new_code, name=name)
                return result.error
            return None
        except (OSError, subprocess.SubprocessError) as e:
            return f"Error editing shred: {e}"
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                self._logger.debug(f"Could not delete temp file: {temp_path}")

    def _cmd_shell(self, args: dict[str, Any]) -> str | None:
        """Execute a shell command."""
        subprocess.run(args["cmd"], shell=True)
        return None

    def _cmd_open_editor(self, args: dict[str, Any]) -> str | None:
        """Open external editor for code entry."""
        # Get editor from environment or use default
        editor = os.environ.get("EDITOR", "nano")

        # Create temp file with .ck extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ck", delete=False) as f:
            # Write a template
            f.write("// ChucK code - save and exit to spork\n")
            f.write("SinOsc s => dac;\n")
            f.write("440 => s.freq;\n")
            f.write("second => now;\n")
            temp_path = f.name

        try:
            # Open editor
            subprocess.run([editor, temp_path])

            # Read the file
            with open(temp_path, "r") as f:
                code = f.read()

            # Spork it if not empty/template
            if code.strip() and "// ChucK code" not in code:
                result = self.shred_service.spork_code(code, name="editor")
                if result.success:
                    for sid in result.shred_ids:
                        self._log(f"sporked from editor -> shred {sid}")
                else:
                    return "Failed to spork editor code"
            return None
        except (OSError, subprocess.SubprocessError) as e:
            return f"Error opening editor: {e}"
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                self._logger.debug(f"Could not delete temp file: {temp_path}")

    def _cmd_watch(self, args: dict[str, Any]) -> str | None:
        """Monitor VM state continuously."""
        self._log("Watching VM state (Ctrl+C to stop)...")
        self._log("")
        try:
            while True:
                shred_count = len(self.chuck.get_all_shred_ids())
                now = self.chuck.now()
                audio = "ON" if self.session.audio_running else "OFF"
                print(
                    f"\rAudio: {audio:<3} | Now: {now:>10.2f} | Shreds: {shred_count:<3}",
                    end="",
                    flush=True,
                )
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n")
        return None

    def _cmd_load_snippet(self, args: dict[str, Any]) -> str | None:
        """Load and spork a code snippet.

        Searches local snippets (./.numchuck/snippets/) first, then global
        snippets (~/.numchuck/snippets/). Local snippets take precedence.
        """
        name = args["name"]
        snippet_path, source = get_snippet_path_with_source(name)

        if snippet_path is None:
            # Snippet not found - show available snippets
            snippets_dir = get_snippets_dir()
            if not snippets_dir.exists():
                try:
                    ensure_numchuck_directories()
                    self._log(f"Created snippets directory: {snippets_dir}")
                except OSError as e:
                    return f"Could not create snippets directory: {e}"

            self._log(f"Snippet '{name}' not found")
            self._log("")
            self._log("Available snippets:")

            all_snippets = list_all_snippets()
            if all_snippets:
                for snippet_name, snippet_source in all_snippets:
                    source_tag = " (global)" if snippet_source == "global" else ""
                    self._log(f"  @{snippet_name}{source_tag}")
            else:
                self._log("  (none)")
                self._log("")
                self._log(f"Add .ck files to {snippets_dir} to create snippets")
            return None

        # Spork the snippet using ShredService
        # Note: we use the custom name @{name} for the snippet
        result = self.shred_service.spork_file(snippet_path)
        if result.success:
            source_tag = " (global)" if source == "global" else ""
            # Update session with snippet name instead of path
            for sid in result.shred_ids:
                if self.session and sid in self.session.shreds:
                    self.session.shreds[sid]["name"] = f"@{name}"
                self._log(f"sporked snippet @{name}{source_tag} -> shred {sid}")
            return None
        else:
            return f"Failed to spork snippet @{name}"

    # -------------------------------------------------------------------------
    # File watching commands
    # -------------------------------------------------------------------------

    def _get_or_create_watcher(self):
        """Get or create the file watcher instance."""
        if (
            not hasattr(self.session, "_file_watcher")
            or self.session._file_watcher is None
        ):
            from ..watcher import FileWatcher

            def on_reload(path: Path, shred_id: int) -> None:
                self._log(f"[reload] {path.name} -> shred {shred_id}")

            def on_error(path: Path, error: str) -> None:
                self._logger.error(f"[watch error] {path.name}: {error}")

            self.session._file_watcher = FileWatcher(
                chuck=self.chuck,
                session=self.session,
                on_reload=on_reload,
                on_error=on_error,
            )

        return self.session._file_watcher

    def _cmd_watch_file(self, args: dict[str, Any]) -> str | None:
        """Start watching a file for auto-reload."""
        filepath = args["path"]
        path = Path(filepath).resolve()

        if not path.exists():
            return f"File not found: {filepath}"

        watcher = self._get_or_create_watcher()

        # First, compile the file if not already running
        shred_id = None
        result = self.shred_service.spork_file(path)
        if result.success:
            shred_id = result.shred_id
            self._log(f"sporked {path.name} -> shred {shred_id}")

        # Add to watch list
        try:
            added = watcher.watch_file(path, shred_id=shred_id)
            if added:
                self._log(f"watching {path.name}")
            else:
                self._log(f"already watching {path.name}")

            # Start watcher if not running
            if not watcher.is_running:
                watcher.start()
                self._log("file watcher started")

        except FileNotFoundError:
            return f"File not found: {filepath}"

        return None

    def _cmd_unwatch_file(self, args: dict[str, Any]) -> str | None:
        """Stop watching a file."""
        filepath = args["path"]
        path = Path(filepath).resolve()

        if (
            not hasattr(self.session, "_file_watcher")
            or self.session._file_watcher is None
        ):
            return "No files are being watched"

        watcher = self.session._file_watcher
        removed = watcher.unwatch_file(path)

        if removed:
            self._log(f"stopped watching {path.name}")
        else:
            self._log(f"not watching {path.name}")

        return None

    def _cmd_unwatch_all(self, args: dict[str, Any]) -> str | None:
        """Stop watching all files."""
        if (
            not hasattr(self.session, "_file_watcher")
            or self.session._file_watcher is None
        ):
            return "No files are being watched"

        watcher = self.session._file_watcher
        watched = watcher.get_watched_files()

        for wf in watched:
            watcher.unwatch_file(wf.filepath)

        if watcher.is_running:
            watcher.stop()

        self._log(f"stopped watching {len(watched)} file(s)")
        return None

    def _cmd_list_watched(self, args: dict[str, Any]) -> str | None:
        """List all watched files."""
        if (
            not hasattr(self.session, "_file_watcher")
            or self.session._file_watcher is None
        ):
            self._log("no files being watched")
            self._log("")
            self._log("Use 'watch file.ck' to start watching a file")
            return None

        watcher = self.session._file_watcher
        watched = watcher.get_watched_files()

        if not watched:
            self._log("no files being watched")
            return None

        self._log(f"{'File':<40} {'Shred':<8}")
        self._log("-" * 50)
        for wf in watched:
            shred_str = str(wf.shred_id) if wf.shred_id is not None else "-"
            name = wf.filepath.name
            if len(name) > 38:
                name = "..." + name[-35:]
            self._log(f"{name:<40} {shred_str:<8}")

        self._log("")
        self._log(f"Watcher: {'running' if watcher.is_running else 'stopped'}")
        return None
