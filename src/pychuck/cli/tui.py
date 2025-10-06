#!/usr/bin/env python3
"""
TUI subcommand - launches REPL with optional rich interface
"""
import sys

def main(use_rich=False, use_simple=False, use_basic=False):
    """
    Launch TUI REPL

    Args:
        use_rich: If True, use textual rich TUI. If False, use vanilla REPL.
        use_simple: If True, use simplified textual TUI (for debugging).
        use_basic: If True, use basic textual TUI (no colors).
    """

    if use_basic:
        # Basic TUI - no colors, for terminals with escape sequence issues
        try:
            from .tui_basic import ChuckBasicTUI
        except ImportError as e:
            print("Error: Basic TUI requires 'textual' package.", file=sys.stderr)
            print("Install with: pip install pychuck[tui]", file=sys.stderr)
            print(f"\nDetails: {e}", file=sys.stderr)
            sys.exit(1)

        app = ChuckBasicTUI()
        app.run(mouse=False)
    elif use_simple:
        # Simplified TUI for debugging
        try:
            from .tui_simple import ChuckSimpleTUI
        except ImportError as e:
            print("Error: Simple TUI requires 'textual' package.", file=sys.stderr)
            print("Install with: pip install pychuck[tui]", file=sys.stderr)
            print(f"\nDetails: {e}", file=sys.stderr)
            sys.exit(1)

        app = ChuckSimpleTUI()
        app.run(mouse=False)
    elif use_rich:
        # User explicitly requested rich TUI - fail if not available
        try:
            print("DEBUG: importing ChuckTUI", file=sys.stderr)
            from .tui_rich import ChuckTUI
            print("DEBUG: ChuckTUI imported successfully", file=sys.stderr)
        except ImportError as e:
            print("Error: Rich TUI requires 'textual' package.", file=sys.stderr)
            print("Install with: pip install pychuck[tui]", file=sys.stderr)
            print(f"\nDetails: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"ERROR during import: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)

        try:
            print("DEBUG: Creating ChuckTUI instance", file=sys.stderr)
            app = ChuckTUI()
            print("DEBUG: Running app with mouse=False", file=sys.stderr)
            app.run(mouse=False)
            print("DEBUG: App exited normally", file=sys.stderr)
        except Exception as e:
            print(f"ERROR during app run: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        # Use vanilla REPL by default
        from .repl import ChuckREPL
        repl = ChuckREPL()
        repl.run()

if __name__ == '__main__':
    main()
