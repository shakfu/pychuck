import subprocess
from .. import start_audio, stop_audio, shutdown_audio, audio_info

class CommandExecutor:
    def __init__(self, session):
        self.session = session
        self.chuck = session.chuck

    def execute(self, cmd):
        handler = getattr(self, f'_cmd_{cmd.type}', None)
        if handler:
            handler(cmd.args)
        else:
            print(f"Unknown command type: {cmd.type}")

    def _cmd_spork_file(self, args):
        success, shred_ids = self.chuck.compile_file(args['path'])
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, args['path'])
                print(f"sporked {args['path']} -> shred {sid}")
        else:
            print(f"failed to spork {args['path']}")

    def _cmd_spork_code(self, args):
        success, shred_ids = self.chuck.compile_code(args['code'])
        if success:
            for sid in shred_ids:
                self.session.add_shred(sid, f"inline:{args['code'][:20]}...")
                print(f"sporked code -> shred {sid}")
        else:
            print("failed to spork code")

    def _cmd_remove_shred(self, args):
        sid = args['id']
        self.chuck.remove_shred(sid)
        self.session.remove_shred(sid)
        print(f"removed shred {sid}")

    def _cmd_remove_all(self, args):
        self.chuck.remove_all_shreds()
        self.session.clear_shreds()
        print("removed all shreds")

    def _cmd_replace_shred(self, args):
        new_id = self.chuck.replace_shred(args['id'], args['code'])
        self.session.remove_shred(args['id'])
        self.session.add_shred(new_id, f"replaced:{args['code'][:20]}...")
        print(f"replaced shred {args['id']} -> {new_id}")

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
        try:
            self.chuck.get_global_int(name, lambda v: print(f"{name} = {v}"))
        except:
            try:
                self.chuck.get_global_float(name, lambda v: print(f"{name} = {v}"))
            except:
                try:
                    self.chuck.get_global_string(name, lambda v: print(f"{name} = \"{v}\""))
                except Exception as e:
                    print(f"Error: {e}")

    def _cmd_signal_event(self, args):
        self.chuck.signal_global_event(args['name'])
        print(f"signaled event '{args['name']}'")

    def _cmd_broadcast_event(self, args):
        self.chuck.broadcast_global_event(args['name'])
        print(f"broadcast event '{args['name']}'")

    def _cmd_start_audio(self, args):
        start_audio(self.chuck)
        self.session.audio_running = True
        print("audio started")

    def _cmd_stop_audio(self, args):
        stop_audio()
        self.session.audio_running = False
        print("audio stopped")

    def _cmd_shutdown_audio(self, args):
        shutdown_audio(500)
        self.session.audio_running = False
        print("audio shutdown")

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
            print(f"compiled {args['path']}")
        else:
            print(f"compilation failed")

    def _cmd_exec_code(self, args):
        success, _ = self.chuck.compile_code(args['code'], immediate=True)
        if success:
            print("executed")
        else:
            print("execution failed")

    def _cmd_shell(self, args):
        subprocess.run(args['cmd'], shell=True)
