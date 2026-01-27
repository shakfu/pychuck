#!/usr/bin/env python3
"""
TUI subcommand - launches vanilla REPL

Supports both interactive mode (TTY) and non-interactive mode (piped input):
    numchuck repl                    # Interactive full-screen REPL
    echo '+ test.ck' | numchuck repl # Piped input mode
    numchuck repl < commands.txt     # Redirected input mode
    numchuck repl --stdin            # Force stdin mode (for testing)
"""

import sys


def main(
    start_audio=False,
    smart_enter=True,
    show_sidebar=True,
    project_name=None,
    files=None,
    force_stdin=False,
):
    """
    Launch vanilla TUI REPL

    Args:
        start_audio: If True, start audio automatically on startup
        smart_enter: If True, enable smart Enter mode (default)
        show_sidebar: If True, show sidebar with active shreds (default)
        project_name: Optional project name for versioned file storage
        files: Optional list of ChucK files to load on startup
        force_stdin: If True, force stdin mode even if TTY is available
    """
    # Detect if stdin is a TTY (interactive) or piped/redirected
    # Use stdin mode if forced or if stdin is not a TTY
    use_stdin_mode = force_stdin or not sys.stdin.isatty()

    if not use_stdin_mode:
        # Interactive mode - use full-screen REPL
        from .repl import ChuckREPL

        repl = ChuckREPL(
            smart_enter=smart_enter,
            show_sidebar=show_sidebar,
            project_name=project_name,
        )
        repl.run(start_audio=start_audio, files=files or [])
    else:
        # Non-interactive mode - read from stdin
        from .repl import ChuckREPLStdin

        repl = ChuckREPLStdin(project_name=project_name)
        exit_code = repl.run(start_audio=start_audio, files=files or [])
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
