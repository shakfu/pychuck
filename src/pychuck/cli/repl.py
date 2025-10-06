import sys
import os
from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS
)
from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor

class ChuckREPL:
    def __init__(self):
        self.chuck = ChucK()
        self.session = REPLSession(self.chuck)
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session)

        # Only use prompt_toolkit if available
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import FileHistory
            from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
            from prompt_toolkit.completion import PathCompleter, merge_completers, WordCompleter, Completer, Completion
            from prompt_toolkit.key_binding import KeyBindings
            from prompt_toolkit.lexers import PygmentsLexer
            from prompt_toolkit.styles import Style
            from prompt_toolkit.document import Document
            from pygments.lexers.c_cpp import CLexer

            # Context-aware completer
            class ChuckCompleter(Completer):
                def __init__(self, repl_instance):
                    self.repl = repl_instance
                    self.path_completer = PathCompleter(
                        file_filter=lambda filename: filename.endswith('.ck') or os.path.isdir(filename),
                        expanduser=True
                    )
                    self.commands = [
                        '+', '-', '~', '?', '?g', '?a',
                        'clear', 'reset', '>', '||', 'X', '.',
                        'all', '$', ':', '!', 'help', 'quit', 'exit', 'edit', 'ml', 'watch'
                    ]

                def get_completions(self, document, complete_event):
                    text = document.text.strip()

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

                    # Default: suggest commands
                    else:
                        for cmd in self.commands:
                            if cmd.startswith(text):
                                yield Completion(cmd, start_position=-len(text))

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

            # Custom style for syntax highlighting
            repl_style = Style.from_dict({
                'bottom-toolbar': '#ffffff bg:#333333',
            })

            # Key bindings for enhanced history search
            kb = KeyBindings()

            @kb.add('c-s')
            def _(event):
                """Forward history search with Ctrl+S"""
                event.current_buffer.history_forward()

            self.prompt_session = PromptSession(
                history=FileHistory('.chuck_repl_history'),
                auto_suggest=AutoSuggestFromHistory(),
                completer=chuck_completer,
                lexer=PygmentsLexer(CLexer),  # Syntax highlighting (C-like for ChucK)
                multiline=False,
                complete_while_typing=False,  # Only complete on Tab
                enable_history_search=True,
                bottom_toolbar=get_toolbar,
                style=repl_style,
                key_bindings=kb,
            )
            self.use_prompt_toolkit = True
        except ImportError:
            self.use_prompt_toolkit = False
            # Fall back to readline for basic history support
            try:
                import readline
                import glob
                self.use_readline = True

                # Detect if using libedit (macOS default) vs GNU readline
                is_libedit = 'libedit' in readline.__doc__ if readline.__doc__ else False

                # Disable bell
                try:
                    readline.parse_and_bind('set bell-style none')
                except:
                    pass  # May not be supported on all platforms

                # Set up history file
                histfile = os.path.expanduser('~/.chuck_repl_history')
                try:
                    readline.read_history_file(histfile)
                    # Default history length
                    readline.set_history_length(1000)
                except FileNotFoundError:
                    pass

                # Save history on exit
                import atexit
                atexit.register(readline.write_history_file, histfile)

                # Set up tab completion with readline
                def chuck_completer(text, state):
                    """Tab completion for ChucK commands and .ck files"""
                    # Commands
                    commands = ['+', '-', '~', '?', '?g', '?a',
                               'clear', 'reset', '>', '||', 'X', '.',
                               'all', '$', ':', '!', 'help', 'quit', 'exit']

                    # Get matches from commands
                    matches = [cmd for cmd in commands if cmd.startswith(text)]

                    # Also try file completion for .ck files
                    if '/' in text or '.' in text or text == '':
                        # Expand ~ and environment variables
                        expanded = os.path.expanduser(text)

                        # Add glob patterns
                        file_matches = []
                        try:
                            # Match files
                            file_matches = glob.glob(expanded + '*')
                            # Filter for .ck files or directories
                            file_matches = [f for f in file_matches
                                          if f.endswith('.ck') or os.path.isdir(f)]
                            # Add trailing slash to directories
                            file_matches = [f + '/' if os.path.isdir(f) else f
                                          for f in file_matches]
                        except:
                            pass

                        matches.extend(file_matches)

                    try:
                        return matches[state]
                    except IndexError:
                        return None

                readline.set_completer(chuck_completer)

                # Configure tab completion based on readline implementation
                if is_libedit:
                    # macOS libedit syntax
                    readline.parse_and_bind('bind ^I rl_complete')
                else:
                    # GNU readline syntax
                    readline.parse_and_bind('tab: complete')

                # Enable filename completion characters
                # Set delimiters so that paths and commands are completed properly
                readline.set_completer_delims(' \t\n;')

            except ImportError:
                self.use_readline = False

    def setup(self):
        """Initialize ChucK with sensible defaults"""
        self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.chuck.init()

        # Capture ChucK output
        self.chuck.set_chout_callback(lambda msg: print(f"[chout] {msg}", end=''))
        self.chuck.set_cherr_callback(lambda msg: print(f"[cherr] {msg}", end='', file=sys.stderr))

    def run(self):
        """Main REPL loop"""
        try:
            self.setup()

            # Disable terminal mouse tracking and other escape sequences
            # that might be left over from previous programs
            sys.stdout.write('\033[?1000l')  # Disable mouse tracking
            sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
            sys.stdout.write('\033[?1006l')  # Disable SGR mouse mode
            sys.stdout.flush()

            mode = "prompt-toolkit" if self.use_prompt_toolkit else ("readline" if hasattr(self, 'use_readline') and self.use_readline else "basic")
            print(f"ChucK REPL v0.1.0 (vanilla mode - {mode})")
            print("Type 'help' for commands, 'quit' to exit\n")

            while True:
                try:
                    if self.use_prompt_toolkit:
                        text = self.prompt_session.prompt('chuck> ')
                    else:
                        text = input('chuck> ')

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
                        result = self.executor.execute(cmd)
                        # Check if we should enter multiline mode
                        if result == 'MULTILINE_MODE':
                            self._multiline_mode()

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

    def _multiline_mode(self):
        """Enter multiline input mode"""
        print("Entering multiline mode. Type 'END' on a line by itself to finish.")
        lines = []

        while True:
            try:
                if self.use_prompt_toolkit:
                    line = self.prompt_session.prompt('...   ')
                else:
                    line = input('...   ')

                if line.strip() == 'END':
                    break

                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                print("\nMultiline input cancelled")
                return

        code = '\n'.join(lines)
        if code.strip():
            success, shred_ids = self.chuck.compile_code(code)
            if success:
                for sid in shred_ids:
                    self.session.add_shred(sid, f"multiline:{code[:20]}...")
                    print(f"✓ sporked multiline code -> shred {sid}")
            else:
                print("✗ failed to spork multiline code")

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

Other:
  : <file>              Compile only
  ! "<code>"            Execute immediately
  $ <cmd>               Shell command
  edit                  Open $EDITOR for code
  ml                    Enter multiline mode
  watch                 Monitor VM state
  @<name>               Load snippet from ~/.chuck_snippets/
  help                  Show this help
  quit                  Exit

Keyboard Shortcuts:
  Ctrl+R                Reverse history search
  Ctrl+S                Forward history search
  Ctrl+C                Cancel/interrupt
  Tab                   Auto-complete
""")
