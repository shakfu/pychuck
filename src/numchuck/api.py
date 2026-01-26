"""
High-level Pythonic API for ChucK.

This module provides a wrapper around the low-level ChucK bindings with
a more Pythonic interface using properties instead of get/set methods.

Example:
    >>> from numchuck.api import Chuck
    >>> chuck = Chuck(sample_rate=48000, output_channels=2)
    >>> chuck.sample_rate
    48000
    >>> chuck.compile("SinOsc s => dac;")
    (True, [1])

Thread Safety:
    When real-time audio is active (after calling start_audio()), the following
    operations are NOT thread-safe and should be avoided:

    - compile() / compile_file() - Stop audio first
    - remove_shred() / clear() - Stop audio first
    - Deleting the Chuck instance - Call stop_audio() first

    Safe operations during real-time audio:
    - Global variable getters/setters (set_int, get_int, etc.)
    - Event signaling (signal_event, broadcast_event)
    - Read-only queries (shreds property, shred_info)

    See docs/architecture.md for detailed thread safety documentation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from . import _numchuck

if TYPE_CHECKING:
    from typing import Callable

    from numpy.typing import NDArray


class Chuck:
    """High-level wrapper for ChucK with Pythonic property-based API.

    Parameters can be set via constructor kwargs or as properties before
    calling init(). After init(), most parameters become read-only.

    Args:
        sample_rate: Audio sample rate in Hz (default: 44100)
        input_channels: Number of input channels (default: 2)
        output_channels: Number of output channels (default: 2)
        working_directory: Working directory for file operations
        chugin_enable: Enable chugin loading (default: True)
        user_chugins: List of user chugin paths (default: None)
        vm_adaptive: Enable adaptive VM timing (default: False)
        vm_halt: Halt VM when no shreds (default: False)
        auto_depend: Enable automatic dependency resolution (default: False)
        deprecate_level: Deprecation warning level 0-2 (default: 1)
        dump_instructions: Dump VM instructions for debugging (default: False)
        otf_enable: Enable on-the-fly programming (default: False)
        otf_port: Port for on-the-fly programming (default: 8888)
        tty_color: Enable colored terminal output (default: False)
        tty_width_hint: Terminal width hint for formatting (default: 80)
        auto_init: Automatically call init() after setting params (default: True)
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        input_channels: int = 2,
        output_channels: int = 2,
        working_directory: str = "",
        chugin_enable: bool = True,
        user_chugins: list[str] | None = None,
        vm_adaptive: bool = False,
        vm_halt: bool = False,
        auto_depend: bool = False,
        deprecate_level: int = 1,
        dump_instructions: bool = False,
        otf_enable: bool = False,
        otf_port: int = 8888,
        tty_color: bool = False,
        tty_width_hint: int = 80,
        auto_init: bool = True,
    ) -> None:
        self._chuck = _numchuck.ChucK()

        # Set parameters before init
        self._chuck.set_param(_numchuck.PARAM_SAMPLE_RATE, sample_rate)
        self._chuck.set_param(_numchuck.PARAM_INPUT_CHANNELS, input_channels)
        self._chuck.set_param(_numchuck.PARAM_OUTPUT_CHANNELS, output_channels)
        if working_directory:
            self._chuck.set_param_string(
                _numchuck.PARAM_WORKING_DIRECTORY, working_directory
            )
        self._chuck.set_param(_numchuck.PARAM_CHUGIN_ENABLE, int(chugin_enable))
        if user_chugins:
            self._chuck.set_param_string_list(
                _numchuck.PARAM_USER_CHUGINS, user_chugins
            )
        self._chuck.set_param(_numchuck.PARAM_VM_ADAPTIVE, int(vm_adaptive))
        self._chuck.set_param(_numchuck.PARAM_VM_HALT, int(vm_halt))
        self._chuck.set_param(_numchuck.PARAM_AUTO_DEPEND, int(auto_depend))
        self._chuck.set_param(_numchuck.PARAM_DEPRECATE_LEVEL, deprecate_level)
        self._chuck.set_param(_numchuck.PARAM_DUMP_INSTRUCTIONS, int(dump_instructions))
        self._chuck.set_param(_numchuck.PARAM_OTF_ENABLE, int(otf_enable))
        self._chuck.set_param(_numchuck.PARAM_OTF_PORT, otf_port)
        self._chuck.set_param(_numchuck.PARAM_TTY_COLOR, int(tty_color))
        self._chuck.set_param(_numchuck.PARAM_TTY_WIDTH_HINT, tty_width_hint)

        if auto_init:
            self._chuck.init()

        # Internal buffers for run_reuse() - lazily allocated
        self._reuse_input_buf: NDArray[np.float32] | None = None
        self._reuse_output_buf: NDArray[np.float32] | None = None
        self._reuse_num_frames: int = 0

    # -------------------------------------------------------------------------
    # Context manager support
    # -------------------------------------------------------------------------

    def __enter__(self) -> "Chuck":
        """Enter context manager.

        Example:
            >>> with Chuck() as chuck:
            ...     chuck.compile("SinOsc s => dac;")
            ...     output = chuck.run(44100)
            ... # Automatically calls close() on exit
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, ensuring proper cleanup.

        Calls close() to shutdown the ChucK instance. This is especially
        important on Windows where explicit cleanup is required for proper
        thread termination.
        """
        self.close()

    # -------------------------------------------------------------------------
    # Core operations
    # -------------------------------------------------------------------------

    def init(self) -> bool:
        """Initialize the ChucK instance. Usually called automatically."""
        return self._chuck.init()

    def close(self) -> None:
        """Explicitly shutdown the ChucK instance.

        This method should be called before the instance is destroyed,
        especially on Windows where it ensures proper thread cleanup.

        Safe to call multiple times.
        """
        self._chuck.shutdown()

    def compile(
        self,
        code: str,
        args: str = "",
        count: int = 1,
        immediate: bool = False,
    ) -> tuple[bool, list[int]]:
        """Compile and run ChucK code.

        Args:
            code: ChucK source code string
            args: Arguments to pass to the shred
            count: Number of shreds to spawn (default: 1)
            immediate: If True, compile immediately without queuing

        Returns:
            Tuple of (success, list of shred IDs)

        Warning:
            Not thread-safe during real-time audio playback.
            Call stop_audio() before compiling new code.
        """
        return self._chuck.compile_code(code, args, count, immediate)

    def compile_file(
        self,
        path: str,
        args: str = "",
        count: int = 1,
        immediate: bool = False,
    ) -> tuple[bool, list[int]]:
        """Compile and run a ChucK file.

        Args:
            path: Path to .ck file
            args: Arguments to pass to the shred
            count: Number of shreds to spawn (default: 1)
            immediate: If True, compile immediately without queuing

        Returns:
            Tuple of (success, list of shred IDs)

        Warning:
            Not thread-safe during real-time audio playback.
            Call stop_audio() before compiling new code.
        """
        return self._chuck.compile_file(path, args, count, immediate)

    def run(
        self,
        num_frames: int,
        *,
        output: NDArray[np.float32] | None = None,
        input: NDArray[np.float32] | None = None,
        reuse: bool = False,
    ) -> NDArray[np.float32]:
        """Run the VM for a number of frames, returning the output audio.

        Args:
            num_frames: Number of audio frames to compute
            output: Pre-allocated output buffer, or None to allocate
            input: Pre-allocated input buffer, or None for silence
            reuse: If True and output is None, reuse internal buffer (zero GC)

        Returns:
            Output audio as numpy array (num_frames * output_channels,)

        Examples:
            # Simple (allocates each call)
            audio = chuck.run(512)

            # Zero allocation with your buffer
            buf = np.zeros(1024, dtype=np.float32)
            chuck.run(512, output=buf)

            # Zero allocation with internal buffer
            audio = chuck.run(512, reuse=True)

            # Effect mode (both buffers)
            chuck.run(512, output=out_buf, input=in_buf)
        """
        in_channels = self.input_channels
        out_channels = self.output_channels

        # Determine output buffer
        if output is not None:
            output_buf = output
        elif reuse:
            # Use internal reusable buffer
            if self._reuse_num_frames != num_frames or self._reuse_output_buf is None:
                self._reuse_output_buf = np.zeros(
                    num_frames * out_channels, dtype=np.float32
                )
                self._reuse_input_buf = np.zeros(
                    num_frames * in_channels, dtype=np.float32
                )
                self._reuse_num_frames = num_frames
            output_buf = self._reuse_output_buf
        else:
            output_buf = np.zeros(num_frames * out_channels, dtype=np.float32)

        # Determine input buffer
        if input is not None:
            input_buf = input
        elif reuse and self._reuse_input_buf is not None:
            input_buf = self._reuse_input_buf
        else:
            input_buf = np.zeros(num_frames * in_channels, dtype=np.float32)

        self._chuck.run(input_buf, output_buf, num_frames)
        return output_buf

    def advance(self, num_frames: int) -> None:
        """Advance the VM by a number of frames without returning audio.

        Use when you only need to trigger callbacks or advance time,
        and don't need the audio output.

        Args:
            num_frames: Number of audio frames to compute

        Example:
            >>> chuck.get_int_async("myVar", lambda v: print(v))
            >>> chuck.advance(256)  # triggers callback
        """
        in_channels = self.input_channels
        out_channels = self.output_channels
        input_buf = np.zeros(num_frames * in_channels, dtype=np.float32)
        output_buf = np.zeros(num_frames * out_channels, dtype=np.float32)
        self._chuck.run(input_buf, output_buf, num_frames)

    # -------------------------------------------------------------------------
    # Audio parameters (read-only after init)
    # -------------------------------------------------------------------------

    @property
    def sample_rate(self) -> int:
        """Audio sample rate in Hz."""
        return self._chuck.get_param_int(_numchuck.PARAM_SAMPLE_RATE)

    @property
    def input_channels(self) -> int:
        """Number of audio input channels."""
        return self._chuck.get_param_int(_numchuck.PARAM_INPUT_CHANNELS)

    @property
    def output_channels(self) -> int:
        """Number of audio output channels."""
        return self._chuck.get_param_int(_numchuck.PARAM_OUTPUT_CHANNELS)

    @property
    def working_directory(self) -> str:
        """Working directory for file operations."""
        return self._chuck.get_param_string(_numchuck.PARAM_WORKING_DIRECTORY)

    @property
    def version(self) -> str:
        """ChucK version string (read-only)."""
        return self._chuck.get_param_string(_numchuck.PARAM_VERSION)

    @property
    def chugin_enable(self) -> bool:
        """Whether chugin loading is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_CHUGIN_ENABLE))

    @property
    def vm_adaptive(self) -> bool:
        """Whether adaptive VM timing is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_VM_ADAPTIVE))

    @property
    def vm_halt(self) -> bool:
        """Whether VM halts when no shreds remain."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_VM_HALT))

    @property
    def auto_depend(self) -> bool:
        """Whether automatic dependency resolution is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_AUTO_DEPEND))

    @property
    def deprecate_level(self) -> int:
        """Deprecation warning level (0=none, 1=warn, 2=error)."""
        return self._chuck.get_param_int(_numchuck.PARAM_DEPRECATE_LEVEL)

    @property
    def dump_instructions(self) -> bool:
        """Whether VM instruction dumping is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_DUMP_INSTRUCTIONS))

    @property
    def otf_enable(self) -> bool:
        """Whether on-the-fly programming is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_OTF_ENABLE))

    @property
    def otf_port(self) -> int:
        """Port for on-the-fly programming."""
        return self._chuck.get_param_int(_numchuck.PARAM_OTF_PORT)

    @property
    def tty_color(self) -> bool:
        """Whether colored terminal output is enabled."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_TTY_COLOR))

    @property
    def tty_width_hint(self) -> int:
        """Terminal width hint for formatting."""
        return self._chuck.get_param_int(_numchuck.PARAM_TTY_WIDTH_HINT)

    @property
    def user_chugins(self) -> list[str]:
        """List of user chugin paths."""
        return self._chuck.get_param_string_list(_numchuck.PARAM_USER_CHUGINS)

    @property
    def compiler_highlight_on_error(self) -> bool:
        """Whether syntax highlighting in error messages is enabled."""
        return bool(
            self._chuck.get_param_int(_numchuck.PARAM_COMPILER_HIGHLIGHT_ON_ERROR)
        )

    @property
    def is_realtime_audio_hint(self) -> bool:
        """Hint for real-time audio mode."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_IS_REALTIME_AUDIO_HINT))

    @property
    def otf_print_warnings(self) -> bool:
        """Whether on-the-fly compiler warnings are printed."""
        return bool(self._chuck.get_param_int(_numchuck.PARAM_OTF_PRINT_WARNINGS))

    # -------------------------------------------------------------------------
    # Shred management
    # -------------------------------------------------------------------------

    @property
    def shreds(self) -> list[int]:
        """List of all active shred IDs."""
        return self._chuck.get_all_shred_ids()

    def remove_shred(self, shred_id: int) -> None:
        """Remove a shred by ID.

        Warning:
            Not thread-safe during real-time audio playback.
            Call stop_audio() before removing shreds.
        """
        self._chuck.remove_shred(shred_id)

    def replace_shred(self, shred_id: int, code: str, args: str = "") -> int:
        """Replace a running shred with new code.

        Args:
            shred_id: ID of shred to replace
            code: New ChucK source code
            args: Optional arguments string

        Returns:
            New shred ID if successful, 0 otherwise
        """
        return self._chuck.replace_shred(shred_id, code, args)

    def shred_info(self, shred_id: int) -> dict | None:
        """Get information about a shred.

        Returns:
            Dict with shred info, or None if not found
        """
        return self._chuck.get_shred_info(shred_id)

    def clear(self) -> None:
        """Remove all shreds from the VM.

        Warning:
            Not thread-safe during real-time audio playback.
            Call stop_audio() before clearing the VM.
        """
        self._chuck.clear_vm()

    def reset_id(self) -> None:
        """Reset the shred ID counter."""
        self._chuck.reset_shred_id()

    # -------------------------------------------------------------------------
    # Global variables
    # -------------------------------------------------------------------------

    def set_int(self, name: str, value: int) -> None:
        """Set a global int variable."""
        self._chuck.set_global_int(name, value)

    def get_int(self, name: str, run_frames: int = 256) -> int:
        """Get a global int variable.

        Args:
            name: Variable name
            run_frames: Number of frames to run for callback to execute

        Returns:
            The variable value
        """
        result: list[int] = []
        self._chuck.get_global_int(name, lambda v: result.append(v))
        self.run(run_frames)
        if not result:
            raise RuntimeError(
                f"Failed to get global int '{name}' - callback not invoked. "
                f"Try increasing run_frames (currently {run_frames})."
            )
        return result[0]

    def set_float(self, name: str, value: float) -> None:
        """Set a global float variable."""
        self._chuck.set_global_float(name, value)

    def get_float(self, name: str, run_frames: int = 256) -> float:
        """Get a global float variable.

        Args:
            name: Variable name
            run_frames: Number of frames to run for callback to execute

        Returns:
            The variable value
        """
        result: list[float] = []
        self._chuck.get_global_float(name, lambda v: result.append(v))
        self.run(run_frames)
        if not result:
            raise RuntimeError(
                f"Failed to get global float '{name}' - callback not invoked. "
                f"Try increasing run_frames (currently {run_frames})."
            )
        return result[0]

    def set_string(self, name: str, value: str) -> None:
        """Set a global string variable."""
        self._chuck.set_global_string(name, value)

    def get_string(self, name: str, run_frames: int = 256) -> str:
        """Get a global string variable.

        Args:
            name: Variable name
            run_frames: Number of frames to run for callback to execute

        Returns:
            The variable value
        """
        result: list[str] = []
        self._chuck.get_global_string(name, lambda v: result.append(v))
        self.run(run_frames)
        if not result:
            raise RuntimeError(
                f"Failed to get global string '{name}' - callback not invoked. "
                f"Try increasing run_frames (currently {run_frames})."
            )
        return result[0]

    def get_int_async(self, name: str, callback: Callable[[int], None]) -> None:
        """Get a global int variable asynchronously.

        The callback will be invoked during the next run() call.
        """
        self._chuck.get_global_int(name, callback)

    def get_float_async(self, name: str, callback: Callable[[float], None]) -> None:
        """Get a global float variable asynchronously.

        The callback will be invoked during the next run() call.
        """
        self._chuck.get_global_float(name, callback)

    def get_string_async(self, name: str, callback: Callable[[str], None]) -> None:
        """Get a global string variable asynchronously.

        The callback will be invoked during the next run() call.
        """
        self._chuck.get_global_string(name, callback)

    # -------------------------------------------------------------------------
    # Global events
    # -------------------------------------------------------------------------

    def signal_event(self, name: str) -> None:
        """Signal a global event (wakes one waiting shred)."""
        self._chuck.signal_global_event(name)

    def broadcast_event(self, name: str) -> None:
        """Broadcast a global event (wakes all waiting shreds)."""
        self._chuck.broadcast_global_event(name)

    def on_event(
        self, name: str, callback: Callable[[], None], listen_forever: bool = True
    ) -> int:
        """Register a callback for a global event.

        Args:
            name: Event name
            callback: Function to call when event fires
            listen_forever: If True, callback persists; if False, removed after first call

        Returns:
            Callback ID for use with stop_listening_for_event
        """
        return self._chuck.listen_for_global_event(name, callback, listen_forever)

    def stop_listening_for_event(self, name: str, callback_id: int) -> None:
        """Stop listening for a global event.

        Args:
            name: Event name
            callback_id: ID returned by on_event
        """
        self._chuck.stop_listening_for_global_event(name, callback_id)

    # -------------------------------------------------------------------------
    # Console output
    # -------------------------------------------------------------------------

    def set_stdout_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for ChucK stdout (chout) output."""
        self._chuck.set_stdout_callback(callback)

    def set_stderr_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for ChucK stderr (cherr) output."""
        self._chuck.set_stderr_callback(callback)

    # -------------------------------------------------------------------------
    # Access to low-level API
    # -------------------------------------------------------------------------

    @property
    def raw(self) -> _numchuck.ChucK:
        """Access the underlying low-level ChucK instance."""
        return self._chuck
