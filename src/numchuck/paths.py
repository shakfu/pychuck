"""
Path management for numchuck

Provides centralized management of user directories and files for:
- REPL history
- Code snippets
- Sessions/projects
- Logs
- Configuration

The .numchuck directory is searched in this order:
1. Current working directory (./.numchuck)
2. Home directory (~/.numchuck)

This allows project-specific configuration to override global settings.
"""

from pathlib import Path


def get_numchuck_dir() -> Path:
    """
    Get the active numchuck directory.

    Searches for .numchuck in:
    1. Current working directory (./.numchuck)
    2. Home directory (~/.numchuck)

    Returns the first one that exists, or ~/.numchuck if neither exists.

    Returns:
        Path to the active .numchuck directory
    """
    # Check current working directory first
    cwd_numchuck = Path.cwd() / ".numchuck"
    if cwd_numchuck.exists():
        return cwd_numchuck

    # Fall back to home directory
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


def get_themes_dir() -> Path:
    """
    Get the themes directory.

    Returns:
        Path to themes directory
    """
    return get_numchuck_dir() / "themes"


def get_chugins_dir() -> Path:
    """
    Get the chugins directory.

    Returns:
        Path to chugins directory
    """
    return get_numchuck_dir() / "chugins"


def get_keybindings_dir() -> Path:
    """
    Get the keybindings directory.

    Returns:
        Path to keybindings directory
    """
    return get_numchuck_dir() / "keybindings"


def ensure_numchuck_directories() -> None:
    """
    Ensure all numchuck directories exist in the home directory.

    Creates ~/.numchuck and standard subdirectories if they don't exist.
    """
    numchuck_home = get_numchuck_home()
    numchuck_home.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (numchuck_home / "snippets").mkdir(exist_ok=True)
    (numchuck_home / "sessions").mkdir(exist_ok=True)
    (numchuck_home / "logs").mkdir(exist_ok=True)
    (numchuck_home / "projects").mkdir(exist_ok=True)
    (numchuck_home / "recordings").mkdir(exist_ok=True)
    (numchuck_home / "examples").mkdir(exist_ok=True)
    (numchuck_home / "themes").mkdir(exist_ok=True)
    (numchuck_home / "chugins").mkdir(exist_ok=True)
    (numchuck_home / "keybindings").mkdir(exist_ok=True)


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
