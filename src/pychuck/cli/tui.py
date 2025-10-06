#!/usr/bin/env python3
"""
TUI subcommand - launches vanilla REPL
"""
import sys

def main(start_audio=False, smart_enter=True):
    """
    Launch vanilla TUI REPL

    Args:
        start_audio: If True, start audio automatically on startup
        smart_enter: If True, enable smart Enter mode (default)
    """
    from .repl import ChuckREPL
    repl = ChuckREPL(smart_enter=smart_enter)
    repl.run(start_audio=start_audio)

if __name__ == '__main__':
    main()
