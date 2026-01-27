#!/usr/bin/env python3
"""
numchuck command-line interface

Provides subcommands for different numchuck modes:
    edit    - Launch multi-tab editor for livecoding
    repl    - Launch interactive REPL
    run     - Execute ChucK files from command line
    version - Show version information
    info    - Show ChucK and numchuck info
"""

import sys
import argparse


def _chump_available() -> bool:
    """Check if the _chump module is available."""
    try:
        from .. import _chump  # noqa: F401

        return True
    except ImportError:
        return False


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="numchuck",
        description="Python bindings for ChucK audio programming language",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # edit subcommand
    edit_parser = subparsers.add_parser(
        "edit", help="Launch multi-tab editor for livecoding"
    )
    edit_parser.add_argument("files", nargs="*", help="ChucK files to open in tabs")
    edit_parser.add_argument(
        "--project", type=str, help="Project name for versioned file storage"
    )
    edit_parser.add_argument(
        "--start-audio",
        action="store_true",
        help="Start audio automatically on startup",
    )

    # repl subcommand
    repl_parser = subparsers.add_parser("repl", help="Launch interactive REPL")
    repl_parser.add_argument("files", nargs="*", help="ChucK files to load on startup")
    repl_parser.add_argument(
        "--start-audio",
        action="store_true",
        help="Start audio automatically on REPL startup",
    )
    repl_parser.add_argument(
        "--no-smart-enter",
        action="store_true",
        help="Disable smart Enter mode (always require Esc+Enter to submit)",
    )
    repl_parser.add_argument(
        "--no-sidebar",
        action="store_true",
        help="Hide topbar showing active shreds (can toggle with F2)",
    )
    repl_parser.add_argument(
        "--project", type=str, help="Project name for versioned file storage"
    )
    repl_parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read commands from stdin (non-interactive mode for testing/scripting)",
    )

    # run subcommand
    run_parser = subparsers.add_parser(
        "run", help="Execute ChucK files from command line"
    )
    run_parser.add_argument("files", nargs="+", help="ChucK files to execute")
    run_parser.add_argument(
        "--srate", type=int, default=44100, help="Sample rate (default: 44100)"
    )
    run_parser.add_argument(
        "--channels", type=int, default=2, help="Number of audio channels (default: 2)"
    )
    run_parser.add_argument(
        "--silent",
        action="store_true",
        help="Run without audio output (useful for testing)",
    )
    run_parser.add_argument(
        "--duration",
        type=float,
        help="Run for specified duration in seconds, then exit",
    )

    # version subcommand
    subparsers.add_parser("version", help="Show version information")

    # info subcommand
    subparsers.add_parser("info", help="Show ChucK and numchuck info")

    # export subcommand
    export_parser = subparsers.add_parser(
        "export", help="Export ChucK files to WAV audio"
    )
    export_parser.add_argument("output", help="Output WAV file path")
    export_parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        required=True,
        help="ChucK files to render",
    )
    export_parser.add_argument(
        "--duration",
        "-d",
        type=float,
        default=10.0,
        help="Duration in seconds (default: 10.0)",
    )
    export_parser.add_argument(
        "--srate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)",
    )
    export_parser.add_argument(
        "--channels",
        "-c",
        type=int,
        default=2,
        help="Number of output channels (default: 2)",
    )

    # snippets subcommand
    snippets_parser = subparsers.add_parser("snippets", help="Manage code snippets")
    snippets_subparsers = snippets_parser.add_subparsers(
        dest="snippets_command", help="Snippets commands"
    )

    # snippets list
    snippets_subparsers.add_parser("list", help="List all available snippets")

    # snippets show
    snippets_show_parser = snippets_subparsers.add_parser(
        "show", help="Show snippet content"
    )
    snippets_show_parser.add_argument("name", help="Snippet name (without .ck)")

    # snippets path
    snippets_subparsers.add_parser("path", help="Show snippets directory path")

    # watch subcommand
    watch_parser = subparsers.add_parser(
        "watch", help="Watch ChucK files and auto-reload on changes"
    )
    watch_parser.add_argument(
        "files",
        nargs="+",
        help="ChucK files to watch",
    )
    watch_parser.add_argument(
        "--srate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)",
    )
    watch_parser.add_argument(
        "--channels",
        "-c",
        type=int,
        default=2,
        help="Number of output channels (default: 2)",
    )
    watch_parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress status messages",
    )

    # pkg subcommand - package management (only if _chump is available)
    if _chump_available():
        pkg_parser = subparsers.add_parser("pkg", help="Manage ChucK packages")
        pkg_subparsers = pkg_parser.add_subparsers(
            dest="pkg_command", help="Package commands"
        )

        # pkg list
        pkg_list_parser = pkg_subparsers.add_parser(
            "list", help="List available packages"
        )
        pkg_list_parser.add_argument(
            "--installed",
            action="store_true",
            help="Show only installed packages",
        )

        # pkg info
        pkg_info_parser = pkg_subparsers.add_parser("info", help="Show package details")
        pkg_info_parser.add_argument("name", help="Package name")

        # pkg install
        pkg_install_parser = pkg_subparsers.add_parser(
            "install", help="Install a package"
        )
        pkg_install_parser.add_argument(
            "package",
            help="Package name (optionally with version: name@version)",
        )

        # pkg uninstall
        pkg_uninstall_parser = pkg_subparsers.add_parser(
            "uninstall", help="Uninstall a package"
        )
        pkg_uninstall_parser.add_argument("name", help="Package name")
        pkg_uninstall_parser.add_argument(
            "--force",
            action="store_true",
            help="Force removal even if files have been modified",
        )

        # pkg update
        pkg_update_parser = pkg_subparsers.add_parser(
            "update", help="Update a package or all packages"
        )
        pkg_update_parser.add_argument(
            "name",
            nargs="?",
            help="Package name (omit to update all)",
        )

        # pkg refresh
        pkg_subparsers.add_parser("refresh", help="Update package manifest from server")

        # pkg search
        pkg_search_parser = pkg_subparsers.add_parser(
            "search", help="Search for packages"
        )
        pkg_search_parser.add_argument("query", help="Search query")

        # pkg path
        pkg_subparsers.add_parser("path", help="Show packages directory path")

    return parser


