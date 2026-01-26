"""Tests for MIDI Learn functionality."""

from __future__ import annotations

import pytest

from numchuck.midi import (
    MIDILearnState,
    MIDIMapping,
    MIDIMappings,
    generate_midi_listener_code,
    generate_midi_monitor_code,
)


class TestMIDIMapping:
    """Tests for MIDIMapping dataclass."""

    def test_create_mapping(self) -> None:
        """Test creating a MIDI mapping."""
        mapping = MIDIMapping(
            channel=0,
            cc_number=1,
            global_name="tempo",
            min_value=60.0,
            max_value=180.0,
        )

        assert mapping.channel == 0
        assert mapping.cc_number == 1
        assert mapping.global_name == "tempo"
        assert mapping.min_value == 60.0
        assert mapping.max_value == 180.0

    def test_default_values(self) -> None:
        """Test default min/max values."""
        mapping = MIDIMapping(channel=0, cc_number=1, global_name="test")

        assert mapping.min_value == 0.0
        assert mapping.max_value == 1.0

    def test_invalid_channel_raises(self) -> None:
        """Test that invalid channel raises error."""
        with pytest.raises(ValueError, match="MIDI channel must be 0-15"):
            MIDIMapping(channel=16, cc_number=1, global_name="test")

        with pytest.raises(ValueError, match="MIDI channel must be 0-15"):
            MIDIMapping(channel=-1, cc_number=1, global_name="test")

    def test_invalid_cc_number_raises(self) -> None:
        """Test that invalid CC number raises error."""
        with pytest.raises(ValueError, match="MIDI CC number must be 0-127"):
            MIDIMapping(channel=0, cc_number=128, global_name="test")

        with pytest.raises(ValueError, match="MIDI CC number must be 0-127"):
            MIDIMapping(channel=0, cc_number=-1, global_name="test")

    def test_empty_global_name_raises(self) -> None:
        """Test that empty global name raises error."""
        with pytest.raises(ValueError, match="Global name cannot be empty"):
            MIDIMapping(channel=0, cc_number=1, global_name="")

    def test_to_dict(self) -> None:
        """Test converting mapping to dictionary."""
        mapping = MIDIMapping(
            channel=1,
            cc_number=7,
            global_name="volume",
            min_value=0.0,
            max_value=1.0,
        )

        result = mapping.to_dict()

        assert result["channel"] == 1
        assert result["cc_number"] == 7
        assert result["global_name"] == "volume"
        assert result["min_value"] == 0.0
        assert result["max_value"] == 1.0

    def test_from_dict(self) -> None:
        """Test creating mapping from dictionary."""
        data = {
            "channel": 2,
            "cc_number": 74,
            "global_name": "filter_freq",
            "min_value": 100.0,
            "max_value": 10000.0,
        }

        mapping = MIDIMapping.from_dict(data)

        assert mapping.channel == 2
        assert mapping.cc_number == 74
        assert mapping.global_name == "filter_freq"
        assert mapping.min_value == 100.0
        assert mapping.max_value == 10000.0

    def test_from_dict_default_values(self) -> None:
        """Test from_dict with missing optional fields."""
        data = {
            "channel": 0,
            "cc_number": 1,
            "global_name": "test",
        }

        mapping = MIDIMapping.from_dict(data)

        assert mapping.min_value == 0.0
        assert mapping.max_value == 1.0

    def test_scale_value_zero(self) -> None:
        """Test scaling CC value of 0."""
        mapping = MIDIMapping(
            channel=0,
            cc_number=1,
            global_name="test",
            min_value=100.0,
            max_value=200.0,
        )

        result = mapping.scale_value(0)

        assert result == 100.0

    def test_scale_value_max(self) -> None:
        """Test scaling CC value of 127."""
        mapping = MIDIMapping(
            channel=0,
            cc_number=1,
            global_name="test",
            min_value=100.0,
            max_value=200.0,
        )

        result = mapping.scale_value(127)

        assert result == 200.0

    def test_scale_value_middle(self) -> None:
        """Test scaling middle CC value."""
        mapping = MIDIMapping(
            channel=0,
            cc_number=1,
            global_name="test",
            min_value=0.0,
            max_value=1.0,
        )

        result = mapping.scale_value(63)

        # 63/127 ~ 0.496
        assert 0.49 < result < 0.50


