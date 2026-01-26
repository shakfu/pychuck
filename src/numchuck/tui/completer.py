"""
ChucK REPL completer for context-aware tab completion.

Provides intelligent completions based on context:
- After '+': suggest .ck files
- After '-': suggest shred IDs or 'all'
- After '~': suggest shred IDs for replace
- After '?': suggest shred IDs or global variables
- After '::': suggest global variables
- Default: REPL commands and ChucK language identifiers
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Iterator

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document

from ..chuck_lang import ALL_IDENTIFIERS, REPL_COMMANDS

if TYPE_CHECKING:
    from .session import ChuckSession


class ChuckCompleter(Completer):
    """Context-aware completer for the ChucK REPL.

    Provides intelligent completions based on the current input context.

    Args:
        session: ChuckSession instance for accessing shreds and globals
        chuck: ChucK instance for querying global variables
    """

    def __init__(self, session: ChuckSession, chuck):
        """Initialize the completer.

        Args:
            session: ChuckSession for shred tracking
            chuck: ChucK instance for global variable queries
        """
        self.session = session
        self.chuck = chuck
        self.path_completer = PathCompleter(
            file_filter=lambda filename: filename.endswith(".ck")
            or os.path.isdir(filename),
            expanduser=True,
        )
        # Use REPL_COMMANDS from chuck_lang as source of truth
        self.commands = sorted(REPL_COMMANDS)

    def _get_shred_ids(self) -> Iterator[str]:
        """Get active shred IDs as strings."""
        try:
            for sid in self.session.shreds.keys():
                yield str(sid)
        except (AttributeError, RuntimeError):
            pass

    def _get_globals(self) -> Iterator[tuple[str, str]]:
        """Get global variables as (type, name) pairs."""
        try:
            return iter(self.chuck.get_all_globals())
        except (AttributeError, RuntimeError):
            return iter([])

    def _complete_path(self, text: str, complete_event) -> Iterator[Completion]:
        """Complete file paths for .ck files."""
        path_doc = Document(text, len(text))
        yield from self.path_completer.get_completions(path_doc, complete_event)

    def _complete_shred_ids(
        self, prefix: str, include_all: bool = False
    ) -> Iterator[Completion]:
        """Complete shred IDs, optionally including 'all'."""
        if include_all and "all".startswith(prefix):
            yield Completion("all", start_position=-len(prefix))

        for sid_str in self._get_shred_ids():
            if sid_str.startswith(prefix):
                yield Completion(sid_str, start_position=-len(prefix))

    def _complete_globals(self, prefix: str, suffix: str = "") -> Iterator[Completion]:
        """Complete global variable names."""
        for typ, name in self._get_globals():
            if name.startswith(prefix):
                yield Completion(
                    name + suffix,
                    start_position=-len(prefix) - len(suffix),
                )

    def get_completions(self, document, complete_event) -> Iterator[Completion]:
        """Get completions based on current document context.

        Args:
            document: The current prompt_toolkit Document
            complete_event: The completion event

        Yields:
            Completion objects for matching completions
        """
        text = document.text.strip()

        # Get the word before cursor for ChucK code completion
        word_before_cursor = document.get_word_before_cursor(WORD=True)

        # After '+', suggest .ck files
        if text.startswith("+ ") and len(text) > 2:
            path_text = text[2:].strip()
            yield from self._complete_path(path_text, complete_event)

        # After '-', suggest shred IDs or 'all'
        elif text.startswith("- ") and len(text) > 2:
            prefix = text[2:].strip()
            yield from self._complete_shred_ids(prefix, include_all=True)

        # After '~', suggest shred IDs
        elif text.startswith("~ ") and len(text) > 2:
            parts = text[2:].strip()
            if " " not in parts:  # Still typing shred ID
                yield from self._complete_shred_ids(parts)

        # After '? ', suggest shred IDs
        elif text.startswith("? ") and len(text) > 2:
            prefix = text[2:].strip()
            yield from self._complete_shred_ids(prefix)

        # After '<name>?', suggest global names with '?' suffix
        elif "?" in text and not text.startswith("?"):
            prefix = text.split("?")[0]
            for typ, name in self._get_globals():
                if name.startswith(prefix):
                    yield Completion(name + "?", start_position=-len(text))

        # After '<name>::', suggest global names with '::' suffix
        elif "::" in text:
            prefix = text.split("::")[0]
            for typ, name in self._get_globals():
                if name.startswith(prefix):
                    yield Completion(name + "::", start_position=-len(text))

        # After ': ', suggest .ck files (compile mode)
        elif text.startswith(": ") and len(text) > 2:
            path_text = text[2:].strip()
            yield from self._complete_path(path_text, complete_event)

        # Default: suggest REPL commands or ChucK identifiers
        else:
            # First priority: REPL commands (if text matches command patterns)
            repl_command_matched = False
            for cmd in self.commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))
                    repl_command_matched = True

            # Second priority: ChucK language identifiers (keywords, types, UGens, etc.)
            # Only suggest ChucK completions if:
            # 1. No REPL commands matched, OR
            # 2. We're completing a word within ChucK code (word_before_cursor exists)
            if not repl_command_matched or word_before_cursor:
                for identifier in sorted(ALL_IDENTIFIERS):
                    if identifier.startswith(word_before_cursor):
                        yield Completion(
                            identifier,
                            start_position=-len(word_before_cursor),
                            display_meta="ChucK",
                        )
