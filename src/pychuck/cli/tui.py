#!/usr/bin/env python3
"""
TUI subcommand - launches vanilla REPL
"""
import sys

def main():
    """
    Launch vanilla TUI REPL
    """
    from .repl import ChuckREPL
    repl = ChuckREPL()
    repl.run()

if __name__ == '__main__':
    main()
