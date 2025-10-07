#!/usr/bin/env python3
"""
TUI subcommand - launches vanilla REPL
"""
import sys

def main(start_audio=False, smart_enter=True, show_sidebar=True):
    """
    Launch vanilla TUI REPL

    Args:
        start_audio: If True, start audio automatically on startup
        smart_enter: If True, enable smart Enter mode (default)
        show_sidebar: If True, show sidebar with active shreds (default)
    """
    from .repl import ChuckREPL
    repl = ChuckREPL(smart_enter=smart_enter, show_sidebar=show_sidebar)
    repl.run(start_audio=start_audio)

if __name__ == '__main__':
    main()
