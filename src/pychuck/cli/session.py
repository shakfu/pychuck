from typing import Dict, List

class REPLSession:
    def __init__(self, chuck):
        self.chuck = chuck
        self.shreds: Dict[int, Dict] = {}  # id -> {'source': 'file.ck', 'type': 'file', 'chuck_time': samples}
        self.audio_running = False

    def add_shred(self, shred_id: int, source: str, shred_type: str = 'file'):
        """Add a shred

        Args:
            shred_id: ChucK shred ID
            source: File path or code snippet
            shred_type: 'file' or 'code'
        """
        # Capture ChucK VM time when shred was created
        try:
            chuck_time = self.chuck.now()
        except:
            chuck_time = 0.0

        self.shreds[shred_id] = {
            'source': source,
            'type': shred_type,
            'chuck_time': chuck_time  # ChucK VM time in samples when shred was created
        }

    def remove_shred(self, shred_id: int):
        if shred_id in self.shreds:
            self.shreds.pop(shred_id)

    def clear_shreds(self):
        self.shreds.clear()

    def get_shred_name(self, shred_id: int) -> str:
        if shred_id in self.shreds:
            return self.shreds[shred_id]['source']
        return f"shred-{shred_id}"
