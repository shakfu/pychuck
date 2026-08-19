"""
Path management for numchuck

Provides centralized management of user directories and files for:
- REPL history
- Code snippets
- Sessions/projects
- Logs
- Configuration

The .numchuck directory resolves to ~/.numchuck. A project-local
./.numchuck can override it, but only when the caller opts in -- see
``enable_local_dir``.

Why it is opt-in
----------------
The directory supplies config, themes, keybindings and *chugins*, and chugins
are native shared libraries loaded into the process. Honouring ./.numchuck
unconditionally would mean that cloning a repository and running numchuck
inside it executes whatever native code the repository shipped, with no prompt.
So the local directory is used only when the user asks for it (``--local``, or
NUMCHUCK_LOCAL=1 in the environment).
"""

import os
from pathlib import Path

# Whether a project-local ./.numchuck may override ~/.numchuck this session.
_local_dir_enabled = False


def enable_local_dir(enabled: bool = True) -> None:
    """Allow (or forbid) a project-local ./.numchuck to take precedence.

    Args:
        enabled: True to honour ./.numchuck, False to use only ~/.numchuck
    """
    global _local_dir_enabled
    _local_dir_enabled = enabled


def local_dir_enabled() -> bool:
    """Whether a project-local ./.numchuck is currently honoured."""
    return _local_dir_enabled or os.environ.get("NUMCHUCK_LOCAL", "") not in ("", "0")


def get_local_numchuck_dir() -> Path | None:
    """The project-local ./.numchuck, if it exists and is permitted.

    Returns:
        Path to ./.numchuck, or None when absent or not opted in
    """
    if not local_dir_enabled():
        return None
    cwd_numchuck = Path.cwd() / ".numchuck"
    return cwd_numchuck if cwd_numchuck.is_dir() else None


def get_numchuck_dir() -> Path:
    """
    Get the active numchuck directory.

    This is ~/.numchuck, unless a project-local ./.numchuck exists *and* the
    caller opted in via ``enable_local_dir()`` or NUMCHUCK_LOCAL=1.

    Returns:
        Path to the active .numchuck directory
    """
    local = get_local_numchuck_dir()
    if local is not None:
        return local

    return Path.home() / ".numchuck"


def get_numchuck_home() -> Path:
    """
    Get the global numchuck home directory (~/.numchuck).

    This is always the home directory location, regardless of
    whether a local .numchuck exists.

    Returns:
        Path to ~/.numchuck directory
    """
    return Path.home() / ".numchuck"


# The standard layout of a .numchuck directory, named once so the accessors
# below and ensure_numchuck_directories() cannot drift apart.
NUMCHUCK_SUBDIRS = (
    "snippets",
    "sessions",
    "logs",
    "projects",
    "recordings",
    "examples",
    "themes",
    "chugins",
    "keybindings",
)


def get_snippets_dir() -> Path:
    """
    Get the snippets directory.

    Searches .numchuck/snippets in cwd first, then home.

    Returns:
        Path to snippets directory
    """
    return get_numchuck_dir() / "snippets"


def get_history_file() -> Path:
    """
    Get the REPL history file path.

    Returns:
        Path to history file
    """
    return get_numchuck_dir() / "numchuck_history"


def get_sessions_dir() -> Path:
    """
    Get the sessions directory.

    Returns:
        Path to sessions directory
    """
    return get_numchuck_dir() / "sessions"


def get_logs_dir() -> Path:
    """
    Get the logs directory.

    Returns:
        Path to logs directory
    """
    return get_numchuck_dir() / "logs"


def get_config_file() -> Path:
    """
    Get the configuration file path.

    Returns:
        Path to config.toml file
    """
    return get_numchuck_dir() / "config.toml"


def get_projects_dir() -> Path:
    """
    Get the projects directory.

    Returns:
        Path to projects directory
    """
    return get_numchuck_dir() / "projects"


def get_recordings_dir() -> Path:
    """
    Get the recordings directory.

    Returns:
        Path to recordings directory
    """
    return get_numchuck_dir() / "recordings"


def get_examples_dir() -> Path:
    """
    Get the examples directory.

    Returns:
        Path to examples directory
    """
    return get_numchuck_dir() / "examples"


def get_chugins_dir() -> Path:
    """
    Get the chugins directory.

    Returns:
        Path to chugins directory
    """
    return get_numchuck_dir() / "chugins"


def ensure_numchuck_directories() -> None:
    """
    Ensure all numchuck directories exist in the home directory.

    Creates ~/.numchuck and standard subdirectories if they don't exist.
    """
    numchuck_home = get_numchuck_home()
    numchuck_home.mkdir(parents=True, exist_ok=True)

    for name in NUMCHUCK_SUBDIRS:
        (numchuck_home / name).mkdir(exist_ok=True)


def list_snippets() -> list[str]:
    """
    List all available snippets.

    Returns:
        List of snippet names (without .ck extension)
    """
    snippets_dir = get_snippets_dir()
    if not snippets_dir.exists():
        return []

    return sorted(f.stem for f in snippets_dir.glob("*.ck"))


def get_snippet_path(name: str) -> Path | None:
    """
    Get the path to a snippet by name.

    Args:
        name: Snippet name (without .ck extension)

    Returns:
        Path to the snippet file, or None if not found
    """
    snippet_path = get_snippets_dir() / f"{name}.ck"
    if snippet_path.exists():
        return snippet_path
    return None


def list_all_snippets() -> list[tuple[str, str]]:
    """
    List all available snippets with their source.

    Returns:
        List of tuples (name, source) where source is 'local' or 'global'
    """
    result: list[tuple[str, str]] = []
    seen_names: set[str] = set()

    # Check local (./.numchuck/snippets) first
    local_snippets = Path.cwd() / ".numchuck" / "snippets"
    if local_snippets.exists():
        for f in local_snippets.glob("*.ck"):
            result.append((f.stem, "local"))
            seen_names.add(f.stem)

    # Then check global (~/.numchuck/snippets)
    global_snippets = Path.home() / ".numchuck" / "snippets"
    if global_snippets.exists():
        for f in global_snippets.glob("*.ck"):
            if f.stem not in seen_names:
                result.append((f.stem, "global"))

    return sorted(result, key=lambda x: x[0])


def get_snippet_path_with_source(name: str) -> tuple[Path | None, str | None]:
    """
    Get the path to a snippet, searching local then global.

    Local snippets (./.numchuck/snippets) take precedence over
    global snippets (~/.numchuck/snippets).

    Args:
        name: Snippet name (without .ck extension)

    Returns:
        Tuple of (path, source) where source is 'local' or 'global',
        or (None, None) if not found
    """
    # Check local first
    local_path = Path.cwd() / ".numchuck" / "snippets" / f"{name}.ck"
    if local_path.exists():
        return local_path, "local"

    # Check global
    global_path = Path.home() / ".numchuck" / "snippets" / f"{name}.ck"
    if global_path.exists():
        return global_path, "global"

    return None, None


def list_projects() -> list[str]:
    """
    List all available projects.

    Returns:
        List of project names (directory names in projects/)
    """
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return []

    return [d.name for d in projects_dir.iterdir() if d.is_dir()]


def create_project(name: str) -> Path:
    """
    Create a new project directory.

    Args:
        name: Project name

    Returns:
        Path to the created project directory
    """
    from .tui.project import Project

    projects_dir = get_projects_dir()
    project = Project(name, projects_dir)
    return project.project_dir


def get_project_path(name: str) -> Path:
    """
    Get the path to a project by name.

    Args:
        name: Project name

    Returns:
        Path to the project directory
    """
    return get_projects_dir() / name