class TestMIDIMappings:
    """Tests for MIDIMappings collection."""

    def test_create_empty(self) -> None:
        """Test creating empty mappings collection."""
        mappings = MIDIMappings()

        assert len(mappings) == 0

    def test_add_mapping(self) -> None:
        """Test adding a mapping."""
        mappings = MIDIMappings()
        mapping = MIDIMapping(channel=0, cc_number=1, global_name="test")

        mappings.add(mapping)

        assert len(mappings) == 1

    def test_add_replaces_same_channel_cc(self) -> None:
        """Test that adding mapping for same channel/CC replaces it."""
        mappings = MIDIMappings()
        mapping1 = MIDIMapping(channel=0, cc_number=1, global_name="first")
        mapping2 = MIDIMapping(channel=0, cc_number=1, global_name="second")

        mappings.add(mapping1)
        mappings.add(mapping2)

        assert len(mappings) == 1
        assert mappings.get(0, 1).global_name == "second"

    def test_remove_by_channel_cc(self) -> None:
        """Test removing by channel and CC number."""
        mappings = MIDIMappings()
        mapping = MIDIMapping(channel=0, cc_number=1, global_name="test")
        mappings.add(mapping)

        result = mappings.remove(0, 1)

        assert result is True
        assert len(mappings) == 0

    def test_remove_nonexistent(self) -> None:
        """Test removing nonexistent mapping."""
        mappings = MIDIMappings()

        result = mappings.remove(0, 1)

        assert result is False

    def test_remove_by_global(self) -> None:
        """Test removing by global name."""
        mappings = MIDIMappings()
        mapping = MIDIMapping(channel=0, cc_number=1, global_name="test")
        mappings.add(mapping)

        result = mappings.remove_by_global("test")

        assert result is True
        assert len(mappings) == 0

    def test_get_by_channel_cc(self) -> None:
        """Test getting by channel and CC number."""
        mappings = MIDIMappings()
        mapping = MIDIMapping(channel=1, cc_number=7, global_name="volume")
        mappings.add(mapping)

        result = mappings.get(1, 7)

        assert result is not None
        assert result.global_name == "volume"

    def test_get_nonexistent(self) -> None:
        """Test getting nonexistent mapping."""
        mappings = MIDIMappings()

        result = mappings.get(0, 1)

        assert result is None

    def test_get_by_global(self) -> None:
        """Test getting by global name."""
        mappings = MIDIMappings()
        mapping = MIDIMapping(channel=0, cc_number=1, global_name="tempo")
        mappings.add(mapping)

        result = mappings.get_by_global("tempo")

        assert result is not None
        assert result.cc_number == 1

    def test_clear(self) -> None:
        """Test clearing all mappings."""
        mappings = MIDIMappings()
        mappings.add(MIDIMapping(channel=0, cc_number=1, global_name="a"))
        mappings.add(MIDIMapping(channel=0, cc_number=2, global_name="b"))

        mappings.clear()

        assert len(mappings) == 0

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        mappings = MIDIMappings()
        mappings.add(MIDIMapping(channel=0, cc_number=1, global_name="test"))

        result = mappings.to_dict()

        assert "mappings" in result
        assert len(result["mappings"]) == 1

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "mappings": [
                {"channel": 0, "cc_number": 1, "global_name": "a"},
                {"channel": 0, "cc_number": 2, "global_name": "b"},
            ]
        }

        mappings = MIDIMappings.from_dict(data)

        assert len(mappings) == 2

    def test_iteration(self) -> None:
        """Test iterating over mappings."""
        mappings = MIDIMappings()
        mappings.add(MIDIMapping(channel=0, cc_number=1, global_name="a"))
        mappings.add(MIDIMapping(channel=0, cc_number=2, global_name="b"))

        names = [m.global_name for m in mappings]

        assert "a" in names
        assert "b" in names


