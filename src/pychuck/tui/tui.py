#!/usr/bin/env python3
"""
TUI subcommand - launches vanilla REPL
"""
import sys

def main(start_audio=False, smart_enter=True, show_sidebar=True, project_name=None, files=None):
    """
    Launch vanilla TUI REPL

    Args:
        start_audio: If True, start audio automatically on startup
        smart_enter: If True, enable smart Enter mode (default)
        show_sidebar: If True, show sidebar with active shreds (default)
        project_name: Optional project name for versioned file storage
        files: Optional list of ChucK files to load on startup
    """
    from .repl import ChuckREPL
    repl = ChuckREPL(smart_enter=smart_enter, show_sidebar=show_sidebar, project_name=project_name)
    repl.run(start_audio=start_audio, files=files or [])

if __name__ == '__main__':
    main()
