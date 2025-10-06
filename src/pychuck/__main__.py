#!/usr/bin/env python3
"""
pychuck command-line interface

Usage:
    python -m pychuck tui [--rich]     # Launch TUI REPL
    python -m pychuck version          # Show version
    python -m pychuck info             # Show ChucK info
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
    tui_parser.add_argument(
        '--rich',
        action='store_true',
        help='Use rich TUI interface (requires textual)'
    )
    tui_parser.add_argument(
        '--simple',
        action='store_true',
        help='Use simplified TUI (for debugging, requires textual)'
    )
    tui_parser.add_argument(
        '--basic',
        action='store_true',
        help='Use basic TUI (no colors, for terminals with issues, requires textual)'
    )

    # version subcommand
    version_parser = subparsers.add_parser('version', help='Show version information')

    # info subcommand
    info_parser = subparsers.add_parser('info', help='Show ChucK and pychuck info')

    args = parser.parse_args()

    if args.command == 'tui':
        from .cli.tui import main as tui_main
        tui_main(use_rich=args.rich, use_simple=args.simple, use_basic=args.basic)
    elif args.command == 'version':
        from . import version
        print(f"pychuck version: 0.1.0")
        print(f"ChucK version: {version()}")
    elif args.command == 'info':
        from . import ChucK, version
        print(f"pychuck: 0.1.0")
        print(f"ChucK: {version()}")
        print(f"ChucK int size: {ChucK.int_size()} bits")
        print(f"Active VMs: {ChucK.num_vms()}")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
