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

from ..constants import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT


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
    edit_parser.add_argument(
        "--otf",
        action="store_true",
        help="Enable on-the-fly programming listener",
    )
    edit_parser.add_argument(
        "--otf-port",
        type=int,
        default=8888,
        help="OTF listener port (default: 8888)",
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
    repl_parser.add_argument(
        "--otf",
        action="store_true",
        help="Enable on-the-fly programming listener",
    )
    repl_parser.add_argument(
        "--otf-port",
        type=int,
        default=8888,
        help="OTF listener port (default: 8888)",
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
    run_parser.add_argument(
        "--otf",
        action="store_true",
        help="Enable on-the-fly programming listener",
    )
    run_parser.add_argument(
        "--otf-port",
        type=int,
        default=8888,
        help="OTF listener port (default: 8888)",
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

    # web subcommand
    web_parser = subparsers.add_parser(
        "web", help="Launch browser-based ChucK IDE (WebChucK-style)"
    )
    web_parser.add_argument(
        "files",
        nargs="*",
        help="ChucK files to load on startup",
    )
    web_parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=DEFAULT_WEB_PORT,
        help=f"HTTP port to listen on (default: {DEFAULT_WEB_PORT})",
    )
    web_parser.add_argument(
        "--host",
        default=DEFAULT_WEB_HOST,
        help=(
            f"Address to bind (default: {DEFAULT_WEB_HOST}). The IDE runs "
            "arbitrary ChucK, so anything other than loopback exposes the VM "
            "to the network and is issued an auth token automatically"
        ),
    )
    web_parser.add_argument(
        "--token",
        default=None,
        help=(
            "Auth token clients must present. Generated automatically and "
            "included in the URL opened in the browser; pass an empty string "
            "to disable auth entirely"
        ),
    )
    web_parser.add_argument(
        "--srate",
        type=int,
        default=44100,
        help="Sample rate in Hz (default: 44100)",
    )
    web_parser.add_argument(
        "--channels",
        "-c",
        type=int,
        default=2,
        help="Number of output channels (default: 2)",
    )
    web_parser.add_argument(
        "--start-audio",
        action="store_true",
        help="Start audio automatically on startup",
    )
    web_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )

    # Opting into a project-local ./.numchuck. Off by default because that
    # directory can supply chugins, which are native libraries loaded into this
    # process -- see numchuck.paths for the reasoning.
    for subparser in (edit_parser, repl_parser, run_parser, web_parser, watch_parser):
        subparser.add_argument(
            "--local",
            action="store_true",
            help=(
                "use ./.numchuck (snippets, themes, chugins, config) in "
                "preference to ~/.numchuck; off by default because chugins are "
                "native code"
            ),
        )

    return parser


def cmd_edit(args: argparse.Namespace) -> None:
    """Launch the multi-tab editor."""
    from ..tui.editor import main as editor_main

    editor_main(
        files=args.files,
        project_name=args.project,
        start_audio=args.start_audio,
        otf_enable=args.otf,
        otf_port=args.otf_port,
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
        otf_enable=args.otf,
        otf_port=args.otf_port,
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
        otf_enable=args.otf,
        otf_port=args.otf_port,
    )


def cmd_version(args: argparse.Namespace) -> None:
    """Show version information."""
    from .._numchuck import version
    from .._version import __version__

    print(f"numchuck version: {__version__}")
    print(f"ChucK version: {version()}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show ChucK and numchuck info."""
    from pathlib import Path

    from .._numchuck import ChucK, version
    from .._version import __version__

    print(f"numchuck: {__version__}")
    print(f"ChucK: {version()}")
    print(f"ChucK int size: {ChucK.int_size()} bits")
    print(f"Active VMs: {ChucK.num_vms()}")

    # Bundled chugins
    bundled_dir = Path(__file__).resolve().parent.parent / "chugins"
    if bundled_dir.is_dir():
        chugins = sorted(p.stem for p in bundled_dir.glob("*.chug"))
        print(f"Bundled chugins ({len(chugins)}): {', '.join(chugins)}")
    else:
        print("Bundled chugins: none")


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


def cmd_web(args: argparse.Namespace) -> None:
    """Launch browser-based ChucK IDE."""
    import signal
    import webbrowser

    try:
        from ..web import WEB_AVAILABLE, WebChuckServer, is_loopback_host
    except ImportError:
        print("Error: Web module not available.")
        print("Rebuild numchuck with -DNUMCHUCK_ENABLE_WEB=ON")
        sys.exit(1)

    if not WEB_AVAILABLE:
        print("Error: Web module not available.")
        print("Rebuild numchuck with -DNUMCHUCK_ENABLE_WEB=ON")
        sys.exit(1)

    from .. import Chuck
    from .._numchuck import start_audio, stop_audio

    # Create ChucK instance
    chuck = Chuck(
        sample_rate=args.srate,
        output_channels=args.channels,
    )

    # Create and start web server
    server = WebChuckServer(
        chuck, port=args.port, host=args.host, auth_token=args.token
    )

    # Track if audio was started
    audio_started = False

    # Flag to signal shutdown
    shutdown_requested = False

    # Handle Ctrl+C gracefully
    def signal_handler(sig: int, frame: object) -> None:
        nonlocal shutdown_requested
        print("\nShutting down...")
        shutdown_requested = True

    signal.signal(signal.SIGINT, signal_handler)

    try:
        server.start()
        print("numchuck Web IDE running. Open this URL:")
        print(f"    {server.url}")
        if server.auth_token:
            # The token is in the URL above; say so, because a bare
            # http://host:port typed from memory will be refused.
            print("  (the token in that URL is required -- a plain "
                  f"http://{args.host}:{args.port} will not authenticate)")
        else:
            print("  WARNING: auth disabled -- any process on this machine can "
                  "run code through this server")
        if not is_loopback_host(args.host):
            print(
                f"  WARNING: bound to {args.host} -- anyone who can reach this "
                "port and token can run code on this machine"
            )
        print("Press Ctrl+C to stop")

        # Load any initial files
        for filepath in args.files:
            try:
                success, shred_ids = chuck.compile_file(filepath)
                if success:
                    print(f"  Loaded {filepath} -> shred {shred_ids}")
            except Exception as e:
                print(f"  Failed to load {filepath}: {e}")

        # Start audio if requested
        if args.start_audio:
            start_audio(chuck.raw)
            audio_started = True
            print("  Audio started")

        # Open the browser on the tokenized URL, which is the only form that
        # authenticates. The page lifts the token out of the query string,
        # keeps it for the session and scrubs it from the address bar.
        if not args.no_browser:
            if not webbrowser.open(server.url):
                print("  (could not open a browser -- visit the URL above)")

        # Keep running until interrupted
        from ..constants import SHUTDOWN_DELAY
        import time

        while server.is_running and not shutdown_requested:
            time.sleep(SHUTDOWN_DELAY)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        # Stop server first
        server.stop()
        # Stop audio if it was started
        if audio_started:
            stop_audio()
        # Clean up ChucK instance
        chuck.close()


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if getattr(args, "local", False):
        from ..paths import enable_local_dir

        enable_local_dir()
        print("using ./.numchuck (local chugins are native code)", file=sys.stderr)

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
        "web": cmd_web,
    }

    # Execute command
    if args.command in command_handlers:
        command_handlers[args.command](args)
    elif args.command is None and sys.stdin.isatty():
        # No subcommand on an interactive terminal -- default to REPL
        args.start_audio = False
        args.no_smart_enter = False
        args.no_sidebar = False
        args.project = None
        args.files = []
        args.stdin = False
        args.otf = False
        args.otf_port = 8888
        cmd_repl(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
