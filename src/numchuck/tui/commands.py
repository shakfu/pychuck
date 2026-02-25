from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ..constants import POLL_INTERVAL, SHELL_COMMAND_TIMEOUT
from .._numchuck import start_audio, stop_audio, shutdown_audio, audio_info
from ..midi import MIDIMapping, generate_midi_listener_code, generate_midi_monitor_code
from ..osc import OSCServer, OSCController
from ..paths import get_recordings_dir
from ..recorder import RecordedSession, list_recordings, get_recording_path
from ..services import ShredService, GlobalsService, FileService
from .logging import get_logger, TUILogger

if TYPE_CHECKING:
    from .._numchuck import ChucK
    from .parser import Command
    from .session import ChuckSession
    from ..watcher import FileWatcher


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
        file_service: FileService | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize CommandExecutor.

        Args:
            session: ChuckSession for state tracking
            logger: Optional logger (uses global logger if None)
            shred_service: Optional ShredService (created if None)
            globals_service: Optional GlobalsService (created if None)
            file_service: Optional FileService (created if None)
            log_callback: Optional callback for output (uses print if None)
        """
        self.session = session
        self._chuck = session.chuck
        self._logger = logger or get_logger()
        self._log_callback = log_callback

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

        # Create FileService if not provided
        self._file_service: FileService | None
        if file_service is None:
            self._file_service = FileService(session, self._logger)
        else:
            self._file_service = file_service

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

    @property
    def file_service(self) -> FileService:
        """Get FileService, raising if not available."""
        if self._file_service is None:
            raise RuntimeError("FileService not available")
        return self._file_service

    # Command types that should not be recorded (meta/recording commands)
    _NO_RECORD_TYPES = frozenset(
        {
            "record_start",
            "record_stop",
            "record_save",
            "record_discard",
            "record_status",
            "exit",
        }
    )

    def execute(self, cmd: Command) -> str | None:
        """Execute command and return error message if any.

        Args:
            cmd: Parsed command object

        Returns:
            None on success, error message string on failure
        """
        # Record action if recording is active
        if self.session.recorder.is_recording and cmd.type not in self._NO_RECORD_TYPES:
            self.session.recorder.record_command(cmd.type)

        handler = getattr(self, f"_cmd_{cmd.type}", None)
        if handler:
            result: str | None = handler(cmd.args)
            return result
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

    def _cmd_abort_shred(self, args: dict[str, Any]) -> str | None:
        """Abort a shred by ID (ChucK abort.shred command).

        This is the ChucK-native command for removing shreds.
        Functionally equivalent to remove_shred.
        """
        sid = args["id"]
        if self.shred_service.remove_shred(sid):
            self._log(f"[shred {sid}]: abort")
            return None
        return f"Failed to abort shred {sid}"

    def _cmd_exit(self, args: dict[str, Any]) -> str | None:
        """Exit the REPL.

        Returns None to indicate success. The REPL checks for the 'exit'
        command type and handles the actual termination.
        """
        return None

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
        """List all running shreds.

        Uses session tracking for immediate results. The session tracks
        shreds as they're sporked, which works better for non-realtime
        use (testing, scripting) where VM message queue isn't processed.
        """
        # Use session data for reliability (works without audio running)
        if not self.session.shreds:
            self._log("no shreds running")
            return None

        self._log(f"{'ID':<8} {'Name':<40}")
        self._log("-" * 50)
        for sid, info in self.session.shreds.items():
            name = info.get("name", "unknown")
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
        """Log output message (goes to UI callback or stdout)."""
        if self._log_callback is not None:
            self._log_callback(message)
        else:
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
        """Execute a shell command with output capture and timeout."""
        try:
            result = subprocess.run(
                args["cmd"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=SHELL_COMMAND_TIMEOUT,
            )
            if result.stdout:
                self._log(result.stdout.rstrip())
            if result.stderr:
                self._log(result.stderr.rstrip())
            if result.returncode != 0:
                return f"Command exited with code {result.returncode}"
            return None
        except subprocess.TimeoutExpired:
            return f"Command timed out after {SHELL_COMMAND_TIMEOUT}s"
        except OSError as e:
            return f"Command failed: {e}"

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
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\n")
        return None

    def _cmd_load_snippet(self, args: dict[str, Any]) -> str | None:
        """Load and spork a code snippet.

        Searches local snippets (./.numchuck/snippets/) first, then global
        snippets (~/.numchuck/snippets/). Local snippets take precedence.
        """
        name = args["name"]
        snippet = self.file_service.load_snippet(name)

        if snippet is None:
            # Snippet not found - show available snippets
            snippets_dir = self.file_service.get_snippets_dir()
            if not snippets_dir.exists():
                if not self.file_service.ensure_directories():
                    return "Could not create snippets directory"
                self._log(f"Created snippets directory: {snippets_dir}")

            self._log(f"Snippet '{name}' not found")
            self._log("")
            self._log("Available snippets:")

            all_snippets = self.file_service.list_snippets()
            if all_snippets:
                for info in all_snippets:
                    source_tag = " (global)" if info.source == "global" else ""
                    self._log(f"  @{info.name}{source_tag}")
            else:
                self._log("  (none)")
                self._log("")
                self._log(f"Add .ck files to {snippets_dir} to create snippets")
            return None

        # Spork the snippet using ShredService
        # Note: we use the custom name @{name} for the snippet
        result = self.shred_service.spork_file(snippet.path)
        if result.success:
            source_tag = " (global)" if snippet.source == "global" else ""
            # Update session with snippet name instead of path
            for sid in result.shred_ids:
                if self.session and sid in self.session.shreds:
                    self.session.shreds[sid]["name"] = f"@{name}"
                self._log(f"sporked snippet @{name}{source_tag} -> shred {sid}")
            return None
        else:
            return f"Failed to spork snippet @{name}"

    # -------------------------------------------------------------------------
    # Waveform commands
    # -------------------------------------------------------------------------

    def _cmd_toggle_waveform(self, args: dict[str, Any]) -> str | None:
        """Toggle waveform display."""
        self.session.show_waveform = not self.session.show_waveform
        state = "on" if self.session.show_waveform else "off"
        self._log(f"waveform display {state}")
        return None

    def _cmd_waveform_on(self, args: dict[str, Any]) -> str | None:
        """Enable waveform display."""
        self.session.show_waveform = True
        self._log("waveform display on")
        return None

    def _cmd_waveform_off(self, args: dict[str, Any]) -> str | None:
        """Disable waveform display."""
        self.session.show_waveform = False
        self._log("waveform display off")
        return None

    # -------------------------------------------------------------------------
    # Recording commands
    # -------------------------------------------------------------------------

    def _cmd_record_start(self, args: dict[str, Any]) -> str | None:
        """Start recording a session."""
        name = args.get("name") or "session"
        try:
            self.session.recorder.start(name)
            self._log(f"recording started: {name}")
            return None
        except RuntimeError as e:
            return str(e)

    def _cmd_record_stop(self, args: dict[str, Any]) -> str | None:
        """Stop recording and auto-save."""
        try:
            recorded = self.session.recorder.stop()
            recordings_dir = get_recordings_dir()
            path = get_recording_path(recordings_dir, recorded.name)
            recorded.save(path)
            self._log(
                f"recording stopped: {recorded.name} "
                f"({recorded.action_count} actions, saved to {path})"
            )
            return None
        except RuntimeError as e:
            return str(e)

    def _cmd_record_save(self, args: dict[str, Any]) -> str | None:
        """Save the current/last recording under a new name."""
        name = args["name"]
        if not self.session.recorder.is_recording:
            return "Not currently recording"
        try:
            recorded = self.session.recorder.stop()
            recorded.name = name
            recordings_dir = get_recordings_dir()
            path = get_recording_path(recordings_dir, name)
            recorded.save(path)
            self._log(f"recording saved as: {name} ({recorded.action_count} actions)")
            return None
        except RuntimeError as e:
            return str(e)

    def _cmd_record_discard(self, args: dict[str, Any]) -> str | None:
        """Discard the current recording."""
        if not self.session.recorder.is_recording:
            return "Not currently recording"
        self.session.recorder.discard()
        self._log("recording discarded")
        return None

    def _cmd_record_status(self, args: dict[str, Any]) -> str | None:
        """Show recording status."""
        recorder = self.session.recorder
        if recorder.is_recording:
            self._log(f"recording: {recorder.session_name}")
            self._log(f"  elapsed: {recorder.elapsed_time:.1f}s")
            self._log(f"  actions: {recorder.action_count}")
        else:
            self._log("not recording")
        return None

    # -------------------------------------------------------------------------
    # Playback commands
    # -------------------------------------------------------------------------

    def _cmd_play(self, args: dict[str, Any]) -> str | None:
        """Start playback of a recorded session."""
        name = args["name"]
        speed = args.get("speed", 1.0)

        recordings_dir = get_recordings_dir()
        path = get_recording_path(recordings_dir, name)

        if not path.exists():
            return f"Recording not found: {name}"

        try:
            recorded = RecordedSession.load(path)
        except Exception as e:
            return f"Failed to load recording: {e}"

        player = self.session.player

        def on_action(action: Any) -> None:
            if action.action_type == "command":
                from .parser import CommandParser

                parser = CommandParser()
                cmd = parser.parse(action.content)
                if cmd:
                    self.execute(cmd)
            elif action.action_type == "code":
                self.shred_service.spork_code(action.content)

        player.load(recorded)
        player.set_action_callback(on_action)
        player.start(speed)
        self._log(
            f"playback started: {name} "
            f"({recorded.action_count} actions, speed={speed}x)"
        )
        return None

    def _cmd_play_pause(self, args: dict[str, Any]) -> str | None:
        """Pause playback."""
        player = self.session.player
        if not player.is_playing:
            return "No playback in progress"
        player.pause()
        self._log("playback paused")
        return None

    def _cmd_play_resume(self, args: dict[str, Any]) -> str | None:
        """Resume playback."""
        player = self.session.player
        if not player.is_playing:
            return "No playback in progress"
        if not player.is_paused:
            return "Playback is not paused"
        player.resume()
        self._log("playback resumed")
        return None

    def _cmd_play_stop(self, args: dict[str, Any]) -> str | None:
        """Stop playback."""
        player = self.session.player
        if not player.is_playing:
            return "No playback in progress"
        player.stop()
        self._log("playback stopped")
        return None

    def _cmd_list_recordings(self, args: dict[str, Any]) -> str | None:
        """List all saved recordings."""
        recordings_dir = get_recordings_dir()
        names = list_recordings(recordings_dir)
        if not names:
            self._log("no recordings found")
            return None

        self._log("recordings:")
        for name in names:
            self._log(f"  {name}")
        return None

    # -------------------------------------------------------------------------
    # MIDI commands
    # -------------------------------------------------------------------------

    def _cmd_midi_learn(self, args: dict[str, Any]) -> str | None:
        """Add a MIDI CC to global variable mapping."""
        name = args["name"]
        cc = args["cc"]
        channel = args.get("channel", 0)
        min_val = args.get("min", 0.0)
        max_val = args.get("max", 1.0)

        try:
            mapping = MIDIMapping(
                channel=channel,
                cc_number=cc,
                global_name=name,
                min_value=min_val,
                max_value=max_val,
            )
        except ValueError as e:
            return str(e)

        self.session.midi_mappings.add(mapping)
        self._log(f"MIDI mapping: ch{channel} cc{cc} -> {name} [{min_val}, {max_val}]")

        # If listener is running, respork with updated mappings
        if self.session.midi_listener_shred_id is not None:
            self._respork_midi_listener()

        return None

    def _cmd_midi_list(self, args: dict[str, Any]) -> str | None:
        """List all MIDI mappings."""
        mappings = self.session.midi_mappings
        if len(mappings) == 0:
            self._log("no MIDI mappings")
            return None

        self._log(f"{'Ch':<4} {'CC':<5} {'Global':<20} {'Range':<15}")
        self._log("-" * 46)
        for m in mappings:
            self._log(
                f"{m.channel:<4} {m.cc_number:<5} {m.global_name:<20} "
                f"[{m.min_value}, {m.max_value}]"
            )
        return None

    def _cmd_midi_remove(self, args: dict[str, Any]) -> str | None:
        """Remove a MIDI mapping by global variable name."""
        name = args["name"]
        if self.session.midi_mappings.remove_by_global(name):
            self._log(f"removed MIDI mapping for {name}")
            # Respork listener if running
            if self.session.midi_listener_shred_id is not None:
                if len(self.session.midi_mappings) > 0:
                    self._respork_midi_listener()
                else:
                    self._stop_midi_listener()
            return None
        return f"No MIDI mapping for '{name}'"

    def _cmd_midi_start(self, args: dict[str, Any]) -> str | None:
        """Start the MIDI listener shred."""
        if len(self.session.midi_mappings) == 0:
            return "No MIDI mappings defined (use 'midi learn' first)"

        if self.session.midi_listener_shred_id is not None:
            return "MIDI listener already running"

        return self._spork_midi_listener()

    def _cmd_midi_stop(self, args: dict[str, Any]) -> str | None:
        """Stop the MIDI listener shred."""
        if self.session.midi_listener_shred_id is None:
            return "MIDI listener not running"
        self._stop_midi_listener()
        self._log("MIDI listener stopped")
        return None

    def _cmd_midi_status(self, args: dict[str, Any]) -> str | None:
        """Show MIDI status."""
        mappings = self.session.midi_mappings
        listener = self.session.midi_listener_shred_id
        self._log(f"MIDI mappings: {len(mappings)}")
        if listener is not None:
            self._log(f"MIDI listener: running (shred {listener})")
        else:
            self._log("MIDI listener: stopped")
        return None

    def _cmd_midi_monitor(self, args: dict[str, Any]) -> str | None:
        """Start MIDI monitor shred."""
        code = generate_midi_monitor_code()
        result = self.shred_service.spork_code(code, name="midi-monitor")
        if result.success:
            self._log("MIDI monitor started (move a controller...)")
            return None
        return "Failed to start MIDI monitor"

    def _spork_midi_listener(self) -> str | None:
        """Spork the MIDI listener shred. Returns error or None."""
        code = generate_midi_listener_code(self.session.midi_mappings)
        if not code:
            return "No MIDI mappings to generate listener for"
        result = self.shred_service.spork_code(code, name="midi-listener")
        if result.success:
            self.session.midi_listener_shred_id = result.shred_id
            self._log(f"MIDI listener started (shred {result.shred_id})")
            return None
        return "Failed to start MIDI listener"

    def _stop_midi_listener(self) -> None:
        """Stop the MIDI listener shred."""
        sid = self.session.midi_listener_shred_id
        if sid is not None:
            self.shred_service.remove_shred(sid)
            self.session.midi_listener_shred_id = None

    def _respork_midi_listener(self) -> None:
        """Remove and re-spork the MIDI listener with updated mappings."""
        self._stop_midi_listener()
        self._spork_midi_listener()

    # -------------------------------------------------------------------------
    # OSC commands
    # -------------------------------------------------------------------------

    def _cmd_osc_start(self, args: dict[str, Any]) -> str | None:
        """Start the OSC server."""
        port = args.get("port", 9000)

        if self.session.osc_server is not None and self.session.osc_server.is_running:
            return "OSC server already running"

        server = OSCServer(port=port)

        # Create controller with callbacks wired to executor methods.
        # Lambdas discard return values to satisfy Callable[..., None] signatures.
        def _set_global(name: str, val: float) -> None:
            self.globals_service.set_global(name, val)

        def _spork(code: str) -> None:
            self.shred_service.spork_code(code)

        def _remove(sid: int) -> None:
            self.shred_service.remove_shred(sid)

        def _clear() -> None:
            self.shred_service.clear_vm()

        def _signal(name: str) -> None:
            self.globals_service.signal_event(name)

        def _broadcast(name: str) -> None:
            self.globals_service.broadcast_event(name)

        controller = OSCController(
            on_set_global=_set_global,
            on_spork=_spork,
            on_remove=_remove,
            on_clear=_clear,
            on_signal_event=_signal,
            on_broadcast_event=_broadcast,
        )
        controller.register_with_server(server)

        if server.start():
            self.session.osc_server = server
            self.session.osc_controller = controller
            self._log(f"OSC server started on port {port}")
            return None
        return f"Failed to start OSC server on port {port}"

    def _cmd_osc_stop(self, args: dict[str, Any]) -> str | None:
        """Stop the OSC server."""
        if self.session.osc_server is None or not self.session.osc_server.is_running:
            return "OSC server not running"

        self.session.osc_server.stop()
        self.session.osc_server = None
        self.session.osc_controller = None
        self._log("OSC server stopped")
        return None

    def _cmd_osc_status(self, args: dict[str, Any]) -> str | None:
        """Show OSC server status."""
        server = self.session.osc_server
        if server is not None and server.is_running:
            self._log(f"OSC server: running on port {server.port}")
            self._log(f"  handlers: {len(server.handlers)}")
        else:
            self._log("OSC server: stopped")
        return None

    # -------------------------------------------------------------------------
    # File watching commands
    # -------------------------------------------------------------------------

    def _get_or_create_watcher(self) -> "FileWatcher":
        """Get or create the file watcher instance."""
        if self.session._file_watcher is None:
            from ..watcher import FileWatcher

            def on_reload(path: Path, shred_id: int) -> None:
                self._log(f"[reload] {path.name} -> shred {shred_id}")

            def on_error(path: Path, error: str) -> None:
                self._logger.error(f"[watch error] {path.name}: {error}")

            self.session._file_watcher = FileWatcher(
                chuck=self.chuck,  # type: ignore[arg-type]
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
