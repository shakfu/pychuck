from typing import Dict, List

class REPLSession:
    def __init__(self, chuck):
        self.chuck = chuck
        self.shreds: Dict[int, str] = {}  # id -> name/code
        self.audio_running = False

    def add_shred(self, shred_id: int, name: str):
        self.shreds[shred_id] = name

    def remove_shred(self, shred_id: int):
        self.shreds.pop(shred_id, None)

    def clear_shreds(self):
        self.shreds.clear()

    def get_shred_name(self, shred_id: int) -> str:
        return self.shreds.get(shred_id, f"shred-{shred_id}")
