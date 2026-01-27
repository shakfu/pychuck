"""Tests for the ChuckCompleter class."""

import pytest
from prompt_toolkit.document import Document

from numchuck.tui.completer import ChuckCompleter


class MockChuck:
    """Mock ChucK instance for testing."""

    def __init__(self, globals_list=None):
        self._globals = globals_list or []

    def get_all_globals(self):
        return self._globals


class MockSession:
    """Mock session for testing."""

    def __init__(self, shreds=None):
        self.shreds = shreds or {}


class TestChuckCompleter:
    """Test ChuckCompleter functionality."""

    def test_repl_command_completion(self):
        """Test completion of REPL commands."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("hel")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'help'
        assert any(c.text == "help" for c in completions)

    def test_chuck_keyword_completion(self):
        """Test completion of ChucK keywords."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("whil")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'while'
        assert any(c.text == "while" for c in completions)

    def test_ugen_completion(self):
        """Test completion of UGen names."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("SinO")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'SinOsc'
        assert any(c.text == "SinOsc" for c in completions)

    def test_shred_id_completion_for_remove(self):
        """Test shred ID completion after '-'."""
        session = MockSession(shreds={1: {}, 2: {}, 3: {}})
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("- 1")
        completions = list(completer.get_completions(doc, None))

        # Should suggest '1'
        assert any(c.text == "1" for c in completions)

    def test_shred_id_completion_includes_all(self):
        """Test that '- ' completion includes 'all'."""
        session = MockSession(shreds={1: {}})
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("- a")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'all'
        assert any(c.text == "all" for c in completions)

    def test_global_variable_completion(self):
        """Test global variable completion with '?'."""
        session = MockSession()
        chuck = MockChuck(globals_list=[("int", "tempo"), ("float", "gain")])
        completer = ChuckCompleter(session, chuck)

        doc = Document("tem?")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'tempo?'
        assert any(c.text == "tempo?" for c in completions)

    def test_global_variable_set_completion(self):
        """Test global variable completion with '::'."""
        session = MockSession()
        chuck = MockChuck(globals_list=[("int", "tempo"), ("float", "gain")])
        completer = ChuckCompleter(session, chuck)

        doc = Document("tem::")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'tempo::'
        assert any(c.text == "tempo::" for c in completions)

    def test_shred_info_completion(self):
        """Test shred ID completion after '? '."""
        session = MockSession(shreds={42: {}})
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("? 4")
        completions = list(completer.get_completions(doc, None))

        # Should suggest '42'
        assert any(c.text == "42" for c in completions)

    def test_replace_shred_completion(self):
        """Test shred ID completion after '~ '."""
        session = MockSession(shreds={10: {}})
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("~ 1")
        completions = list(completer.get_completions(doc, None))

        # Should suggest '10'
        assert any(c.text == "10" for c in completions)

    def test_empty_input(self):
        """Test completion with empty input."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("")
        completions = list(completer.get_completions(doc, None))

        # Should suggest REPL commands
        assert len(completions) > 0

    def test_no_crash_on_session_error(self):
        """Test that completer doesn't crash if session access fails."""
        session = MockSession()
        session.shreds = None  # Will cause AttributeError
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("- a")
        # Should not raise exception
        completions = list(completer.get_completions(doc, None))
        # 'all' should still be suggested even if session.shreds fails
        assert any(c.text == "all" for c in completions)

    def test_no_crash_on_chuck_error(self):
        """Test that completer doesn't crash if chuck access fails."""
        session = MockSession()
        chuck = MockChuck()
        chuck.get_all_globals = lambda: (_ for _ in ()).throw(RuntimeError("test"))
        completer = ChuckCompleter(session, chuck)

        doc = Document("var?")
        # Should not raise exception
        completions = list(completer.get_completions(doc, None))
        # Should return empty since globals query failed
        assert completions == []

    def test_ugen_param_completion_after_dot(self):
        """Test UGen parameter completion after a dot."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        # Simple dot completion without known UGen context
        doc = Document("s.fr")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'freq' (common UGen parameter)
        assert any(c.text == "freq" for c in completions)

    def test_ugen_param_completion_with_context(self):
        """Test UGen parameter completion with known UGen type."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        # With UGen declaration context
        doc = Document("SinOsc s; s.fr")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'freq' with 'SinOsc' in metadata
        freq_completions = [c for c in completions if c.text == "freq"]
        assert len(freq_completions) > 0
        # display_meta may be a string or FormattedText, check string content
        meta = freq_completions[0].display_meta
        meta_str = str(meta) if hasattr(meta, "__iter__") else meta
        assert "SinOsc" in meta_str

    def test_ugen_param_completion_empty_prefix(self):
        """Test UGen parameter completion with empty prefix after dot."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("s.")
        completions = list(completer.get_completions(doc, None))

        # Should suggest common UGen parameters
        param_names = [c.text for c in completions]
        assert "freq" in param_names
        assert "gain" in param_names

    def test_ugen_param_filter_specific(self):
        """Test that filter UGens get filter-specific parameters."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("LPF f; f.Q")
        completions = list(completer.get_completions(doc, None))

        # Should suggest 'Q' (filter parameter)
        assert any(c.text == "Q" for c in completions)

    def test_ugen_param_adsr_specific(self):
        """Test that ADSR gets envelope-specific parameters."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("ADSR e; e.attack")
        completions = list(completer.get_completions(doc, None))

        # Should suggest attackTime, attackRate
        param_names = [c.text for c in completions]
        assert "attackTime" in param_names
        assert "attackRate" in param_names

    def test_ugen_param_sndbuf_specific(self):
        """Test that SndBuf gets buffer-specific parameters."""
        session = MockSession()
        chuck = MockChuck()
        completer = ChuckCompleter(session, chuck)

        doc = Document("SndBuf buf; buf.r")
        completions = list(completer.get_completions(doc, None))

        # Should suggest rate, read
        param_names = [c.text for c in completions]
        assert "rate" in param_names
        assert "read" in param_names
