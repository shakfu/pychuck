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
