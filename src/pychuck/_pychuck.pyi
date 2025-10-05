"""Python bindings for ChucK audio programming language"""

import numpy as np
from typing import Any

# Parameter constants
PARAM_AUTO_DEPEND: str
PARAM_CHUGIN_ENABLE: str
PARAM_DEPRECATE_LEVEL: str
PARAM_DUMP_INSTRUCTIONS: str
PARAM_INPUT_CHANNELS: str
PARAM_OTF_ENABLE: str
PARAM_OTF_PORT: str
PARAM_OUTPUT_CHANNELS: str
PARAM_SAMPLE_RATE: str
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