class TestMIDILearnState:
    """Tests for MIDILearnState class."""

    def test_initial_state(self) -> None:
        """Test initial state is not learning."""
        state = MIDILearnState()

        assert not state.is_learning
        assert state.target_global is None

    def test_start_learning(self) -> None:
        """Test starting learn mode."""
        state = MIDILearnState()

        state.start_learning("tempo")

        assert state.is_learning
        assert state.target_global == "tempo"

    def test_start_learning_with_range(self) -> None:
        """Test starting learn mode with min/max values."""
        state = MIDILearnState()

        state.start_learning("bpm", min_value=60.0, max_value=180.0)

        assert state.is_learning

    def test_finish_learning(self) -> None:
        """Test finishing learn mode."""
        state = MIDILearnState()
        state.start_learning("volume", min_value=0.0, max_value=1.0)

        mapping = state.finish_learning(channel=0, cc_number=7)

        assert not state.is_learning
        assert mapping.channel == 0
        assert mapping.cc_number == 7
        assert mapping.global_name == "volume"
        assert mapping.min_value == 0.0
        assert mapping.max_value == 1.0

    def test_finish_learning_not_learning_raises(self) -> None:
        """Test that finishing when not learning raises error."""
        state = MIDILearnState()

        with pytest.raises(RuntimeError, match="Not in learn mode"):
            state.finish_learning(0, 1)

    def test_cancel_learning(self) -> None:
        """Test canceling learn mode."""
        state = MIDILearnState()
        state.start_learning("test")

        state.cancel_learning()

        assert not state.is_learning
        assert state.target_global is None


class TestGenerateMIDICode:
    """Tests for MIDI code generation."""

    def test_generate_empty_mappings(self) -> None:
        """Test generating code for empty mappings."""
        mappings = MIDIMappings()

        code = generate_midi_listener_code(mappings)

        assert code == ""

    def test_generate_single_mapping(self) -> None:
        """Test generating code for single mapping."""
        mappings = MIDIMappings()
        mappings.add(MIDIMapping(channel=0, cc_number=1, global_name="tempo"))

        code = generate_midi_listener_code(mappings)

        assert "MidiIn" in code
        assert "tempo" in code
        assert "channel == 0" in code
        assert "cc == 1" in code

    def test_generate_multiple_mappings(self) -> None:
        """Test generating code for multiple mappings."""
        mappings = MIDIMappings()
        mappings.add(MIDIMapping(channel=0, cc_number=1, global_name="tempo"))
        mappings.add(MIDIMapping(channel=0, cc_number=7, global_name="volume"))

        code = generate_midi_listener_code(mappings)

        assert "tempo" in code
        assert "volume" in code
        assert "else if" in code

    def test_generate_monitor_code(self) -> None:
        """Test generating MIDI monitor code."""
        code = generate_midi_monitor_code()

        assert "MidiIn" in code
        assert "monitor" in code.lower()


class TestCommandParserMIDICommands:
    """Tests for MIDI command parsing."""

    def test_parse_midi_learn(self) -> None:
        """Test parsing 'midi learn varname' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi learn tempo")

        assert cmd is not None
        assert cmd.type == "midi_learn"
        assert cmd.args["name"] == "tempo"
        assert cmd.args["min"] == 0.0
        assert cmd.args["max"] == 1.0

    def test_parse_midi_learn_with_range(self) -> None:
        """Test parsing 'midi learn varname min max' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi learn bpm 60 180")

        assert cmd is not None
        assert cmd.type == "midi_learn"
        assert cmd.args["name"] == "bpm"
        assert cmd.args["min"] == 60.0
        assert cmd.args["max"] == 180.0

    def test_parse_midi_list(self) -> None:
        """Test parsing 'midi list' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi list")

        assert cmd is not None
        assert cmd.type == "midi_list"

    def test_parse_midi_remove(self) -> None:
        """Test parsing 'midi remove varname' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi remove tempo")

        assert cmd is not None
        assert cmd.type == "midi_remove"
        assert cmd.args["name"] == "tempo"

    def test_parse_midi_start(self) -> None:
        """Test parsing 'midi start' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi start")

        assert cmd is not None
        assert cmd.type == "midi_start"

    def test_parse_midi_stop(self) -> None:
        """Test parsing 'midi stop' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi stop")

        assert cmd is not None
        assert cmd.type == "midi_stop"

    def test_parse_midi_status(self) -> None:
        """Test parsing 'midi status' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi status")

        assert cmd is not None
        assert cmd.type == "midi_status"

    def test_parse_midi_monitor(self) -> None:
        """Test parsing 'midi monitor' command."""
        from numchuck.tui.parser import CommandParser

        parser = CommandParser()
        cmd = parser.parse("midi monitor")

        assert cmd is not None
        assert cmd.type == "midi_monitor"
