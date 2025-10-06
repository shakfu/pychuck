import subprocess
from .. import start_audio, stop_audio, shutdown_audio, audio_info

class CommandExecutor:
    def __init__(self, session):
        self.session = session
        self.chuck = session.chuck

    def execute(self, cmd):
        handler = getattr(self, f'_cmd_{cmd.type}', None)
        if handler:
            return handler(cmd.args)
        else:
            print(f"Unknown command type: {cmd.type}")
            return None

    def _cmd_spork_file(self, args):
        success, shred_ids = self.chuck.compile_file(args['path'])
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, args['path'])
                print(f"✓ sporked {args['path']} -> shred {sid}")
        else:
            print(f"✗ failed to spork {args['path']}")
            # TODO: Add chuck.get_last_error() to get compiler error messages

    def _cmd_spork_code(self, args):
        success, shred_ids = self.chuck.compile_code(args['code'])
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, f"inline:{args['code'][:20]}...")
                print(f"✓ sporked code -> shred {sid}")
        else:
            print("✗ failed to spork code")
            # TODO: Add chuck.get_last_error() to get compiler error messages

    def _cmd_remove_shred(self, args):
        sid = args['id']
        success = self.chuck.remove_shred(sid)
        if success:
            self.session.remove_shred(sid)
            print(f"✓ removed shred {sid}")
        else:
            print(f"✗ failed to remove shred {sid} (not found)")

    def _cmd_remove_all(self, args):
        count = len(self.session.shreds)
        self.chuck.remove_all_shreds()
        self.session.clear_shreds()
        print(f"✓ removed {count} shred(s)")

    def _cmd_replace_shred(self, args):
        try:
            new_id = self.chuck.replace_shred(args['id'], args['code'])
            if new_id > 0:
                self.session.remove_shred(args['id'])
                self.session.add_shred(new_id, f"replaced:{args['code'][:20]}...")
                print(f"✓ replaced shred {args['id']} -> {new_id}")
            else:
                print(f"✗ failed to replace shred {args['id']}")
        except Exception as e:
            print(f"✗ error replacing shred: {e}")

    def _cmd_list_shreds(self, args):
        shreds = self.chuck.get_all_shred_ids()
        if not shreds:
            print("no shreds running")
            return

        print(f"{'ID':<8} {'Name':<40}")
        print("-" * 50)
        for sid in shreds:
            name = self.session.get_shred_name(sid)
            print(f"{sid:<8} {name:<40}")

    def _cmd_shred_info(self, args):
        try:
            info = self.chuck.get_shred_info(args['id'])
            print(f"Shred {info['id']}:")
            print(f"  name: {info['name']}")
            print(f"  running: {info['is_running']}")
            print(f"  done: {info['is_done']}")
        except Exception as e:
            print(f"Error: {e}")

    def _cmd_list_globals(self, args):
        globals_list = self.chuck.get_all_globals()
        if not globals_list:
            print("no globals defined")
            return

        print(f"{'Type':<20} {'Name':<30}")
        print("-" * 52)
        for typ, name in globals_list:
            print(f"{typ:<20} {name:<30}")

    def _cmd_audio_info(self, args):
        info = audio_info()
        print(f"Sample rate: {info['sample_rate']} Hz")
        print(f"Channels out: {info['num_channels_out']}")
        print(f"Channels in: {info['num_channels_in']}")
        print(f"Buffer size: {info['buffer_size']}")

    def _cmd_current_time(self, args):
        print(f"now: {self.chuck.now()}")

    def _cmd_set_global(self, args):
        val = args['value']
        name = args['name']

        if isinstance(val, int):
            self.chuck.set_global_int(name, val)
        elif isinstance(val, float):
            self.chuck.set_global_float(name, val)
        elif isinstance(val, str):
            self.chuck.set_global_string(name, val)
        elif isinstance(val, list):
            if all(isinstance(x, int) for x in val):
                self.chuck.set_global_int_array(name, val)
            elif all(isinstance(x, float) for x in val):
                self.chuck.set_global_float_array(name, val)

        print(f"set {name} = {val}")

    def _cmd_get_global(self, args):
        name = args['name']

        # Try int first (callback prints value)
        found = [False]  # Use list to allow modification in nested function

        def handle_int(v):
            found[0] = True
            print(f"{name} = {v}")

        def handle_float(v):
            found[0] = True
            print(f"{name} = {v}")

        def handle_string(v):
            found[0] = True
            print(f"{name} = \"{v}\"")

        try:
            self.chuck.get_global_int(name, handle_int)
        except:
            try:
                self.chuck.get_global_float(name, handle_float)
            except:
                try:
                    self.chuck.get_global_string(name, handle_string)
                except Exception as e:
                    pass

        if not found[0]:
            print(f"✗ global variable '{name}' not found or wrong type")

    def _cmd_signal_event(self, args):
        self.chuck.signal_global_event(args['name'])
        print(f"signaled event '{args['name']}'")

    def _cmd_broadcast_event(self, args):
        self.chuck.broadcast_global_event(args['name'])
        print(f"broadcast event '{args['name']}'")

    def _cmd_start_audio(self, args):
        try:
            start_audio(self.chuck)
            self.session.audio_running = True
            print("✓ audio started")
        except Exception as e:
            print(f"✗ failed to start audio: {e}")

    def _cmd_stop_audio(self, args):
        try:
            stop_audio()
            self.session.audio_running = False
            print("✓ audio stopped")
        except Exception as e:
            print(f"✗ failed to stop audio: {e}")

    def _cmd_shutdown_audio(self, args):
        try:
            shutdown_audio(500)
            self.session.audio_running = False
            print("✓ audio shutdown")
        except Exception as e:
            print(f"✗ failed to shutdown audio: {e}")

    def _cmd_clear_vm(self, args):
        self.chuck.clear_vm()
        self.session.clear_shreds()
        print("VM cleared")

    def _cmd_reset_id(self, args):
        self.chuck.reset_shred_id()
        print("shred ID reset")

    def _cmd_compile_file(self, args):
        # Compile with count=0 (don't run)
        success, _ = self.chuck.compile_file(args['path'], count=0)
        if success:
            print(f"✓ compiled {args['path']}")
        else:
            print(f"✗ compilation failed for {args['path']}")
            # TODO: Add chuck.get_last_error() to get compiler error messages

    def _cmd_exec_code(self, args):
        success, _ = self.chuck.compile_code(args['code'], immediate=True)
        if success:
            print("✓ executed")
        else:
            print("✗ execution failed")
            # TODO: Add chuck.get_last_error() to get compiler error messages

    def _cmd_shell(self, args):
        subprocess.run(args['cmd'], shell=True)

    def _cmd_open_editor(self, args):
        import tempfile
        import os

        # Get editor from environment or use default
        editor = os.environ.get('EDITOR', 'nano')

        # Create temp file with .ck extension
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ck', delete=False) as f:
            # Write a template
            f.write('// ChucK code - save and exit to spork\n')
            f.write('SinOsc s => dac;\n')
            f.write('440 => s.freq;\n')
            f.write('second => now;\n')
            temp_path = f.name

        try:
            # Open editor
            subprocess.run([editor, temp_path])

            # Read the file
            with open(temp_path, 'r') as f:
                code = f.read()

            # Spork it if not empty/template
            if code.strip() and '// ChucK code' not in code:
                success, shred_ids = self.chuck.compile_code(code)
                if success:
                    for sid in shred_ids:
                        self.session.add_shred(sid, f"editor:{temp_path}")
                        print(f"✓ sporked from editor -> shred {sid}")
                else:
                    print("✗ failed to spork editor code")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    def _cmd_multiline(self, args):
        # Signal to REPL to enter multiline mode
        return 'MULTILINE_MODE'

    def _cmd_watch(self, args):
        """Monitor VM state continuously"""
        import time
        print("Watching VM state (Ctrl+C to stop)...")
        print()
        try:
            while True:
                shred_count = len(self.chuck.get_all_shred_ids())
                now = self.chuck.now()
                audio = "ON" if self.session.audio_running else "OFF"
                print(f"\rAudio: {audio:<3} | Now: {now:>10.2f} | Shreds: {shred_count:<3}", end='', flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n")

    def _cmd_load_snippet(self, args):
        """Load and spork a code snippet from ~/.chuck_snippets/"""
        import os
        from pathlib import Path

        name = args['name']
        snippets_dir = Path.home() / '.chuck_snippets'
        snippet_path = snippets_dir / f'{name}.ck'

        if not snippet_path.exists():
            # Try to create snippets directory if it doesn't exist
            if not snippets_dir.exists():
                try:
                    snippets_dir.mkdir(parents=True)
                    print(f"Created snippets directory: {snippets_dir}")
                    print(f"Add .ck files to this directory to use @<name> syntax")
                except Exception as e:
                    print(f"✗ could not create snippets directory: {e}")
                    return

            print(f"✗ snippet '{name}' not found at {snippet_path}")
            print(f"Available snippets in {snippets_dir}:")
            if snippets_dir.exists():
                snippets = sorted(snippets_dir.glob('*.ck'))
                if snippets:
                    for s in snippets:
                        print(f"  @{s.stem}")
                else:
                    print("  (none)")
            return

        # Spork the snippet
        success, shred_ids = self.chuck.compile_file(str(snippet_path))
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, f"@{name}")
                print(f"✓ sporked snippet @{name} -> shred {sid}")
        else:
            print(f"✗ failed to spork snippet @{name}")
            # TODO: Add chuck.get_last_error() to get compiler error messages