def cmd_edit(args: argparse.Namespace) -> None:
    """Launch the multi-tab editor."""
    from ..tui.editor import main as editor_main

    editor_main(
        files=args.files, project_name=args.project, start_audio=args.start_audio
    )


def cmd_repl(args: argparse.Namespace) -> None:
    """Launch the interactive REPL."""
    from ..tui.tui import main as tui_main

    # Get project name from args if provided
    project_name = getattr(args, "project", None)
    force_stdin = getattr(args, "stdin", False)

    tui_main(
        start_audio=args.start_audio,
        smart_enter=not args.no_smart_enter,
        show_sidebar=not args.no_sidebar,
        project_name=project_name,
        files=getattr(args, "files", []),
        force_stdin=force_stdin,
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Execute ChucK files from command line."""
    from .executor import execute_files

    execute_files(
        files=args.files,
        srate=args.srate,
        channels=args.channels,
        silent=args.silent,
        duration=args.duration,
    )


def cmd_version(args: argparse.Namespace) -> None:
    """Show version information."""
    from .._numchuck import version
    from .._version import __version__

    print(f"numchuck version: {__version__}")
    print(f"ChucK version: {version()}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show ChucK and numchuck info."""
    from .._numchuck import ChucK, version
    from .._version import __version__

    print(f"numchuck: {__version__}")
    print(f"ChucK: {version()}")
    print(f"ChucK int size: {ChucK.int_size()} bits")
    print(f"Active VMs: {ChucK.num_vms()}")


def cmd_export(args: argparse.Namespace) -> None:
    """Export ChucK files to WAV audio."""
    from .. import RenderError, to_wav

    try:
        output_path = to_wav(
            output=args.output,
            files=args.files,
            duration=args.duration,
            sample_rate=args.srate,
            channels=args.channels,
        )
        print(f"Exported to {output_path}")
        print(f"  Duration: {args.duration}s")
        print(f"  Sample rate: {args.srate} Hz")
        print(f"  Channels: {args.channels}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RenderError as e:
        print(f"Export failed: {e}")
        sys.exit(1)


def cmd_snippets(args: argparse.Namespace) -> None:
    """Manage code snippets."""
    from .snippets import (
        cmd_snippets_list,
        cmd_snippets_path,
        cmd_snippets_show,
    )

    if args.snippets_command == "list" or args.snippets_command is None:
        cmd_snippets_list()
    elif args.snippets_command == "show":
        cmd_snippets_show(args.name)
    elif args.snippets_command == "path":
        cmd_snippets_path()
    else:
        # Default to list if no subcommand
        cmd_snippets_list()


def cmd_watch(args: argparse.Namespace) -> None:
    """Watch ChucK files and auto-reload on changes."""
    from .watcher import cmd_watch as run_watch

    run_watch(
        files=args.files,
        sample_rate=args.srate,
        channels=args.channels,
        quiet=args.quiet,
    )


def cmd_pkg(args: argparse.Namespace) -> None:
    """Manage ChucK packages."""
    from .packages import (
        cmd_pkg_info,
        cmd_pkg_install,
        cmd_pkg_list,
        cmd_pkg_path,
        cmd_pkg_refresh,
        cmd_pkg_search,
        cmd_pkg_uninstall,
        cmd_pkg_update,
    )

    if args.pkg_command == "list" or args.pkg_command is None:
        cmd_pkg_list(installed_only=getattr(args, "installed", False))
    elif args.pkg_command == "info":
        cmd_pkg_info(args.name)
    elif args.pkg_command == "install":
        cmd_pkg_install(args.package)
    elif args.pkg_command == "uninstall":
        cmd_pkg_uninstall(args.name, force=args.force)
    elif args.pkg_command == "update":
        cmd_pkg_update(args.name)
    elif args.pkg_command == "refresh":
        cmd_pkg_refresh()
    elif args.pkg_command == "search":
        cmd_pkg_search(args.query)
    elif args.pkg_command == "path":
        cmd_pkg_path()
    else:
        cmd_pkg_list()


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Map commands to handlers
    command_handlers = {
        "edit": cmd_edit,
        "repl": cmd_repl,
        "run": cmd_run,
        "version": cmd_version,
        "info": cmd_info,
        "export": cmd_export,
        "snippets": cmd_snippets,
        "watch": cmd_watch,
    }

    # Add pkg handler only if _chump is available
    if _chump_available():
        command_handlers["pkg"] = cmd_pkg

    # Execute command
    if args.command in command_handlers:
        command_handlers[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
