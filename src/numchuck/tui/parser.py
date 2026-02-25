import ast
import re
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class Command:
    type: str
    args: dict[str, Any]


class CommandParser:
    def __init__(self) -> None:
        self.patterns: list[tuple[str, Callable[[re.Match[str]], Command]]] = [
            # Chuck-style word commands
            (r"^add\s+(.+\.ck)$", self._spork_file),
            (r"^remove\s+all$", self._remove_all),
            (r"^remove\s+(\d+)$", self._remove_shred),
            (r"^replace\s+(\d+)\s+(.+\.ck)$", self._replace_shred_file),
            (r'^replace\s+(\d+)\s+"([^"]+)"$', self._replace_shred),
            (r"^abort\.shred\s+(\d+)$", self._abort_shred),
            (r"^abort\s+(\d+)$", self._abort_shred),
            (r"^status$", self._status),
            (r"^time$", self._current_time),
            (r"^exit$", self._exit),
            (r"^quit$", self._exit),
            # Word aliases for symbol commands
            (r"^shreds$", self._list_shreds),
            (r"^shred\s+(\d+)$", self._shred_info),
            (r"^globals$", self._list_globals),
            (r"^audio$", self._audio_info),
            (r"^start$", self._start_audio),
            (r"^stop$", self._stop_audio),
            (r"^shutdown$", self._shutdown_audio),
            (r"^compile\s+(.+\.ck)$", self._compile_file),
            (r'^exec\s+"([^"]+)"$', self._exec_code),
            (r"^exec\s+'([^']+)'$", self._exec_code),
            (r"^shell\s+(.+)$", self._shell),
            (r"^snippet\s+(\w+)$", self._load_snippet),
            (r"^get\s+(\w+)$", self._get_global),
            (r"^set\s+(\w+)\s+(.+)$", self._set_global_word),
            (r"^signal\s+(\w+)$", self._signal_event),
            (r"^broadcast\s+(\w+)$", self._broadcast_event),
            # Shred management (ChucK shortcut symbols: + - = ^)
            (r"^\+\s+(.+\.ck)$", self._spork_file),
            (r'^\+\s+"([^"]+)"$', self._spork_code),
            (r"^\+\s+\'([^\']+)\'$", self._spork_code),
            (r"^-\s+all$", self._remove_all),
            (r"^-\s*(\d+)$", self._remove_shred),  # Accept "- 1" or "-1"
            (r"^=\s*(\d+)\s+(.+\.ck)$", self._replace_shred_file),  # = <id> file.ck
            (r'^=\s*(\d+)\s+"([^"]+)"$', self._replace_shred),  # = <id> "code"
            (r'^~\s+(\d+)\s+"([^"]+)"$', self._replace_shred),  # Legacy: ~ <id> "code"
            (r"^\^$", self._status),  # ChucK status shortcut
            # Status (numchuck extensions)
            (r"^\?$", self._list_shreds),
            (r"^\?\s+(\d+)$", self._shred_info),
            (r"^\?g$", self._list_globals),
            (r"^\?a$", self._audio_info),
            (r"^\.$", self._current_time),
            # Globals
            (r"^(\w+)::(.+)$", self._set_global),
            (r"^(\w+)\?$", self._get_global),
            # Events
            (r"^(\w+)!!$", self._broadcast_event),
            (r"^(\w+)!$", self._signal_event),
            # Audio
            (r"^>$", self._start_audio),
            (r"^\|\|$", self._stop_audio),
            (r"^X$", self._shutdown_audio),
            # VM
            (r"^clear$", self._clear_vm),
            (r"^reset$", self._reset_id),
            # Screen
            (r"^cls$", self._clear_screen),
            # Other
            (r"^:\s+(.+\.ck)$", self._compile_file),
            (r'^!\s+"([^"]+)"$', self._exec_code),
            (r"^\$\s+(.+)$", self._shell),
            (r"^edit\s*(\d+)$", self._edit_shred),  # Accept "edit 1" or "edit1"
            (r"^edit$", self._open_editor),
            (r"^watch$", self._watch),
            (r"^watch\s+(.+\.ck)$", self._watch_file),
            (r"^unwatch\s+(.+\.ck)$", self._unwatch_file),
            (r"^unwatch\s+all$", self._unwatch_all),
            (r"^watching$", self._list_watched),
            (r"^wave$", self._toggle_waveform),
            (r"^wave\s+on$", self._waveform_on),
            (r"^wave\s+off$", self._waveform_off),
            # Recording commands
            (r"^record\s+start(?:\s+(\w+))?$", self._record_start),
            (r"^record\s+stop$", self._record_stop),
            (r"^record\s+save\s+(\w+)$", self._record_save),
            (r"^record\s+discard$", self._record_discard),
            (r"^record\s+status$", self._record_status),
            # Play specific commands must come before general pattern
            (r"^play\s+pause$", self._play_pause),
            (r"^play\s+resume$", self._play_resume),
            (r"^play\s+stop$", self._play_stop),
            (r"^play\s+(\w+)(?:\s+(\d*\.?\d+))?$", self._play),
            (r"^recordings$", self._list_recordings),
            # MIDI commands
            (
                r"^midi\s+learn\s+(\w+)\s+(\d+)(?:\s+(\d+))?(?:\s+(\d*\.?\d+)\s+(\d*\.?\d+))?$",
                self._midi_learn,
            ),
            (r"^midi\s+list$", self._midi_list),
            (r"^midi\s+remove\s+(\w+)$", self._midi_remove),
            (r"^midi\s+start$", self._midi_start),
            (r"^midi\s+stop$", self._midi_stop),
            (r"^midi\s+status$", self._midi_status),
            (r"^midi\s+monitor$", self._midi_monitor),
            # OSC commands
            (r"^osc\s+start(?:\s+(\d+))?$", self._osc_start),
            (r"^osc\s+stop$", self._osc_stop),
            (r"^osc\s+status$", self._osc_status),
            (r"^@(\w+)$", self._load_snippet),
        ]

    def parse(self, text: str) -> Optional[Command]:
        for pattern, handler in self.patterns:
            match = re.match(pattern, text)
            if match:
                return handler(match)

        # Return None for potential ChucK code (will be handled by REPL)
        # Don't generate error for things that look like ChucK code
        return None

    def _spork_file(self, m: re.Match[str]) -> Command:
        return Command("spork_file", {"path": m.group(1)})

    def _spork_code(self, m: re.Match[str]) -> Command:
        return Command("spork_code", {"code": m.group(1)})

    def _remove_all(self, m: re.Match[str]) -> Command:
        return Command("remove_all", {})

    def _remove_shred(self, m: re.Match[str]) -> Command:
        return Command("remove_shred", {"id": int(m.group(1))})

    def _replace_shred(self, m: re.Match[str]) -> Command:
        return Command("replace_shred", {"id": int(m.group(1)), "code": m.group(2)})

    def _replace_shred_file(self, m: re.Match[str]) -> Command:
        return Command(
            "replace_shred_file", {"id": int(m.group(1)), "path": m.group(2)}
        )

    def _status(self, m: re.Match[str]) -> Command:
        return Command("status", {})

    def _abort_shred(self, m: re.Match[str]) -> Command:
        return Command("abort_shred", {"id": int(m.group(1))})

    def _exit(self, m: re.Match[str]) -> Command:
        return Command("exit", {})

    def _list_shreds(self, m: re.Match[str]) -> Command:
        return Command("list_shreds", {})

    def _shred_info(self, m: re.Match[str]) -> Command:
        return Command("shred_info", {"id": int(m.group(1))})

    def _list_globals(self, m: re.Match[str]) -> Command:
        return Command("list_globals", {})

    def _audio_info(self, m: re.Match[str]) -> Command:
        return Command("audio_info", {})

    def _current_time(self, m: re.Match[str]) -> Command:
        return Command("current_time", {})

    def _set_global(self, m: re.Match[str]) -> Command:
        name = m.group(1)
        value_str = m.group(2)
        return Command(
            "set_global", {"name": name, "value": self._parse_value(value_str)}
        )

    def _set_global_word(self, m: re.Match[str]) -> Command:
        return Command(
            "set_global",
            {"name": m.group(1), "value": self._parse_value(m.group(2))},
        )

    def _get_global(self, m: re.Match[str]) -> Command:
        return Command("get_global", {"name": m.group(1)})

    def _broadcast_event(self, m: re.Match[str]) -> Command:
        return Command("broadcast_event", {"name": m.group(1)})

    def _signal_event(self, m: re.Match[str]) -> Command:
        return Command("signal_event", {"name": m.group(1)})

    def _start_audio(self, m: re.Match[str]) -> Command:
        return Command("start_audio", {})

    def _stop_audio(self, m: re.Match[str]) -> Command:
        return Command("stop_audio", {})

    def _shutdown_audio(self, m: re.Match[str]) -> Command:
        return Command("shutdown_audio", {})

    def _clear_vm(self, m: re.Match[str]) -> Command:
        return Command("clear_vm", {})

    def _reset_id(self, m: re.Match[str]) -> Command:
        return Command("reset_id", {})

    def _clear_screen(self, m: re.Match[str]) -> Command:
        return Command("clear_screen", {})

    def _compile_file(self, m: re.Match[str]) -> Command:
        return Command("compile_file", {"path": m.group(1)})

    def _exec_code(self, m: re.Match[str]) -> Command:
        return Command("exec_code", {"code": m.group(1)})

    def _shell(self, m: re.Match[str]) -> Command:
        return Command("shell", {"cmd": m.group(1)})

    def _edit_shred(self, m: re.Match[str]) -> Command:
        return Command("edit_shred", {"id": int(m.group(1))})

    def _open_editor(self, m: re.Match[str]) -> Command:
        return Command("open_editor", {})

    def _watch(self, m: re.Match[str]) -> Command:
        return Command("watch", {})

    def _watch_file(self, m: re.Match[str]) -> Command:
        return Command("watch_file", {"path": m.group(1)})

    def _unwatch_file(self, m: re.Match[str]) -> Command:
        return Command("unwatch_file", {"path": m.group(1)})

    def _unwatch_all(self, m: re.Match[str]) -> Command:
        return Command("unwatch_all", {})

    def _list_watched(self, m: re.Match[str]) -> Command:
        return Command("list_watched", {})

    def _toggle_waveform(self, m: re.Match[str]) -> Command:
        return Command("toggle_waveform", {})

    def _waveform_on(self, m: re.Match[str]) -> Command:
        return Command("waveform_on", {})

    def _waveform_off(self, m: re.Match[str]) -> Command:
        return Command("waveform_off", {})

    def _record_start(self, m: re.Match[str]) -> Command:
        name = m.group(1) if m.group(1) else None
        return Command("record_start", {"name": name})

    def _record_stop(self, m: re.Match[str]) -> Command:
        return Command("record_stop", {})

    def _record_save(self, m: re.Match[str]) -> Command:
        return Command("record_save", {"name": m.group(1)})

    def _record_discard(self, m: re.Match[str]) -> Command:
        return Command("record_discard", {})

    def _record_status(self, m: re.Match[str]) -> Command:
        return Command("record_status", {})

    def _play(self, m: re.Match[str]) -> Command:
        name = m.group(1)
        speed = float(m.group(2)) if m.group(2) else 1.0
        return Command("play", {"name": name, "speed": speed})

    def _play_pause(self, m: re.Match[str]) -> Command:
        return Command("play_pause", {})

    def _play_resume(self, m: re.Match[str]) -> Command:
        return Command("play_resume", {})

    def _play_stop(self, m: re.Match[str]) -> Command:
        return Command("play_stop", {})

    def _list_recordings(self, m: re.Match[str]) -> Command:
        return Command("list_recordings", {})

    def _load_snippet(self, m: re.Match[str]) -> Command:
        return Command("load_snippet", {"name": m.group(1)})

    def _midi_learn(self, m: re.Match[str]) -> Command:
        name = m.group(1)
        cc = int(m.group(2))
        channel = int(m.group(3)) if m.group(3) else 0
        min_val = float(m.group(4)) if m.group(4) else 0.0
        max_val = float(m.group(5)) if m.group(5) else 1.0
        return Command(
            "midi_learn",
            {
                "name": name,
                "cc": cc,
                "channel": channel,
                "min": min_val,
                "max": max_val,
            },
        )

    def _midi_list(self, m: re.Match[str]) -> Command:
        return Command("midi_list", {})

    def _midi_remove(self, m: re.Match[str]) -> Command:
        return Command("midi_remove", {"name": m.group(1)})

    def _midi_start(self, m: re.Match[str]) -> Command:
        return Command("midi_start", {})

    def _midi_stop(self, m: re.Match[str]) -> Command:
        return Command("midi_stop", {})

    def _midi_status(self, m: re.Match[str]) -> Command:
        return Command("midi_status", {})

    def _midi_monitor(self, m: re.Match[str]) -> Command:
        return Command("midi_monitor", {})

    def _osc_start(self, m: re.Match[str]) -> Command:
        port = int(m.group(1)) if m.group(1) else 9000
        return Command("osc_start", {"port": port})

    def _osc_stop(self, m: re.Match[str]) -> Command:
        return Command("osc_stop", {})

    def _osc_status(self, m: re.Match[str]) -> Command:
        return Command("osc_status", {})

    def _parse_value(self, s: str) -> int | float | str | list[Any]:
        """Parse value from string"""
        s = s.strip()

        # Array
        if s.startswith("[") and s.endswith("]"):
            result: list[Any] = ast.literal_eval(s)
            return result

        # String
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]

        # Number
        try:
            if "." in s:
                return float(s)
            return int(s)
        except ValueError:
            return s
