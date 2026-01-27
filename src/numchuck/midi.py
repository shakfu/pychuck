"""
MIDI support for numchuck.

Provides MIDI CC to ChucK global variable mapping and ChucK code generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from .constants import MIDI_CC_NORMALIZE, MIDI_MAX_CC, MIDI_MAX_CHANNEL

if TYPE_CHECKING:
    pass


@dataclass
class MIDIMapping:
    """A mapping from MIDI CC to a ChucK global variable.

    Attributes:
        channel: MIDI channel (0-15)
        cc_number: MIDI CC number (0-127)
        global_name: Name of the ChucK global variable to control
        min_value: Minimum output value (when CC is 0)
        max_value: Maximum output value (when CC is 127)
    """

    channel: int
    cc_number: int
    global_name: str
    min_value: float = 0.0
    max_value: float = 1.0

    def __post_init__(self) -> None:
        """Validate the mapping parameters."""
        if not 0 <= self.channel <= MIDI_MAX_CHANNEL:
            raise ValueError(
                f"MIDI channel must be 0-{MIDI_MAX_CHANNEL}, got {self.channel}"
            )
        if not 0 <= self.cc_number <= MIDI_MAX_CC:
            raise ValueError(
                f"MIDI CC number must be 0-{MIDI_MAX_CC}, got {self.cc_number}"
            )
        if not self.global_name:
            raise ValueError("Global name cannot be empty")

    def to_dict(self) -> dict[str, int | str | float]:
        """Convert to dictionary for serialization."""
        return {
            "channel": self.channel,
            "cc_number": self.cc_number,
            "global_name": self.global_name,
            "min_value": self.min_value,
            "max_value": self.max_value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int | str | float]) -> "MIDIMapping":
        """Create from dictionary."""
        return cls(
            channel=int(data["channel"]),
            cc_number=int(data["cc_number"]),
            global_name=str(data["global_name"]),
            min_value=float(data.get("min_value", 0.0)),
            max_value=float(data.get("max_value", 1.0)),
        )

    def scale_value(self, cc_value: int) -> float:
        """Scale a MIDI CC value (0-127) to the configured range.

        Args:
            cc_value: MIDI CC value (0-127)

        Returns:
            Scaled value in [min_value, max_value] range
        """
        normalized = cc_value / MIDI_CC_NORMALIZE
        return self.min_value + normalized * (self.max_value - self.min_value)


@dataclass
class MIDIMappings:
    """Collection of MIDI mappings.

    Manages multiple MIDI CC to global variable mappings.
    """

    mappings: list[MIDIMapping] = field(default_factory=list)

    def add(self, mapping: MIDIMapping) -> None:
        """Add a mapping.

        Args:
            mapping: The mapping to add
        """
        # Remove any existing mapping for the same channel/cc
        self.remove(mapping.channel, mapping.cc_number)
        self.mappings.append(mapping)

    def remove(self, channel: int, cc_number: int) -> bool:
        """Remove a mapping by channel and CC number.

        Args:
            channel: MIDI channel
            cc_number: MIDI CC number

        Returns:
            True if a mapping was removed
        """
        for i, m in enumerate(self.mappings):
            if m.channel == channel and m.cc_number == cc_number:
                del self.mappings[i]
                return True
        return False

    def remove_by_global(self, global_name: str) -> bool:
        """Remove a mapping by global variable name.

        Args:
            global_name: Name of the global variable

        Returns:
            True if a mapping was removed
        """
        for i, m in enumerate(self.mappings):
            if m.global_name == global_name:
                del self.mappings[i]
                return True
        return False

    def get(self, channel: int, cc_number: int) -> MIDIMapping | None:
        """Get a mapping by channel and CC number.

        Args:
            channel: MIDI channel
            cc_number: MIDI CC number

        Returns:
            The mapping if found, None otherwise
        """
        for m in self.mappings:
            if m.channel == channel and m.cc_number == cc_number:
                return m
        return None

    def get_by_global(self, global_name: str) -> MIDIMapping | None:
        """Get a mapping by global variable name.

        Args:
            global_name: Name of the global variable

        Returns:
            The mapping if found, None otherwise
        """
        for m in self.mappings:
            if m.global_name == global_name:
                return m
        return None

    def clear(self) -> None:
        """Remove all mappings."""
        self.mappings.clear()

    def to_dict(self) -> dict[str, list[dict[str, int | str | float]]]:
        """Convert to dictionary for serialization."""
        return {"mappings": [m.to_dict() for m in self.mappings]}

    @classmethod
    def from_dict(
        cls, data: dict[str, list[dict[str, int | str | float]]]
    ) -> "MIDIMappings":
        """Create from dictionary."""
        mappings = [MIDIMapping.from_dict(m) for m in data.get("mappings", [])]
        return cls(mappings=mappings)

    def __len__(self) -> int:
        """Return number of mappings."""
        return len(self.mappings)

    def __iter__(self) -> "Iterator[MIDIMapping]":
        """Iterate over mappings."""
        return iter(self.mappings)


class MIDILearnState:
    """State machine for MIDI learn mode.

    When in learn mode, the next MIDI CC message received
    will be mapped to the target global variable.
    """

    def __init__(self) -> None:
        """Initialize learn state."""
        self._learning: bool = False
        self._target_global: str | None = None
        self._min_value: float = 0.0
        self._max_value: float = 1.0

    @property
    def is_learning(self) -> bool:
        """Check if currently in learn mode."""
        return self._learning

    @property
    def target_global(self) -> str | None:
        """Get the target global variable name."""
        return self._target_global

    def start_learning(
        self,
        global_name: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
    ) -> None:
        """Start learning mode for a global variable.

        Args:
            global_name: Name of the global to map
            min_value: Minimum output value
            max_value: Maximum output value
        """
        self._learning = True
        self._target_global = global_name
        self._min_value = min_value
        self._max_value = max_value

    def finish_learning(self, channel: int, cc_number: int) -> MIDIMapping:
        """Finish learning and create a mapping.

        Args:
            channel: MIDI channel that was detected
            cc_number: MIDI CC number that was detected

        Returns:
            The created mapping

        Raises:
            RuntimeError: If not in learn mode
        """
        if not self._learning or self._target_global is None:
            raise RuntimeError("Not in learn mode")

        mapping = MIDIMapping(
            channel=channel,
            cc_number=cc_number,
            global_name=self._target_global,
            min_value=self._min_value,
            max_value=self._max_value,
        )
        self.cancel_learning()
        return mapping

    def cancel_learning(self) -> None:
        """Cancel learn mode without creating a mapping."""
        self._learning = False
        self._target_global = None
        self._min_value = 0.0
        self._max_value = 1.0


def generate_midi_listener_code(mappings: MIDIMappings) -> str:
    """Generate ChucK code for MIDI CC to global variable mapping.

    This generates a ChucK shred that listens for MIDI CC messages
    and updates the corresponding global variables.

    Args:
        mappings: The mappings to use

    Returns:
        ChucK code string
    """
    if len(mappings) == 0:
        return ""

    lines = [
        "// MIDI CC listener",
        "// Maps MIDI CC to global variables",
        "",
        "MidiIn min;",
        "MidiMsg msg;",
        "",
        '// Open default MIDI port (use "min.open(port)" for specific port)',
        "if (!min.open(0)) {",
        '    <<< "Error: Could not open MIDI input" >>>;',
        "    me.exit();",
        "}",
        "",
        '<<< "MIDI listener started" >>>;',
        "",
        "while (true) {",
        "    min => now;",
        "    while (min.recv(msg)) {",
        "        // Check for CC messages (status 0xB0-0xBF)",
        "        if ((msg.data1 & 0xF0) == 0xB0) {",
        "            (msg.data1 & 0x0F) => int channel;",
        "            msg.data2 => int cc;",
        "            msg.data3 => int value;",
        "",
    ]

    # Generate case for each mapping
    first = True
    for mapping in mappings:
        condition = "if" if first else "else if"
        first = False

        # Calculate scaling
        scale = mapping.max_value - mapping.min_value
        offset = mapping.min_value

        lines.extend(
            [
                f"            {condition} (channel == {mapping.channel} && cc == {mapping.cc_number}) {{",
                f"                {offset} + (value / 127.0) * {scale} => global float {mapping.global_name};",
                "            }",
            ]
        )

    lines.extend(
        [
            "        }",
            "    }",
            "}",
        ]
    )

    return "\n".join(lines)


def generate_midi_monitor_code() -> str:
    """Generate ChucK code for monitoring MIDI CC messages.

    This is useful for debugging MIDI input without mappings.

    Returns:
        ChucK code string
    """
    return """// MIDI CC Monitor
MidiIn min;
MidiMsg msg;

if (!min.open(0)) {
    <<< "Error: Could not open MIDI input" >>>;
    me.exit();
}

<<< "MIDI monitor started - move a controller..." >>>;

while (true) {
    min => now;
    while (min.recv(msg)) {
        if ((msg.data1 & 0xF0) == 0xB0) {
            (msg.data1 & 0x0F) => int channel;
            msg.data2 => int cc;
            msg.data3 => int value;
            <<< "Channel:", channel, "CC:", cc, "Value:", value >>>;
        }
    }
}
"""
