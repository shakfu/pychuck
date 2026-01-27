"""
Services layer for numchuck.

Provides business logic services that can be used by both CLI and TUI:
- AudioService: Audio lifecycle management
- ShredService: Shred compilation and management
- GlobalsService: Global variable and event operations
- FileService: Snippet and project file operations
"""

from .audio import AudioService
from .shreds import ShredService, ShredResult, ShredInfo
from .globals import GlobalsService, GlobalInfo
from .files import FileService, SnippetInfo

__all__ = [
    "AudioService",
    "ShredService",
    "ShredResult",
    "ShredInfo",
    "GlobalsService",
    "GlobalInfo",
    "FileService",
    "SnippetInfo",
]
