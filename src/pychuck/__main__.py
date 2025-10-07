#!/usr/bin/env python3
"""
pychuck command-line interface

Usage:
    python -m pychuck edit [files...]        # Launch multi-tab editor
    python -m pychuck repl [files...]        # Launch interactive REPL
    python -m pychuck exec <files...>        # Execute ChucK files
    python -m pychuck version                # Show version
    python -m pychuck info                   # Show ChucK info

For detailed help on each command:
    python -m pychuck <command> --help
"""

def main():
    from .cli.main import main as cli_main
    cli_main()

if __name__ == '__main__':
    main()
