import re
from dataclasses import dataclass
from typing import Optional, Union, List

@dataclass
class Command:
    type: str
    args: dict

class CommandParser:
    def __init__(self):
        self.patterns = [
            # Chuck-style word commands (new)
            (r'^add\s+(.+\.ck)$', self._spork_file),
            (r'^remove\s+all$', self._remove_all),
            (r'^remove\s+(\d+)$', self._remove_shred),
            (r'^replace\s+(\d+)\s+(.+\.ck)$', self._replace_shred_file),
            (r'^status$', self._status),
            (r'^time$', self._current_time),

            # Shred management (shortcut symbols)
            (r'^\+\s+(.+\.ck)$', self._spork_file),
            (r'^\+\s+"([^"]+)"$', self._spork_code),
            (r'^\+\s+\'([^\']+)\'$', self._spork_code),
            (r'^-\s+all$', self._remove_all),
            (r'^-\s*(\d+)$', self._remove_shred),  # Accept "- 1" or "-1"
            (r'^~\s+(\d+)\s+"([^"]+)"$', self._replace_shred),

            # Status
            (r'^\?$', self._list_shreds),
            (r'^\?\s+(\d+)$', self._shred_info),
            (r'^\?g$', self._list_globals),
            (r'^\?a$', self._audio_info),
            (r'^\.$', self._current_time),

            # Globals
            (r'^(\w+)::(.+)$', self._set_global),
            (r'^(\w+)\?$', self._get_global),

            # Events
            (r'^(\w+)!!$', self._broadcast_event),
            (r'^(\w+)!$', self._signal_event),

            # Audio
            (r'^>$', self._start_audio),
            (r'^\|\|$', self._stop_audio),
            (r'^X$', self._shutdown_audio),

            # VM
            (r'^clear$', self._clear_vm),
            (r'^reset$', self._reset_id),

            # Screen
            (r'^cls$', self._clear_screen),

            # Other
            (r'^:\s+(.+\.ck)$', self._compile_file),
            (r'^!\s+"([^"]+)"$', self._exec_code),
            (r'^\$\s+(.+)$', self._shell),
            (r'^edit\s*(\d+)$', self._edit_shred),  # Accept "edit 1" or "edit1"
            (r'^edit$', self._open_editor),
            (r'^watch$', self._watch),
            (r'^@(\w+)$', self._load_snippet),
        ]

    def parse(self, text: str) -> Optional[Command]:
        for pattern, handler in self.patterns:
            match = re.match(pattern, text)
            if match:
                return handler(match)

        # Return None for potential ChucK code (will be handled by REPL)
        # Don't generate error for things that look like ChucK code
        return None

    def _spork_file(self, m):
        return Command('spork_file', {'path': m.group(1)})

    def _spork_code(self, m):
        return Command('spork_code', {'code': m.group(1)})

    def _remove_all(self, m):
        return Command('remove_all', {})

    def _remove_shred(self, m):
        return Command('remove_shred', {'id': int(m.group(1))})

    def _replace_shred(self, m):
        return Command('replace_shred', {
            'id': int(m.group(1)),
            'code': m.group(2)
        })

    def _replace_shred_file(self, m):
        return Command('replace_shred_file', {
            'id': int(m.group(1)),
            'path': m.group(2)
        })

    def _status(self, m):
        return Command('status', {})

    def _list_shreds(self, m):
        return Command('list_shreds', {})

    def _shred_info(self, m):
        return Command('shred_info', {'id': int(m.group(1))})

    def _list_globals(self, m):
        return Command('list_globals', {})

    def _audio_info(self, m):
        return Command('audio_info', {})

    def _current_time(self, m):
        return Command('current_time', {})

    def _set_global(self, m):
        name = m.group(1)
        value_str = m.group(2)
        return Command('set_global', {
            'name': name,
            'value': self._parse_value(value_str)
        })

    def _get_global(self, m):
        return Command('get_global', {'name': m.group(1)})

    def _broadcast_event(self, m):
        return Command('broadcast_event', {'name': m.group(1)})

    def _signal_event(self, m):
        return Command('signal_event', {'name': m.group(1)})

    def _start_audio(self, m):
        return Command('start_audio', {})

    def _stop_audio(self, m):
        return Command('stop_audio', {})

    def _shutdown_audio(self, m):
        return Command('shutdown_audio', {})

    def _clear_vm(self, m):
        return Command('clear_vm', {})

    def _reset_id(self, m):
        return Command('reset_id', {})

    def _clear_screen(self, m):
        return Command('clear_screen', {})

    def _compile_file(self, m):
        return Command('compile_file', {'path': m.group(1)})

    def _exec_code(self, m):
        return Command('exec_code', {'code': m.group(1)})

    def _shell(self, m):
        return Command('shell', {'cmd': m.group(1)})

    def _edit_shred(self, m):
        return Command('edit_shred', {'id': int(m.group(1))})

    def _open_editor(self, m):
        return Command('open_editor', {})

    def _watch(self, m):
        return Command('watch', {})

    def _load_snippet(self, m):
        return Command('load_snippet', {'name': m.group(1)})

    def _parse_value(self, s):
        """Parse value from string"""
        s = s.strip()

        # Array
        if s.startswith('[') and s.endswith(']'):
            import ast
            return ast.literal_eval(s)

        # String
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]

        # Number
        try:
            if '.' in s:
                return float(s)
            return int(s)
        except ValueError:
            return s
