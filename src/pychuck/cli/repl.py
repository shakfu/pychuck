import sys
import os
from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
)
from ..chuck_lang import REPL_COMMANDS, ALL_IDENTIFIERS
from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor
from .paths import get_history_file, ensure_pychuck_directories

class ChuckREPL:
    def __init__(self, smart_enter=True):
        self.chuck = ChucK()
        self.session = REPLSession(self.chuck)
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session)
        self.smart_enter = smart_enter  # Enable smart Enter behavior

        # Import prompt_toolkit (now a required dependency)
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.completion import PathCompleter, merge_completers, WordCompleter, Completer, Completion
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.lexers import PygmentsLexer
        from prompt_toolkit.styles import Style
        from prompt_toolkit.document import Document
        from prompt_toolkit.formatted_text import HTML

        # Try to import ChucK lexer, fall back to C lexer
        try:
            from .chuck_lexer import ChuckLexer
            lexer_class = ChuckLexer
        except ImportError:
            from pygments.lexers.c_cpp import CLexer
            lexer_class = CLexer

        # Context-aware completer
        class ChuckCompleter(Completer):
            def __init__(self, repl_instance):
                self.repl = repl_instance
                self.path_completer = PathCompleter(
                    file_filter=lambda filename: filename.endswith('.ck') or os.path.isdir(filename),
                    expanduser=True
                )
                # Use REPL_COMMANDS from chuck_lang as source of truth
                self.commands = sorted(REPL_COMMANDS)

            def get_completions(self, document, complete_event):
                text = document.text.strip()

                # Get the word before cursor for ChucK code completion
                word_before_cursor = document.get_word_before_cursor(WORD=True)

                # After '+', suggest .ck files
                if text.startswith('+ ') and len(text) > 2:
                    # Create new document with just the path part
                    path_text = text[2:].strip()
                    path_doc = Document(path_text, len(path_text))
                    for completion in self.path_completer.get_completions(path_doc, complete_event):
                        yield completion

                # After '-', suggest shred IDs or 'all'
                elif text.startswith('- ') and len(text) > 2:
                    prefix = text[2:].strip()
                    # Suggest 'all'
                    if 'all'.startswith(prefix):
                        yield Completion('all', start_position=-len(prefix))
                    # Suggest active shred IDs
                    try:
                        for sid in self.repl.session.shreds.keys():
                            sid_str = str(sid)
                            if sid_str.startswith(prefix):
                                yield Completion(sid_str, start_position=-len(prefix))
                    except:
                        pass

                # After '~', suggest shred IDs
                elif text.startswith('~ ') and len(text) > 2:
                    parts = text[2:].strip()
                    if ' ' not in parts:  # Still typing shred ID
                        try:
                            for sid in self.repl.session.shreds.keys():
                                sid_str = str(sid)
                                if sid_str.startswith(parts):
                                    yield Completion(sid_str, start_position=-len(parts))
                        except:
                            pass

                # After '? ', suggest shred IDs
                elif text.startswith('? ') and len(text) > 2:
                    prefix = text[2:].strip()
                    try:
                        for sid in self.repl.session.shreds.keys():
                            sid_str = str(sid)
                            if sid_str.startswith(prefix):
                                yield Completion(sid_str, start_position=-len(prefix))
                    except:
                        pass

                # After '<name>?' or '<name>::', suggest known globals
                elif '?' in text and not text.startswith('?'):
                    prefix = text.split('?')[0]
                    try:
                        globals_list = self.repl.chuck.get_all_globals()
                        for typ, name in globals_list:
                            if name.startswith(prefix):
                                yield Completion(name + '?', start_position=-len(text))
                    except:
                        pass

                elif '::' in text:
                    prefix = text.split('::')[0]
                    try:
                        globals_list = self.repl.chuck.get_all_globals()
                        for typ, name in globals_list:
                            if name.startswith(prefix):
                                yield Completion(name + '::', start_position=-len(text))
                    except:
                        pass

                # After ': ', suggest .ck files (compile mode)
                elif text.startswith(': ') and len(text) > 2:
                    path_text = text[2:].strip()
                    path_doc = Document(path_text, len(path_text))
                    for completion in self.path_completer.get_completions(path_doc, complete_event):
                        yield completion

                # Default: suggest REPL commands or ChucK identifiers
                else:
                    # First priority: REPL commands (if text matches command patterns)
                    repl_command_matched = False
                    for cmd in self.commands:
                        if cmd.startswith(text):
                            yield Completion(cmd, start_position=-len(text))
                            repl_command_matched = True

                    # Second priority: ChucK language identifiers (keywords, types, UGens, etc.)
                    # Only suggest ChucK completions if:
                    # 1. No REPL commands matched, OR
                    # 2. We're completing a word within ChucK code (word_before_cursor exists)
                    if not repl_command_matched or word_before_cursor:
                        for identifier in sorted(ALL_IDENTIFIERS):
                            if identifier.startswith(word_before_cursor):
                                yield Completion(
                                    identifier,
                                    start_position=-len(word_before_cursor),
                                    display_meta='ChucK'
                                )

        chuck_completer = ChuckCompleter(self)

        # Create status toolbar function
        def get_toolbar():
            try:
                audio_status = "ON" if self.session.audio_running else "OFF"
                now = self.chuck.now()
                shred_count = len(self.session.shreds)
                return f"Audio: {audio_status} | Now: {now:.2f} | Shreds: {shred_count}"
            except:
                return "Audio: -- | Now: -- | Shreds: --"

        # Custom style for syntax highlighting and prompt
        repl_style = Style.from_dict({
            'bottom-toolbar': '#ffffff bg:#333333',
            'prompt-bracket': '#ff8800',  # orange for brackets
            'prompt-chuck': '#00ff00',     # green for =>
        })

        # Key bindings for enhanced history search and multiline
        kb = KeyBindings()

        @kb.add('c-s')
        def _(event):
            """Forward history search with Ctrl+S"""
            event.current_buffer.history_forward()

        # Ensure pychuck directories exist
        ensure_pychuck_directories()

        # Prompt continuation for multiline input
        def get_continuation(width, line_number, is_soft_wrap):
            return '... ' if line_number > 0 else ''

        # Smart multiline filter - determines if we should stay in multiline mode
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.application import get_app

        @Condition
        def should_continue_multiline():
            if not self.smart_enter:
                return True  # Always multiline, require Esc+Enter/Ctrl+Enter

            # Get current buffer text
            app = get_app()
            text = app.current_buffer.text

            # If there's already a newline, we're in multiline mode
            if '\n' in text:
                return True

            # Single line - check if it's a REPL command
            text_stripped = text.strip()
            if not text_stripped:
                return False

            # Known single-line commands should submit on Enter
            single_line_cmds = [
                'quit', 'exit', 'q', 'help', 'clear', 'reset', 'cls',
                'watch', '?', '?g', '?a', '.', '>', '||', 'X'
            ]
            if text_stripped in single_line_cmds:
                return False  # Don't continue, accept on Enter

            # Patterns that start REPL commands
            if text_stripped.startswith(('+', '-', '~', '?', ':', '!', '$', '@', 'edit')):
                return False  # REPL command, accept on Enter

            # If it contains ChucK code markers, stay multiline
            if any(marker in text_stripped for marker in ['=>', ';', '{']):
                return True  # Likely ChucK code, require Esc+Enter

            # Default: single-line input without ChucK markers, accept on Enter
            return False

        self.prompt_session = PromptSession(
            history=FileHistory(str(get_history_file())),
            auto_suggest=AutoSuggestFromHistory(),
            completer=chuck_completer,
            lexer=PygmentsLexer(lexer_class),  # Syntax highlighting (ChucK or C-like)
            multiline=should_continue_multiline,  # Dynamic multiline based on content
            prompt_continuation=get_continuation,  # Show ... for continuation lines
            complete_while_typing=False,  # Only complete on Tab
            enable_history_search=True,
            bottom_toolbar=get_toolbar,
            style=repl_style,
            key_bindings=kb,
        )
        self.prompt_html = HTML  # Store HTML class for later use

    def setup(self):
        """Initialize ChucK with sensible defaults"""
        self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.chuck.init()

        # Capture ChucK output
        self.chuck.set_chout_callback(lambda msg: print(f"[chout] {msg}", end=''))
        self.chuck.set_cherr_callback(lambda msg: print(f"[cherr] {msg}", end='', file=sys.stderr))

    def run(self, start_audio=False):
        """Main REPL loop

        Args:
            start_audio: If True, start audio automatically on startup
        """
        try:
            self.setup()

            # Start audio if requested
            if start_audio:
                from .. import start_audio as start_audio_func
                try:
                    start_audio_func(self.chuck)
                    self.session.audio_running = True
                except Exception as e:
                    print(f"Warning: Could not start audio: {e}", file=sys.stderr)

            # Clear screen
            sys.stdout.write('\033[2J\033[H')  # Clear screen and move cursor to home
            sys.stdout.flush()

            # Disable terminal mouse tracking and other escape sequences
            # that might be left over from previous programs
            sys.stdout.write('\033[?1000l')  # Disable mouse tracking
            sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
            sys.stdout.write('\033[?1006l')  # Disable SGR mouse mode
            sys.stdout.flush()

            audio_status = " (audio started)" if start_audio and self.session.audio_running else ""
            print(f"PyChucK REPL v0.1.1{audio_status}")
            print("Type 'help' for commands, 'quit' to exit\n")

            while True:
                try:
                    # Use HTML-like formatting with custom styles for prompt
                    prompt_html = self.prompt_html('<prompt-bracket>[</prompt-bracket><prompt-chuck>=></prompt-chuck><prompt-bracket>]</prompt-bracket> ')
                    text = self.prompt_session.prompt(prompt_html)

                    text = text.strip()

                    if not text:
                        continue

                    if text in ['quit', 'exit', 'q']:
                        break

                    if text == 'help':
                        self.print_help()
                        continue

                    # Parse and execute
                    cmd = self.parser.parse(text)
                    if cmd:
                        self.executor.execute(cmd)
                    else:
                        # If not a recognized command, treat as ChucK code
                        # Check if it looks like ChucK code (contains =>, ;, or multiline)
                        if '\n' in text or '=>' in text or ';' in text or '{' in text:
                            success, shred_ids = self.chuck.compile_code(text)
                            if success:
                                for sid in shred_ids:
                                    self.session.add_shred(sid, f"code:{text[:20]}...")
                                    print(f"✓ sporked code -> shred {sid}")
                            else:
                                print("✗ failed to compile code")

                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
        finally:
            self.cleanup()

    def cleanup(self):
        """Shutdown cleanly"""
        print("\nShutting down...")
        try:
            shutdown_audio(500)
        except:
            pass  # Audio might not be running
        try:
            self.chuck.remove_all_shreds()
        except:
            pass
        # Break circular references to allow proper garbage collection
        if hasattr(self, 'session'):
            self.session.chuck = None
            del self.session
        if hasattr(self, 'executor'):
            self.executor.chuck = None
            self.executor.session = None
            del self.executor
        if hasattr(self, 'chuck'):
            del self.chuck

    def print_help(self):
        print("""
ChucK REPL Commands:

Shred Management:
  + <file.ck>           Spork file
  + "<code>"            Spork code
  - <id>                Remove shred
  - all                 Remove all shreds
  ~ <id> "<code>"       Replace shred

Status:
  ?                     List shreds
  ? <id>                Show shred info
  ?g                    List globals
  ?a                    Audio info
  .                     Current time

Globals:
  <name>::<value>       Set global
  <name>?               Get global (async)

Events:
  <event>!              Signal event
  <event>!!             Broadcast event

Audio:
  >                     Start audio
  ||                    Stop audio
  X                     Shutdown audio

VM:
  clear                 Clear VM
  reset                 Reset shred ID

Screen:
  cls                   Clear screen

Other:
  : <file>              Compile only
  ! "<code>"            Execute immediately
  $ <cmd>               Shell command
  edit                  Open $EDITOR for code
  watch                 Monitor VM state
  @<name>               Load snippet from ~/.pychuck/snippets/
  help                  Show this help
  quit                  Exit

Multiline Input (Smart Enter Mode):
  Enter on REPL commands    Submit immediately (quit, help, +, -, etc.)
  Enter on ChucK code       Insert newline (continue editing)
  Esc+Enter                 Submit code (always works)

Keyboard Shortcuts:
  Ctrl+R                Reverse history search
  Ctrl+S                Forward history search
  Ctrl+C                Cancel/interrupt
  Tab                   Auto-complete (REPL commands, file paths, ChucK code)

CLI Options:
  --start-audio         Start audio automatically on REPL startup
  --no-smart-enter      Disable smart Enter mode (always require Esc+Enter)
""")
