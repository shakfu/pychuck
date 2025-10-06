"""Python bindings for ChucK audio programming language"""

import numpy as np
from typing import Any, Callable

# Parameter constants
PARAM_AUTO_DEPEND: str
PARAM_CHUGIN_ENABLE: str
PARAM_COMPILER_HIGHLIGHT_ON_ERROR: str
PARAM_DEPRECATE_LEVEL: str
PARAM_DUMP_INSTRUCTIONS: str
PARAM_IMPORT_PATH_PACKAGES: str
PARAM_IMPORT_PATH_SYSTEM: str
PARAM_IMPORT_PATH_USER: str
PARAM_INPUT_CHANNELS: str
PARAM_IS_REALTIME_AUDIO_HINT: str
PARAM_OTF_ENABLE: str
PARAM_OTF_PORT: str
PARAM_OTF_PRINT_WARNINGS: str
PARAM_OUTPUT_CHANNELS: str
PARAM_SAMPLE_RATE: str
PARAM_TTY_COLOR: str
PARAM_TTY_WIDTH_HINT: str
PARAM_USER_CHUGINS: str
PARAM_VERSION: str
PARAM_VM_ADAPTIVE: str
PARAM_VM_HALT: str
PARAM_WORKING_DIRECTORY: str

class ChucK:
    """ChucK virtual machine and compiler"""

    def __init__(self) -> None:
        """Create a new ChucK instance"""
        ...

    def init(self) -> bool:
        """Initialize ChucK instance with current parameters"""
        ...

    def start(self) -> bool:
        """Explicitly start ChucK (called implicitly by run if needed)"""
        ...

    def set_param(self, name: str, value: int) -> int:
        """Set an integer parameter"""
        ...

    def set_param_float(self, name: str, value: float) -> int:
        """Set a float parameter"""
        ...

    def set_param_string(self, name: str, value: str) -> int:
        """Set a string parameter"""
        ...

    def set_param_string_list(self, name: str, value: list[str]) -> int:
        """Set a string list parameter"""
        ...

    def get_param_int(self, name: str) -> int:
        """Get an integer parameter"""
        ...

    def get_param_float(self, name: str) -> float:
        """Get a float parameter"""
        ...

    def get_param_string(self, name: str) -> str:
        """Get a string parameter"""
        ...

    def get_param_string_list(self, name: str) -> list[str]:
        """Get a string list parameter"""
        ...

    def compile_code(
        self,
        code: str,
        args: str = "",
        count: int = 1,
        immediate: bool = False,
        filepath: str = ""
    ) -> tuple[bool, list[int]]:
        """Compile ChucK code and return (success, shred_ids)"""
        ...

    def compile_file(
        self,
        path: str,
        args: str = "",
        count: int = 1,
        immediate: bool = False
    ) -> tuple[bool, list[int]]:
        """Compile a ChucK file and return (success, shred_ids)"""
        ...

    def run(self, input: np.ndarray, output: np.ndarray, num_frames: int) -> None:
        """Run ChucK audio processing for num_frames"""
        ...

    def remove_all_shreds(self) -> None:
        """Remove all currently running shreds"""
        ...

    def is_init(self) -> bool:
        """Check if ChucK instance is initialized"""
        ...

    def vm_running(self) -> bool:
        """Check if VM is running"""
        ...

    def now(self) -> float:
        """Get current ChucK time"""
        ...

    def toggle_global_color_textoutput(self, onOff: bool) -> None:
        """Set whether ChucK generates color output for messages"""
        ...

    def probe_chugins(self) -> None:
        """Probe and print info on all chugins"""
        ...

    def set_chout_callback(self, callback: Callable[[str], None]) -> bool:
        """Set callback for chout output"""
        ...

    def set_cherr_callback(self, callback: Callable[[str], None]) -> bool:
        """Set callback for cherr output"""
        ...

    # Global variable management - primitives
    def set_global_int(self, name: str, value: int) -> None:
        """Set a global int variable"""
        ...

    def set_global_float(self, name: str, value: float) -> None:
        """Set a global float variable"""
        ...

    def set_global_string(self, name: str, value: str) -> None:
        """Set a global string variable"""
        ...

    def get_global_int(self, name: str, callback: Callable[[int], None]) -> None:
        """Get a global int variable (async via callback)"""
        ...

    def get_global_float(self, name: str, callback: Callable[[float], None]) -> None:
        """Get a global float variable (async via callback)"""
        ...

    def get_global_string(self, name: str, callback: Callable[[str], None]) -> None:
        """Get a global string variable (async via callback)"""
        ...

    # Global variable management - arrays
    def set_global_int_array(self, name: str, values: list[int]) -> None:
        """Set a global int array variable"""
        ...

    def set_global_float_array(self, name: str, values: list[float]) -> None:
        """Set a global float array variable"""
        ...

    def set_global_int_array_value(self, name: str, index: int, value: int) -> None:
        """Set a global int array element by index"""
        ...

    def set_global_float_array_value(self, name: str, index: int, value: float) -> None:
        """Set a global float array element by index"""
        ...

    def set_global_associative_int_array_value(self, name: str, key: str, value: int) -> None:
        """Set a global associative int array element by key"""
        ...

    def set_global_associative_float_array_value(self, name: str, key: str, value: float) -> None:
        """Set a global associative float array element by key"""
        ...

    def get_global_int_array(self, name: str, callback: Callable[[list[int]], None]) -> None:
        """Get a global int array (async via callback)"""
        ...

    def get_global_float_array(self, name: str, callback: Callable[[list[float]], None]) -> None:
        """Get a global float array (async via callback)"""
        ...

    # Global event management
    def signal_global_event(self, name: str) -> None:
        """Signal a global event (wakes one waiting shred)"""
        ...

    def broadcast_global_event(self, name: str) -> None:
        """Broadcast a global event (wakes all waiting shreds)"""
        ...

    def listen_for_global_event(self, name: str, callback: Callable[[], None], listen_forever: bool = True) -> int:
        """Listen for a global event and call Python callback when triggered (returns listener ID)"""
        ...

    def stop_listening_for_global_event(self, name: str, callback_id: int) -> None:
        """Stop listening for a global event using the listener ID"""
        ...

    # Introspection
    def get_all_globals(self) -> list[tuple[str, str]]:
        """Get list of all global variables as (type, name) pairs"""
        ...

    # Shred management and introspection
    def remove_shred(self, shred_id: int) -> None:
        """Remove a shred by ID"""
        ...

    def get_all_shred_ids(self) -> list[int]:
        """Get IDs of all running shreds"""
        ...

    def get_ready_shred_ids(self) -> list[int]:
        """Get IDs of all ready (not blocked) shreds"""
        ...

    def get_blocked_shred_ids(self) -> list[int]:
        """Get IDs of all blocked shreds"""
        ...

    def get_last_shred_id(self) -> int:
        """Get ID of last sporked shred"""
        ...

    def get_next_shred_id(self) -> int:
        """Get what the next shred ID will be"""
        ...

    def get_shred_info(self, shred_id: int) -> dict[str, Any]:
        """Get information about a shred"""
        ...

    # VM control messages
    def clear_vm(self) -> None:
        """Clear the VM (remove all shreds)"""
        ...

    def clear_globals(self) -> None:
        """Clear global variables without clearing the VM"""
        ...

    def reset_shred_id(self) -> None:
        """Reset the shred ID counter"""
        ...

    def replace_shred(self, shred_id: int, code: str, args: str = "") -> int:
        """Replace a running shred with new code (returns new shred ID)"""
        ...

    @staticmethod
    def version() -> str:
        """Get ChucK version string"""
        ...

    @staticmethod
    def int_size() -> int:
        """Get ChucK int size in bits"""
        ...

    @staticmethod
    def num_vms() -> int:
        """Get number of active ChucK VMs"""
        ...

    @staticmethod
    def set_log_level(level: int) -> None:
        """Set ChucK log level"""
        ...

    @staticmethod
    def get_log_level() -> int:
        """Get ChucK log level"""
        ...

    @staticmethod
    def global_cleanup() -> None:
        """Global cleanup for all ChucK instances"""
        ...

    @staticmethod
    def poop() -> None:
        """ChucK poop compatibility"""
        ...

    @staticmethod
    def set_stdout_callback(callback: Callable[[str], None]) -> bool:
        """Set global stdout callback"""
        ...

    @staticmethod
    def set_stderr_callback(callback: Callable[[str], None]) -> bool:
        """Set global stderr callback"""
        ...

def version() -> str:
    """Get ChucK version"""
    ...

def start_audio(
    chuck: ChucK,
    sample_rate: int = 44100,
    num_dac_channels: int = 2,
    num_adc_channels: int = 0,
    dac_device: int = 0,
    adc_device: int = 0,
    buffer_size: int = 512,
    num_buffers: int = 8
) -> bool:
    """Start real-time audio playback with ChucK instance"""
    ...

def stop_audio() -> bool:
    """Stop real-time audio playback"""
    ...

def shutdown_audio(msWait: int = 0) -> None:
    """Shutdown audio system"""
    ...

def audio_info() -> dict[str, Any]:
    """Get current audio system info"""
    ...