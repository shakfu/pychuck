from textual.widgets import Static
from textual.reactive import reactive

class AudioMeter(Static):
    """Widget to display audio status and basic metering"""

    audio_active = reactive(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.info = {}

    def refresh_audio(self, is_running: bool):
        """Update audio info"""
        self.audio_active = is_running

        if is_running:
            from ... import audio_info
            self.info = audio_info()

        self.update_display()

    def update_display(self):
        """Render audio status"""
        if self.audio_active and self.info:
            status = "[green]●[/green] RUNNING"
            content = f"""
{status}

[dim]Sample Rate:[/dim] {self.info.get('sample_rate', 0)} Hz
[dim]Channels:[/dim] {self.info.get('num_channels_out', 0)} out / {self.info.get('num_channels_in', 0)} in
[dim]Buffer:[/dim] {self.info.get('buffer_size', 0)} samples
"""
        else:
            status = "[red]●[/red] STOPPED"
            content = f"\n{status}\n\n[dim]Audio not running[/dim]"

        self.update(content.strip())
