"""
Shared TUI components for editor and REPL.

Provides base class with common functionality:
- ChucK instance management
- Audio lifecycle management
- Session tracking
- Shared UI components (via widgets module)
- Common key bindings
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.widgets import TextArea

from .._numchuck import (
    ChucK,
    PARAM_SAMPLE_RATE,
    PARAM_OUTPUT_CHANNELS,
    PARAM_INPUT_CHANNELS,
    PARAM_CHUGIN_ENABLE,
    PARAM_IMPORT_PATH_SYSTEM,
)
from ..services.audio import AudioService
from .session import ChuckSession
from .logging import TUILogger, get_logger
from ..config import get_config, KeybindingsConfig
from ..paths import get_numchuck_home
from . import widgets

if TYPE_CHECKING:
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from ..services import ShredService, GlobalsService, FileService


def format_elapsed_time(elapsed_sec: float) -> str:
    """Format elapsed time in human-readable format.

    Args:
        elapsed_sec: Elapsed time in seconds

    Returns:
        Formatted string like "5.2s", "2m30.5s", or "1h05m"
    """
    if elapsed_sec < 60:
        return f"{elapsed_sec:.1f}s"
    elif elapsed_sec < 3600:
        mins = int(elapsed_sec / 60)
        secs = elapsed_sec % 60
        return f"{mins}m{secs:04.1f}s"
    else:
        hours = int(elapsed_sec / 3600)
        mins = int((elapsed_sec % 3600) / 60)
        return f"{hours}h{mins:02d}m"


def format_shred_name(full_name: str, max_len: int = 56) -> str:
    """Format shred name for display, showing parent/filename.

    Args:
        full_name: Full path or name of the shred
        max_len: Maximum length for the name

    Returns:
        Formatted name truncated to max_len
    """
    try:
        path = Path(full_name)
        if path.parent.name:
            name = f"{path.parent.name}/{path.name}"
        else:
            name = path.name
    except (ValueError, TypeError):
        name = full_name
    return name[:max_len]


def generate_shreds_table(
    shreds: dict[int, dict[str, Any]],
    chuck: ChucK,
    use_pipes: bool = False,
) -> str:
    """Generate formatted table of active shreds.

    Args:
        shreds: Dictionary of shred_id -> shred info
        chuck: ChucK instance for querying VM time and sample rate
        use_pipes: If True, use pipe separators; if False, use spaces

    Returns:
        Formatted table string
    """
    if not shreds:
        return "No active shreds"

    lines = []

    # Header
    if use_pipes:
        lines.append(
            "ID   | Name                                                    | Elapsed"
        )
        lines.append("-" * 78)
    else:
        lines.append(
            "ID    Name                                                    Elapsed"
        )
        lines.append("\u2500" * 78)  # Unicode box drawing character

    # Get current VM time for elapsed calculation
    try:
        current_time = chuck.now()
    except (RuntimeError, AttributeError):
        current_time = 0.0

    # Get sample rate
    try:
        sample_rate = chuck.get_param_int(PARAM_SAMPLE_RATE)
    except (RuntimeError, AttributeError, ValueError):
        sample_rate = 44100

    for shred_id, info in sorted(shreds.items()):
        name = format_shred_name(info["name"])

        # Calculate elapsed time in seconds
        spork_time = info.get("time", 0.0)
        elapsed_samples = current_time - spork_time
        elapsed_sec = elapsed_samples / sample_rate if sample_rate > 0 else 0.0
        time_str = format_elapsed_time(elapsed_sec)

        if use_pipes:
            lines.append(f"{shred_id:<5d} | {name:<56s} | {time_str}")
        else:
            lines.append(f"{shred_id:<5} {name:<56} {time_str}")

    return "\n".join(lines)


# =============================================================================
# Keybinding Helpers
# =============================================================================


def parse_key_binding(key_str: str) -> str:
    """Parse a key binding string into prompt_toolkit format.

    Args:
        key_str: Key binding string like 'c-q', 'f1', 'c-s-f', 'escape'

    Returns:
        Validated key binding string for prompt_toolkit
    """
    # Normalize the key string
    key_str = key_str.lower().strip()

    # Valid modifier prefixes
    valid_prefixes = {"c-", "s-", "a-", "m-"}  # ctrl, shift, alt, meta

    # Valid function keys
    valid_fkeys = {f"f{i}" for i in range(1, 25)}  # F1-F24

    # Valid special keys
    valid_special = {
        "escape",
        "enter",
        "tab",
        "backspace",
        "delete",
        "insert",
        "home",
        "end",
        "pageup",
        "pagedown",
        "left",
        "right",
        "up",
        "down",
        "space",
    }

    # Remove and count modifiers
    modifiers = []
    remaining = key_str
    while remaining[:2] in valid_prefixes:
        modifiers.append(remaining[:2])
        remaining = remaining[2:]

    # Validate the key
    if remaining in valid_fkeys or remaining in valid_special or len(remaining) == 1:
        # Valid key
        return key_str
    else:
        # Return original, let prompt_toolkit handle validation
        return key_str


def create_keybinding(
    kb: KeyBindings,
    key: str,
    handler: Callable[["KeyPressEvent"], None],
    description: str = "",
) -> None:
    """Safely create a keybinding with validation.

    Args:
        kb: KeyBindings instance to add to
        key: Key binding string
        handler: Handler function for the key press
        description: Optional description for documentation
    """
    parsed_key = parse_key_binding(key)
    try:
        # Use decorator syntax but call it manually
        kb.add(parsed_key)(handler)
    except ValueError as e:
        # Log error but don't crash
        import warnings

        warnings.warn(f"Invalid keybinding '{key}': {e}", stacklevel=2)


def get_keybinding(name: str, keybindings: KeybindingsConfig | None = None) -> str:
    """Get a keybinding value by name from config.

    Args:
        name: Keybinding name (e.g., 'exit', 'toggle_help')
        keybindings: Optional KeybindingsConfig, uses global config if None

    Returns:
        Key binding string
    """
    if keybindings is None:
        keybindings = get_config().keybindings
    return getattr(keybindings, name, "")


class ChuckApplication:
    """Base application managing ChucK instance and shared state.

    Provides common functionality for both REPL and Editor:
    - ChucK instance lifecycle management
    - Audio start/stop/shutdown via AudioService
    - Output capture (chout/cherr)
    - Session tracking with optional project support
    - Shared UI components
    """

    def __init__(
        self,
        project_name: str | None = None,
        sample_rate: int = 44100,
        output_channels: int = 2,
        input_channels: int = 0,
        auto_init: bool = False,
        logger: TUILogger | None = None,
    ) -> None:
        """Initialize the application.

        Args:
            project_name: Optional project name for file versioning
            sample_rate: Audio sample rate in Hz
            output_channels: Number of output audio channels
            input_channels: Number of input audio channels
            auto_init: If True, initialize ChucK immediately
            logger: Optional logger instance (uses global logger if None)
        """
        self.__chuck: ChucK | None = ChucK()
        self._sample_rate = sample_rate
        self._output_channels = output_channels
        self._input_channels = input_channels

        # Logger for consistent error reporting
        self._logger = logger or get_logger()

        # Audio management via AudioService
        self._audio_manager = AudioService(self.__chuck, self._logger)

        self.__session: ChuckSession | None = ChuckSession(
            self.__chuck, project_name=project_name
        )

        # Service instances (lazily created)
        self._shred_service: ShredService | None = None
        self._globals_service: GlobalsService | None = None
        self._file_service: FileService | None = None

        # Shared UI state
        self.show_help = False
        self.show_shreds = False
        self.show_log = False

        # Log tracking
        self.log_messages: list[str] = []
        self._log_callback: Callable[[str], None] | None = None

        if auto_init:
            self.setup()

    @property
    def chuck(self) -> ChucK:
        """Get the ChucK instance, raising if closed."""
        if self.__chuck is None:
            raise RuntimeError("ChucK instance has been closed")
        return self.__chuck

    @property
    def session(self) -> ChuckSession:
        """Get the session, raising if closed."""
        if self.__session is None:
            raise RuntimeError("Session has been closed")
        return self.__session

    @property
    def shred_service(self) -> "ShredService":
        """Get the ShredService for shred operations.

        Lazily creates the service on first access.
        """
        if not hasattr(self, "_shred_service") or self._shred_service is None:
            from ..services import ShredService

            self._shred_service = ShredService(self.chuck, self.session, self._logger)
        return self._shred_service

    @property
    def globals_service(self) -> "GlobalsService":
        """Get the GlobalsService for global variable operations.

        Lazily creates the service on first access.
        """
        if not hasattr(self, "_globals_service") or self._globals_service is None:
            from ..services import GlobalsService

            self._globals_service = GlobalsService(self.chuck, self._logger)
        return self._globals_service

    @property
    def file_service(self) -> "FileService":
        """Get the FileService for file operations.

        Lazily creates the service on first access.
        """
        if not hasattr(self, "_file_service") or self._file_service is None:
            from ..services import FileService

            self._file_service = FileService(self.session, self._logger)
        return self._file_service

    def setup(self) -> None:
        """Initialize ChucK with configured parameters.

        Call this before using the ChucK instance.
        """
        self.chuck.set_param(PARAM_SAMPLE_RATE, self._sample_rate)
        self.chuck.set_param(PARAM_OUTPUT_CHANNELS, self._output_channels)
        self.chuck.set_param(PARAM_INPUT_CHANNELS, self._input_channels)

        # Configure chugin paths from config and numchuck directory
        config = get_config()
        self.chuck.set_param(PARAM_CHUGIN_ENABLE, int(config.chuck.chugin_enable))

        # Build chugin search directories: config paths + numchuck chugins dirs
        # PARAM_IMPORT_PATH_SYSTEM is used for directory search (auto-loads .chug files)
        chugin_dirs: list[str] = []
        for path in config.paths.chugin_paths:
            expanded = str(Path(path).expanduser())
            if expanded not in chugin_dirs:
                chugin_dirs.append(expanded)

        # Always include ~/.numchuck/chugins (global user chugins)
        global_chugins_dir = get_numchuck_home() / "chugins"
        global_chugins_str = str(global_chugins_dir)
        if global_chugins_str not in chugin_dirs:
            chugin_dirs.append(global_chugins_str)

        # Include local .numchuck/chugins if it exists and is different from global
        local_chugins_dir = Path.cwd() / ".numchuck" / "chugins"
        if local_chugins_dir.exists():
            local_chugins_str = str(local_chugins_dir)
            if local_chugins_str not in chugin_dirs:
                chugin_dirs.append(local_chugins_str)

        if chugin_dirs:
            self.chuck.set_param_string_list(PARAM_IMPORT_PATH_SYSTEM, chugin_dirs)

        self.chuck.init()

    def set_log_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for log messages.

        Args:
            callback: Function to call with log messages
        """
        self._log_callback = callback

    def setup_output_capture(self) -> None:
        """Set up ChucK output capture to log messages.

        Captures both chout and cherr output.
        """

        def log_callback(msg: str) -> None:
            self.log_messages.append(msg)
            if self._log_callback:
                self._log_callback(msg)

        self.chuck.set_chout_callback(log_callback)
        self.chuck.set_cherr_callback(log_callback)

    @property
    def audio_running(self) -> bool:
        """Check if audio is currently running."""
        return self._audio_manager.is_running

    @audio_running.setter
    def audio_running(self, value: bool) -> None:
        """Set audio running state (for compatibility)."""
        # This is handled by AudioService, but we sync session state
        self.session.audio_running = value

    def start_audio_playback(self) -> bool:
        """Start real-time audio playback.

        Returns:
            True if audio started successfully, False otherwise
        """
        result = self._audio_manager.start()
        self.session.audio_running = result
        return result

    def stop_audio_playback(self) -> None:
        """Stop real-time audio playback."""
        self._audio_manager.stop()
        self.session.audio_running = False

    def get_common_key_bindings(
        self, keybindings: KeybindingsConfig | None = None
    ) -> KeyBindings:
        """Common key bindings shared across editor and REPL.

        Args:
            keybindings: Optional keybindings config, uses global config if None

        Returns:
            KeyBindings with configurable handlers
        """
        if keybindings is None:
            keybindings = get_config().keybindings

        kb = KeyBindings()

        def exit_app(event: KeyPressEvent) -> None:
            """Exit application"""
            event.app.exit()

        def toggle_help(event: KeyPressEvent) -> None:
            """Toggle help window"""
            self.show_help = not self.show_help
            event.app.invalidate()

        def toggle_shreds(event: KeyPressEvent) -> None:
            """Toggle shreds table"""
            self.show_shreds = not self.show_shreds
            event.app.invalidate()

        def toggle_log(event: KeyPressEvent) -> None:
            """Toggle log window"""
            self.show_log = not self.show_log
            event.app.invalidate()

        # Create keybindings from config
        create_keybinding(kb, keybindings.exit, exit_app, "Exit application")
        create_keybinding(kb, keybindings.toggle_help, toggle_help, "Toggle help")
        create_keybinding(kb, keybindings.toggle_shreds, toggle_shreds, "Toggle shreds")
        create_keybinding(kb, keybindings.toggle_log, toggle_log, "Toggle log")

        return kb

    def create_help_window(self, help_text: str) -> ConditionalContainer:
        """Create help window that toggles with F1.

        Args:
            help_text: Text content for help window

        Returns:
            ConditionalContainer with help window
        """
        return widgets.create_help_window(
            show_condition=lambda: self.show_help,
            help_text=help_text,
        )

    def create_shreds_table(self) -> ConditionalContainer:
        """Create shreds table that toggles with F2.

        Returns:
            ConditionalContainer with shreds table
        """

        def get_text() -> str:
            return generate_shreds_table(
                self.session.shreds, self.chuck, use_pipes=True
            )

        return widgets.create_shreds_table(
            show_condition=lambda: self.show_shreds,
            get_table_text=get_text,
        )

    def create_log_window(
        self, log_area: TextArea | None = None
    ) -> ConditionalContainer:
        """Create log window that toggles with F3.

        Args:
            log_area: Optional pre-created TextArea. If None, creates one.

        Returns:
            ConditionalContainer with log window
        """
        container, log_area = widgets.create_log_window(
            show_condition=lambda: self.show_log,
            log_area=log_area,
        )

        def log_callback(msg: str) -> None:
            """Callback for ChucK output"""
            log_area.text += msg
            if len(self.log_messages) > 1000:
                # Trim old messages
                self.log_messages = self.log_messages[-500:]
                log_area.text = "".join(self.log_messages[-500:])

        # Set up output capture with the log callback
        self.set_log_callback(log_callback)
        self.setup_output_capture()

        return container

    def create_status_bar(self, status_text_func: Callable[[], str]) -> Window:
        """Create status bar at bottom of screen.

        Args:
            status_text_func: Function returning status bar text

        Returns:
            Window with status bar
        """
        return widgets.create_status_bar(status_text_func)

    def cleanup(self) -> None:
        """Cleanup ChucK and audio resources.

        This method:
        1. Removes all shreds
        2. Stops audio if running
        3. Closes ChucK instance (calls shutdown on C++ object)
        4. Breaks circular references for garbage collection
        """
        # Remove all shreds first
        try:
            if self.__chuck is not None:
                self.__chuck.remove_all_shreds()
        except (RuntimeError, AttributeError):
            pass

        # Stop audio if running
        if self.audio_running:
            self.stop_audio_playback()

        # Close ChucK instance (required for proper C++ cleanup)
        try:
            if self.__chuck is not None:
                self.__chuck.shutdown()
        except (RuntimeError, AttributeError):
            pass

        # Break circular references to allow proper garbage collection
        if self.__session is not None:
            self.__session.chuck = None
            self.__session = None
        self.__chuck = None
