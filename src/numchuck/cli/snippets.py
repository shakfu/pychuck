"""
CLI commands for managing code snippets.

Provides commands to list and show snippets from:
- Local: ./.numchuck/snippets/ (current directory)
- Global: ~/.numchuck/snippets/ (home directory)

Local snippets take precedence over global snippets with the same name.
"""

from __future__ import annotations

from ..paths import (
    get_snippet_path_with_source,
    get_snippets_dir,
    list_all_snippets,
)


def get_snippet_info(name: str) -> dict[str, str] | None:
    """Get information about a snippet.

    Local snippets take precedence over global snippets.

    Args:
        name: Snippet name (without .ck extension)

    Returns:
        Dictionary with 'source', 'path', and 'content' keys, or None if not found
    """
    path, source = get_snippet_path_with_source(name)
    if path is None:
        return None

    return {
        "source": source or "unknown",
        "path": str(path),
        "content": path.read_text(),
    }


def cmd_snippets_list() -> None:
    """List all available snippets."""
    snippets = list_all_snippets()

    if not snippets:
        snippets_dir = get_snippets_dir()
        print("No snippets found")
        print()
        print(f"Create .ck files in {snippets_dir}")
        print("Then use @<name> in the REPL to load them")
        return

    print("Available snippets:")
    for name, source in snippets:
        source_tag = f" ({source})" if source == "global" else ""
        print(f"  @{name}{source_tag}")

    print()
    print("Use 'numchuck snippets show <name>' to view content")


def cmd_snippets_show(name: str) -> None:
    """Show the content of a snippet.

    Args:
        name: Snippet name (without .ck extension)
    """
    info = get_snippet_info(name)
    if info is None:
        print(f"Snippet '{name}' not found")
        print()
        print("Use 'numchuck snippets list' to see available snippets")
        return

    print(f"// Snippet: @{name}")
    print(f"// Source: {info['source']} ({info['path']})")
    print("// " + "-" * 60)
    print(info["content"])


def cmd_snippets_path() -> None:
    """Show the snippets directory path."""
    snippets_dir = get_snippets_dir()
    print(f"Snippets directory: {snippets_dir}")
    if not snippets_dir.exists():
        print("  (directory does not exist)")
