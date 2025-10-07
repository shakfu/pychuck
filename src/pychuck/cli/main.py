#!/usr/bin/env python3
"""
pychuck command-line interface

Provides subcommands for different pychuck modes:
    edit    - Launch multi-tab editor for livecoding
    repl    - Launch interactive REPL
    exec    - Execute ChucK files from command line
    version - Show version information
    info    - Show ChucK and pychuck info
"""
import sys
import argparse
from pathlib import Path


def create_parser():
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='pychuck',
        description='Python bindings for ChucK audio programming language'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # edit subcommand
    edit_parser = subparsers.add_parser(
        'edit',
        help='Launch multi-tab editor for livecoding'
    )
    edit_parser.add_argument(
        'files',
        nargs='*',
        help='ChucK files to open in tabs'
    )
    edit_parser.add_argument(
        '--project',
        type=str,
        help='Project name for versioned file storage'
    )
    edit_parser.add_argument(
        '--start-audio',
        action='store_true',
        help='Start audio automatically on startup'
    )

    # repl subcommand
    repl_parser = subparsers.add_parser(
        'repl',
        help='Launch interactive REPL'
    )
    repl_parser.add_argument(
        'files',
        nargs='*',
        help='ChucK files to load on startup'
    )
    repl_parser.add_argument(
        '--start-audio',
        action='store_true',
        help='Start audio automatically on REPL startup'
    )
    repl_parser.add_argument(
        '--no-smart-enter',
        action='store_true',
        help='Disable smart Enter mode (always require Esc+Enter to submit)'
    )
    repl_parser.add_argument(
        '--no-sidebar',
        action='store_true',
        help='Hide topbar showing active shreds (can toggle with F2)'
    )
    repl_parser.add_argument(
        '--project',
        type=str,
        help='Project name for versioned file storage'
    )

    # exec subcommand
    exec_parser = subparsers.add_parser(
        'exec',
        help='Execute ChucK files from command line'
    )
    exec_parser.add_argument(
        'files',
        nargs='+',
        help='ChucK files to execute'
    )
    exec_parser.add_argument(
        '--srate',
        type=int,
        default=44100,
        help='Sample rate (default: 44100)'
    )
    exec_parser.add_argument(
        '--channels',
        type=int,
        default=2,
        help='Number of audio channels (default: 2)'
    )
    exec_parser.add_argument(
        '--silent',
        action='store_true',
        help='Run without audio output (useful for testing)'
    )
    exec_parser.add_argument(
        '--duration',
        type=float,
        help='Run for specified duration in seconds, then exit'
    )

    # version subcommand
    version_parser = subparsers.add_parser(
        'version',
        help='Show version information'
    )

    # info subcommand
    info_parser = subparsers.add_parser(
        'info',
        help='Show ChucK and pychuck info'
    )

    # tui subcommand (backward compatibility - maps to repl)
    tui_parser = subparsers.add_parser(
        'tui',
        help='Launch interactive REPL (alias for repl)'
    )
    tui_parser.add_argument(
        '--start-audio',
        action='store_true',
        help='Start audio automatically on REPL startup'
    )
    tui_parser.add_argument(
        '--no-smart-enter',
        action='store_true',
        help='Disable smart Enter mode (always require Esc+Enter to submit)'
    )
    tui_parser.add_argument(
        '--no-sidebar',
        action='store_true',
        help='Hide topbar showing active shreds (can toggle with F2)'
    )

    return parser


def cmd_edit(args):
    """Launch the multi-tab editor."""
    from ..tui.editor import main as editor_main

    editor_main(
        files=args.files,
        project_name=args.project,
        start_audio=args.start_audio
    )


def cmd_repl(args):
    """Launch the interactive REPL."""
    from ..tui.tui import main as tui_main

    # Get project name from args if provided
    project_name = getattr(args, 'project', None)

    tui_main(
        start_audio=args.start_audio,
        smart_enter=not args.no_smart_enter,
        show_sidebar=not args.no_sidebar,
        project_name=project_name,
        files=getattr(args, 'files', [])
    )


def cmd_exec(args):
    """Execute ChucK files from command line."""
    from .executor import execute_files

    execute_files(
        files=args.files,
        srate=args.srate,
        channels=args.channels,
        silent=args.silent,
        duration=args.duration
    )


def cmd_version(args):
    """Show version information."""
    from .. import version
    print(f"pychuck version: 0.1.1")
    print(f"ChucK version: {version()}")


def cmd_info(args):
    """Show ChucK and pychuck info."""
    from .. import ChucK, version
    print(f"pychuck: 0.1.1")
    print(f"ChucK: {version()}")
    print(f"ChucK int size: {ChucK.int_size()} bits")
    print(f"Active VMs: {ChucK.num_vms()}")


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Map commands to handlers
    command_handlers = {
        'edit': cmd_edit,
        'repl': cmd_repl,
        'tui': cmd_repl,  # Backward compatibility
        'exec': cmd_exec,
        'version': cmd_version,
        'info': cmd_info,
    }

    # Execute command
    if args.command in command_handlers:
        command_handlers[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
