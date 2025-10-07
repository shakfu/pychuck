#!/usr/bin/env python3
"""
pychuck command-line interface

Usage:
    python -m pychuck tui                    # Launch TUI REPL
    python -m pychuck tui --start-audio      # Launch REPL with audio started
    python -m pychuck tui --no-smart-enter   # Launch REPL without smart Enter
    python -m pychuck version                # Show version
    python -m pychuck info                   # Show ChucK info
"""
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog='pychuck',
        description='Python bindings for ChucK audio programming language'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # tui subcommand
    tui_parser = subparsers.add_parser('tui', help='Launch interactive REPL')
    tui_parser.add_argument('--start-audio', action='store_true',
                           help='Start audio automatically on REPL startup')
    tui_parser.add_argument('--no-smart-enter', action='store_true',
                           help='Disable smart Enter mode (always require Esc+Enter to submit)')
    tui_parser.add_argument('--no-sidebar', action='store_true',
                           help='Hide topbar showing active shreds (can toggle with F2)')

    # version subcommand
    version_parser = subparsers.add_parser('version', help='Show version information')

    # info subcommand
    info_parser = subparsers.add_parser('info', help='Show ChucK and pychuck info')

    args = parser.parse_args()

    if args.command == 'tui':
        from .cli.tui import main as tui_main
        tui_main(start_audio=args.start_audio,
                smart_enter=not args.no_smart_enter,
                show_sidebar=not args.no_sidebar)
    elif args.command == 'version':
        from . import version
        print(f"pychuck version: 0.1.1")
        print(f"ChucK version: {version()}")
    elif args.command == 'info':
        from . import ChucK, version
        print(f"pychuck: 0.1.1")
        print(f"ChucK: {version()}")
        print(f"ChucK int size: {ChucK.int_size()} bits")
        print(f"Active VMs: {ChucK.num_vms()}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
