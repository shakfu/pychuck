import sys
import os
from .. import (
    ChucK, start_audio, stop_audio, shutdown_audio,
    PARAM_SAMPLE_RATE, PARAM_OUTPUT_CHANNELS, PARAM_INPUT_CHANNELS,
    LOG_NONE
)
from ..chuck_lang import REPL_COMMANDS, ALL_IDENTIFIERS
from .parser import CommandParser
from .session import REPLSession
from .commands import CommandExecutor
from .paths import get_history_file, ensure_pychuck_directories

class ChuckREPL:
    def __init__(self, smart_enter=True, show_sidebar=True, project_name=None):
        self.chuck = ChucK()
        self.session = REPLSession(self.chuck, project_name=project_name)
        self.parser = CommandParser()
        self.executor = CommandExecutor(self.session)
        self.smart_enter = smart_enter  # Enable smart Enter behavior
        self.show_sidebar = show_sidebar  # Show/hide sidebar

        # Import prompt_toolkit (now a required dependency)
        from prompt_toolkit import Application
        from prompt_toolkit.buffer import Buffer
        from prompt_toolkit.history import FileHistory
        from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
        from prompt_toolkit.completion import PathCompleter, merge_completers, WordCompleter, Completer, Completion
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.lexers import PygmentsLexer
        from prompt_toolkit.styles import Style
        from prompt_toolkit.document import Document
        from prompt_toolkit.formatted_text import HTML, ANSI
        from prompt_toolkit.layout.containers import HSplit, VSplit, Window, ConditionalContainer
        from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
        from prompt_toolkit.layout.layout import Layout
        from prompt_toolkit.layout.dimension import Dimension as D
        from prompt_toolkit.layout.margins import ScrollbarMargin
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.shortcuts import message_dialog
        from prompt_toolkit.widgets import TextArea

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

        # Error message state
        self.error_message = ""

        # Help window visibility
        self.show_help_window = False

        # Shreds table window visibility
        self.show_shreds_window = False

        # Log window visibility and buffer
        self.show_log_window = False
        self.log_lines = []
        self.max_log_lines = 100  # Keep last 100 messages

        # Create topbar content function (simplified to show just IDs)
        def get_topbar_text():
            """Generate topbar content showing active shred IDs"""
            if self.session.shreds:
                shred_ids = " ".join(f"[{sid}]" for sid in sorted(self.session.shreds.keys()))
                return f"Shreds: {shred_ids}  (F2: table)"
            else:
                return "No active shreds  (F2: table)"

        # Create error bar function
        def get_error_text():
            """Show error message if any"""
            if self.error_message:
                return f"✗ {self.error_message}"
            return ""

        # Create help text content
        help_text = """\
SHRED MANAGEMENT                        STATUS & INFO
  + <file.ck>    Spork file               ?         List shreds
  + "<code>"     Spork code               ? <id>    Shred info
  - <id>         Remove shred             ?g        List globals
  - all          Remove all               ?a        Audio info
  edit <id>      Edit shred               .         Current time

GLOBALS                                 EVENTS
  <name>::<val>  Set global               <ev>!     Signal event
  <name>?        Get global               <ev>!!    Broadcast event

AUDIO CONTROL                           VM CONTROL
  >              Start audio              clear     Clear VM
  ||             Stop audio               reset     Reset shred ID
  X              Shutdown                 cls       Clear screen

OTHER COMMANDS                          KEYBOARD SHORTCUTS
  : <file>       Compile only             F1        Toggle help
  $ <cmd>        Shell cmd                F2        Shreds table
  edit           Open editor              F3        Toggle log
  @<name>        Load snippet             Ctrl+Q    Exit REPL
                                          Ctrl+R    History search
                                          Esc+Enter Submit code
                                          Tab       Auto-complete"""

        # Create help TextArea (non-scrollable, fits exactly)
        self.help_area = TextArea(
            text=help_text,
            read_only=True,
            scrollbar=False,
            focusable=False,
            height=D.exact(20),  # Exact height to fit help text
            style='class:help-area'
        )

        # Create log TextArea (scrollable, for VM messages)
        self.log_area = TextArea(
            text="",
            read_only=True,
            scrollbar=True,
            focusable=False,
            height=D(min=0, max=30),  # Scrollable log area
            style='class:log-area'
        )

        # Create shreds table function
        def get_shreds_table():
            """Generate formatted table of active shreds"""
            if not self.session.shreds:
                return "No active shreds"

            lines = []
            lines.append("ID    Name                                                    Elapsed")
            lines.append("─" * 78)

            # Get current VM time for elapsed calculation
            try:
                current_time = self.chuck.now()
            except:
                current_time = 0.0

            for shred_id, info in sorted(self.session.shreds.items()):
                # Extract parent folder + filename from path
                from pathlib import Path
                full_name = info['name']
                try:
                    path = Path(full_name)
                    # Show parent/filename if it's a path, otherwise just the name
                    if path.parent.name:
                        name = f"{path.parent.name}/{path.name}"
                    else:
                        name = path.name
                except:
                    name = full_name
                name = name[:56]  # Wider column for better readability

                # Calculate elapsed time in seconds
                spork_time = info.get('time', 0.0)
                elapsed_samples = current_time - spork_time
                # Get sample rate from ChucK (default 44100)
                try:
                    sample_rate = self.chuck.get_param_int(PARAM_SAMPLE_RATE)
                except:
                    sample_rate = 44100
                elapsed_sec = elapsed_samples / sample_rate if sample_rate > 0 else 0.0

                # Format time display
                if elapsed_sec < 60:
                    time_str = f"{elapsed_sec:.1f}s"
                elif elapsed_sec < 3600:
                    mins = int(elapsed_sec / 60)
                    secs = elapsed_sec % 60
                    time_str = f"{mins}m{secs:04.1f}s"
                else:
                    hours = int(elapsed_sec / 3600)
                    mins = int((elapsed_sec % 3600) / 60)
                    time_str = f"{hours}h{mins:02d}m"

                lines.append(f"{shred_id:<5} {name:<56} {time_str}")

            return "\n".join(lines)

        # Store the shreds table generator function
        self.get_shreds_table = get_shreds_table

        # Create shreds table TextArea (non-scrollable, auto-sized)
        self.shreds_area = TextArea(
            text="",
            read_only=True,
            scrollbar=False,
            focusable=False,
            height=D(min=0, max=20),  # Auto-size up to 20 lines
            style='class:shreds-area'
        )

        # Create bottom toolbar function (shows VM status)
        def get_bottom_toolbar():
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
            'top-toolbar': '#00ffff bg:#000033',  # cyan on dark blue for topbar
            'error-toolbar': '#ffffff bg:#cc0000',  # white on red for errors
            'help-area': '#aaaaaa bg:#222222',     # gray on dark gray for help
            'log-area': '#cccccc bg:#111111',      # lighter gray for log
            'shreds-area': '#00ffff bg:#001133',   # cyan on dark blue for shreds table
            'prompt-bracket': '#ff8800',  # orange for brackets
            'prompt-chuck': '#00ff00',     # green for =>
        })

        # Key bindings for enhanced history search and multiline
        kb = KeyBindings()

        # Topbar visibility condition
        @Condition
        def topbar_visible():
            return self.show_sidebar

        @kb.add('c-s')
        def _(event):
            """Forward history search with Ctrl+S"""
            event.current_buffer.history_forward()

        @kb.add('f2')
        def _(event):
            """Toggle shreds table window with F2"""
            self.show_shreds_window = not self.show_shreds_window
            # Update shreds table content when opening
            if self.show_shreds_window:
                self.shreds_area.text = self.get_shreds_table()
            event.app.invalidate()  # Force redraw

        @kb.add('f1')
        def _(event):
            """Toggle help window with F1"""
            self.show_help_window = not self.show_help_window
            event.app.invalidate()  # Force redraw

        @kb.add('f3')
        def _(event):
            """Toggle log window with F3"""
            self.show_log_window = not self.show_log_window
            event.app.invalidate()  # Force redraw

        @kb.add('c-q')
        def _(event):
            """Exit with Ctrl-Q"""
            event.app.exit()

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

        # Create input buffer
        self.input_buffer = Buffer(
            history=FileHistory(str(get_history_file())),
            auto_suggest=AutoSuggestFromHistory(),
            completer=chuck_completer,
            complete_while_typing=False,
            multiline=should_continue_multiline,
            on_text_insert=lambda _: None,  # Could be used for live updates
        )

        # Create topbar window
        topbar_window = ConditionalContainer(
            Window(
                content=FormattedTextControl(text=get_topbar_text),
                height=D.exact(1),
                style='class:top-toolbar',
            ),
            filter=topbar_visible
        )

        # Create main input window with prompt
        def get_prompt_text():
            prompt_html = HTML('<prompt-bracket>[</prompt-bracket><prompt-chuck>=></prompt-chuck><prompt-bracket>]</prompt-bracket> ')
            return prompt_html

        input_window = Window(
            content=BufferControl(
                buffer=self.input_buffer,
                lexer=PygmentsLexer(lexer_class),
                include_default_input_processors=True,
            ),
            get_line_prefix=lambda line_number, wrap_count: get_continuation(0, line_number, False) if line_number > 0 else get_prompt_text(),
            wrap_lines=True,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )

        # Create error bar window (conditional)
        @Condition
        def error_visible():
            return bool(self.error_message)

        error_window = ConditionalContainer(
            Window(
                height=D.exact(1),
                content=FormattedTextControl(text=get_error_text),
                style='class:error-toolbar'
            ),
            filter=error_visible
        )

        # Create help window (conditional)
        @Condition
        def help_visible():
            return self.show_help_window

        help_window = ConditionalContainer(
            self.help_area,
            filter=help_visible
        )

        # Create shreds table window (conditional)
        @Condition
        def shreds_visible():
            return self.show_shreds_window

        shreds_window = ConditionalContainer(
            self.shreds_area,
            filter=shreds_visible
        )

        # Create log window (conditional)
        @Condition
        def log_visible():
            return self.show_log_window

        log_window = ConditionalContainer(
            self.log_area,
            filter=log_visible
        )

        # Create layout with top toolbar (shreds) and bottom toolbar (status)
        root_container = HSplit([
            topbar_window,  # Top: shows active shreds (IDs only)
            Window(height=D.exact(1)),  # Gap between topbar and input
            input_window,   # Middle: REPL input
            error_window,   # Error bar (only shown when there's an error)
            help_window,    # Help window (toggle with F1)
            shreds_window,  # Shreds table window (toggle with F2)
            log_window,     # Log window (toggle with F3)
            Window(height=D.exact(1), content=FormattedTextControl(text=get_bottom_toolbar), style='class:bottom-toolbar'),  # Bottom: VM status
        ])

        # Create application
        self.app = Application(
            layout=Layout(root_container),
            key_bindings=kb,
            style=repl_style,
            full_screen=True,
            mouse_support=True,  # Enable mouse for scrolling
        )

        self.prompt_html = HTML  # Store HTML class for later use

    def add_to_log(self, msg):
        """Capture ChucK VM messages to log window"""
        msg = msg.rstrip('\n')
        if msg:
            self.log_lines.append(msg)
            # Keep only recent messages
            if len(self.log_lines) > self.max_log_lines:
                self.log_lines.pop(0)
            # Update the log area
            self.log_area.text = '\n'.join(self.log_lines)
            # Scroll to bottom
            self.log_area.buffer.cursor_position = len(self.log_area.text)
            self.app.invalidate()

    def setup(self):
        """Initialize ChucK with sensible defaults"""
        # Use ChucK's stdout callback to capture VM messages (must be set before init)
        ChucK.set_stdout_callback(self.add_to_log)
        ChucK.set_stderr_callback(self.add_to_log)

        self.chuck.set_param(PARAM_SAMPLE_RATE, 44100)
        self.chuck.set_param(PARAM_OUTPUT_CHANNELS, 2)
        self.chuck.set_param(PARAM_INPUT_CHANNELS, 0)
        self.chuck.init()

        # Capture ChucK output (chout/cherr from user code)
        self.chuck.set_chout_callback(lambda msg: self.add_to_log(f"[out] {msg}"))
        self.chuck.set_cherr_callback(lambda msg: self.add_to_log(f"[err] {msg}"))

    def process_input(self, buff):
        """Process input when user presses Enter"""
        text = buff.text.strip()

        # Clear previous error
        self.error_message = ""

        if not text:
            return

        if text in ['quit', 'exit', 'q']:
            self.app.exit()
            return

        if text == 'help':
            self.show_help_window = not self.show_help_window
            self.app.invalidate()
            return

        # Parse and execute
        cmd = self.parser.parse(text)
        if cmd:
            # Only print newline for commands that produce output
            # Silent commands: audio start/stop, shred add/remove
            silent_cmds = ['start_audio', 'stop_audio', 'shutdown_audio', 'spork_file',
                          'spork_code', 'remove_shred', 'remove_all', 'edit_shred']
            if cmd.type not in silent_cmds:
                print()  # newline for output
            # Execute command and get error if any
            error = self.executor.execute(cmd)
            if error:
                self.error_message = error
        else:
            # If not a recognized command, treat as ChucK code
            # Check if it looks like ChucK code (contains =>, ;, or multiline)
            if '\n' in text or '=>' in text or ';' in text or '{' in text:
                # ChucK code compilation is silent, topbar shows result
                success, shred_ids = self.chuck.compile_code(text)
                if success:
                    for sid in shred_ids:
                        self.session.add_shred(sid, f"code-{sid}", content=text, shred_type='code')
                else:
                    self.error_message = "Failed to compile code"
            else:
                # Not a recognized command and doesn't look like ChucK code
                self.error_message = f"Unknown command: {text}"

        # Force redraw to update topbar/toolbar/error
        self.app.invalidate()

    def run(self, start_audio=False, files=None):
        """Main REPL loop

        Args:
            start_audio: If True, start audio automatically on startup
            files: Optional list of ChucK files to load on startup
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

            # Load files if provided
            if files:
                for filepath in files:
                    try:
                        result = self.executor.execute_command(f"+ {filepath}")
                        self.log(result)
                    except Exception as e:
                        self.log(f"Error loading {filepath}: {e}")

            # Disable terminal mouse tracking and other escape sequences
            # that might be left over from previous programs
            sys.stdout.write('\033[?1000l')  # Disable mouse tracking
            sys.stdout.write('\033[?1003l')  # Disable all mouse tracking
            sys.stdout.write('\033[?1006l')  # Disable SGR mouse mode
            sys.stdout.flush()

            # Set accept handler for buffer
            self.input_buffer.accept_handler = self.process_input

            # Run the application
            self.app.run()

        finally:
            self.cleanup()

    def cleanup(self):
        """Shutdown cleanly"""
        print("\nShutting down...")

        # Remove all shreds first
        try:
            self.chuck.remove_all_shreds()
        except Exception as e:
            print(f"Warning: Error removing shreds: {e}", file=sys.stderr)

        # Stop audio properly if running
        if hasattr(self, 'session') and self.session.audio_running:
            try:
                stop_audio()  # Stop audio stream first
            except Exception as e:
                print(f"Warning: Error stopping audio: {e}", file=sys.stderr)

            try:
                shutdown_audio(500)  # Then clean up audio resources
            except Exception as e:
                print(f"Warning: Error shutting down audio: {e}", file=sys.stderr)

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

