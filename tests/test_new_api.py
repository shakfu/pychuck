"""Tests for new API features: Shred handles, Global proxies, Config."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from numchuck import Chuck, Shred, GlobalInt, GlobalFloat, GlobalString
from numchuck.config import Config, load_config, save_config, AudioConfig, REPLConfig


class TestShredHandles:
    """Test Shred handle objects."""

    def test_spork_returns_shred(self):
        """Test that spork() returns a Shred object."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        assert isinstance(shred, Shred)
        assert shred.id > 0

    def test_shred_is_running(self):
        """Test is_running property."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        assert shred.is_running is True

    def test_shred_remove(self):
        """Test removing a shred."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        assert shred.is_running is True
        shred.remove()
        chuck.run(100)
        assert shred.is_running is False

    def test_shred_replace(self):
        """Test replacing a shred."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        assert shred.is_running is True

        shred.replace("TriOsc t => dac; 1::second => now;")
        chuck.run(100)
        # After replace, shred should still be running (possibly with new ID)
        assert shred.id > 0
        assert shred.is_running is True

    def test_shred_replace_returns_self(self):
        """Test that replace() returns self for chaining."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        result = shred.replace("TriOsc t => dac; 1::second => now;")
        assert result is shred

    def test_shred_info(self):
        """Test getting shred info."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        info = shred.info
        assert info is not None
        assert "id" in info

    def test_shred_repr(self):
        """Test Shred string representation."""
        chuck = Chuck()
        shred = chuck.spork("SinOsc s => dac; 1::second => now;")
        chuck.run(100)
        assert "running" in repr(shred)
        shred.remove()
        chuck.run(100)
        assert "stopped" in repr(shred)

    def test_shred_equality(self):
        """Test Shred equality comparison."""
        chuck = Chuck()
        shred1 = chuck.spork("SinOsc s => dac; 1::second => now;")
        # Compare with int
        assert shred1 == shred1.id
        # Compare with self
        assert shred1 == shred1

    def test_spork_failure_raises(self):
        """Test that spork raises on compilation failure."""
        chuck = Chuck()
        with pytest.raises(RuntimeError):
            chuck.spork("invalid code here")


class TestGlobalVariableProxies:
    """Test typed global variable proxies."""

    def test_global_int_set_get(self):
        """Test GlobalInt proxy."""
        chuck = Chuck()
        chuck.compile("global int tempo;")
        chuck.run(100)

        tempo = chuck.global_int("tempo")
        assert isinstance(tempo, GlobalInt)
        assert tempo.name == "tempo"

        tempo.value = 120
        assert tempo.value == 120

    def test_global_int_set_method(self):
        """Test GlobalInt set() method."""
        chuck = Chuck()
        chuck.compile("global int tempo;")
        chuck.run(100)

        tempo = chuck.global_int("tempo")
        tempo.set(140)
        assert tempo.get() == 140

    def test_global_float_set_get(self):
        """Test GlobalFloat proxy."""
        chuck = Chuck()
        chuck.compile("global float gain;")
        chuck.run(100)

        gain = chuck.global_float("gain")
        assert isinstance(gain, GlobalFloat)

        gain.value = 0.8
        assert abs(gain.value - 0.8) < 0.0001

    def test_global_string_set_get(self):
        """Test GlobalString proxy."""
        chuck = Chuck()
        chuck.compile("global string msg;")
        chuck.run(100)

        msg = chuck.global_string("msg")
        assert isinstance(msg, GlobalString)

        msg.value = "hello"
        assert msg.value == "hello"

    def test_global_var_repr(self):
        """Test GlobalVar string representation."""
        chuck = Chuck()
        chuck.compile("global int tempo;")
        chuck.run(100)

        tempo = chuck.global_int("tempo")
        assert "tempo" in repr(tempo)
        assert "GlobalInt" in repr(tempo)


class TestAsyncAPI:
    """Test async/await API."""

    @pytest.mark.asyncio
    async def test_get_int_awaitable(self):
        """Test async get_int."""
        chuck = Chuck()
        chuck.compile("global int counter; 42 => counter;")
        chuck.run(100)

        value = await chuck.get_int_awaitable("counter")
        assert value == 42

    @pytest.mark.asyncio
    async def test_get_float_awaitable(self):
        """Test async get_float."""
        chuck = Chuck()
        chuck.compile("global float value; 3.14 => value;")
        chuck.run(100)

        value = await chuck.get_float_awaitable("value")
        assert abs(value - 3.14) < 0.01

    @pytest.mark.asyncio
    async def test_get_string_awaitable(self):
        """Test async get_string."""
        chuck = Chuck()
        chuck.compile('global string msg; "hello" => msg;')
        chuck.run(100)

        value = await chuck.get_string_awaitable("msg")
        assert value == "hello"

    @pytest.mark.asyncio
    async def test_global_proxy_async(self):
        """Test GlobalInt async method."""
        chuck = Chuck()
        chuck.compile("global int tempo; 120 => tempo;")
        chuck.run(100)

        tempo = chuck.global_int("tempo")
        value = await tempo.get_async()
        assert value == 120


class TestConfig:
    """Test configuration file support."""

    def test_default_config(self):
        """Test default Config values."""
        config = Config()
        assert config.audio.sample_rate == 44100
        assert config.audio.output_channels == 2
        assert config.repl.smart_enter is True
        assert config.chuck.chugin_enable is True

    def test_config_from_dict(self):
        """Test creating Config from dict."""
        data = {
            "audio": {"sample_rate": 48000, "output_channels": 1},
            "repl": {"smart_enter": False},
        }
        config = Config.from_dict(data)
        assert config.audio.sample_rate == 48000
        assert config.audio.output_channels == 1
        assert config.repl.smart_enter is False
        # Unset values should be defaults
        assert config.audio.input_channels == 0

    def test_config_to_dict(self):
        """Test converting Config to dict."""
        config = Config()
        data = config.to_dict()
        assert "audio" in data
        assert "repl" in data
        assert data["audio"]["sample_rate"] == 44100

    def test_save_and_load_config(self):
        """Test saving and loading config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.toml"

            config = Config()
            config.audio.sample_rate = 48000
            config.repl.smart_enter = False

            save_config(config, path)
            assert path.exists()

            loaded = load_config(path)
            assert loaded.audio.sample_rate == 48000
            assert loaded.repl.smart_enter is False

    def test_load_nonexistent_returns_defaults(self):
        """Test loading nonexistent file returns defaults."""
        config = load_config("/nonexistent/path/config.toml")
        assert config.audio.sample_rate == 44100

    def test_audio_config_defaults(self):
        """Test AudioConfig defaults."""
        audio = AudioConfig()
        assert audio.sample_rate == 44100
        assert audio.buffer_size == 512
        assert audio.num_buffers == 8

    def test_repl_config_defaults(self):
        """Test REPLConfig defaults."""
        repl = REPLConfig()
        assert repl.smart_enter is True
        assert repl.show_sidebar is True
        assert repl.max_log_lines == 100
