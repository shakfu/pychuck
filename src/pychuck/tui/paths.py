"""
Path management for pychuck CLI

Provides centralized management of user directories and files for:
- REPL history
- Code snippets
- Sessions/projects
- Logs
- Configuration
"""

from pathlib import Path


def get_pychuck_home() -> Path:
    """
    Get the pychuck home directory (~/.pychuck).

    Returns:
        Path to ~/.pychuck directory
    """
    return Path.home() / '.pychuck'


def get_snippets_dir() -> Path:
    """
    Get the snippets directory (~/.pychuck/snippets).

    This directory stores reusable ChucK code snippets that can be
    loaded with the @<name> command in the REPL.

    Returns:
        Path to ~/.pychuck/snippets directory
    """
    return get_pychuck_home() / 'snippets'


def get_history_file() -> Path:
    """
    Get the REPL history file path (~/.pychuck/history).

    Returns:
        Path to ~/.pychuck/history file
    """
    return get_pychuck_home() / 'history'


def get_sessions_dir() -> Path:
    """
    Get the sessions directory (~/.pychuck/sessions).

    This directory can store saved REPL sessions, allowing users to
    save and restore their work.

    Returns:
        Path to ~/.pychuck/sessions directory
    """
    return get_pychuck_home() / 'sessions'


def get_logs_dir() -> Path:
    """
    Get the logs directory (~/.pychuck/logs).

    This directory can store ChucK VM logs, audio engine logs,
    and REPL debugging output.

    Returns:
        Path to ~/.pychuck/logs directory
    """
    return get_pychuck_home() / 'logs'


def get_config_file() -> Path:
    """
    Get the configuration file path (~/.pychuck/config.toml).

    This file can store user preferences like:
    - Default sample rate
    - Default audio device
    - REPL appearance settings
    - Default chugin paths

    Returns:
        Path to ~/.pychuck/config.toml file
    """
    return get_pychuck_home() / 'config.toml'


def get_projects_dir() -> Path:
    """
    Get the projects directory (~/.pychuck/projects).

    This directory can store multi-file ChucK projects with:
    - Main .ck files
    - Dependencies
    - Audio samples
    - Project configuration

    Returns:
        Path to ~/.pychuck/projects directory
    """
    return get_pychuck_home() / 'projects'


def ensure_pychuck_directories():
    """
    Ensure all pychuck directories exist.

    Creates ~/.pychuck and standard subdirectories if they don't exist:
    - snippets/
    - sessions/
    - logs/
    - projects/
    """
    # Create main directory
    pychuck_home = get_pychuck_home()
    pychuck_home.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    get_snippets_dir().mkdir(exist_ok=True)
    get_sessions_dir().mkdir(exist_ok=True)
    get_logs_dir().mkdir(exist_ok=True)
    get_projects_dir().mkdir(exist_ok=True)


def list_snippets() -> list[str]:
    """
    List all available snippets.

    Returns:
        List of snippet names (without .ck extension)
    """
    snippets_dir = get_snippets_dir()
    if not snippets_dir.exists():
        return []

    return [f.stem for f in snippets_dir.glob('*.ck')]


def get_snippet_path(name: str) -> Path:
    """
    Get the path to a snippet by name.

    Args:
        name: Snippet name (without .ck extension)

    Returns:
        Path to the snippet file
    """
    return get_snippets_dir() / f'{name}.ck'


def list_projects() -> list[str]:
    """
    List all available projects.

    Returns:
        List of project names (directory names in ~/.pychuck/projects/)
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
    from .project import Project
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
