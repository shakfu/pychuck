#!/usr/bin/env python3
"""
numchuck command-line interface

Usage:
    python -m numchuck edit [files...]        # Launch multi-tab editor
    python -m numchuck repl [files...]        # Launch interactive REPL
    python -m numchuck exec <files...>        # Execute ChucK files
    python -m numchuck version                # Show version
    python -m numchuck info                   # Show ChucK info

For detailed help on each command:
    python -m numchuck <command> --help
"""


def main() -> None:
    from .cli.main import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
