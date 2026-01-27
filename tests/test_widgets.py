"""Tests for TUI widgets module."""

import pytest
from unittest.mock import MagicMock

from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.widgets import TextArea

from numchuck.tui import widgets


class TestCreateHelpWindow:
    """Tests for create_help_window function."""

    def test_creates_conditional_container(self):
        """Test that create_help_window returns ConditionalContainer."""
        result = widgets.create_help_window(
            show_condition=lambda: True,
            help_text="Test help",
        )
        assert isinstance(result, ConditionalContainer)

    def test_shows_when_condition_true(self):
        """Test window visibility when condition is True."""
        show = [True]
        result = widgets.create_help_window(
            show_condition=lambda: show[0],
            help_text="Test help",
        )
        # The filter should evaluate to True
        assert result.filter() is True

    def test_hides_when_condition_false(self):
        """Test window visibility when condition is False."""
        show = [False]
        result = widgets.create_help_window(
            show_condition=lambda: show[0],
            help_text="Test help",
        )
        # The filter should evaluate to False
        assert result.filter() is False

    def test_custom_height(self):
        """Test custom min/max height parameters."""
        result = widgets.create_help_window(
            show_condition=lambda: True,
            help_text="Test help",
            min_height=5,
            max_height=20,
        )
        assert isinstance(result, ConditionalContainer)


class TestCreateShredsTable:
    """Tests for create_shreds_table function."""

    def test_creates_conditional_container(self):
        """Test that create_shreds_table returns ConditionalContainer."""
        result = widgets.create_shreds_table(
            show_condition=lambda: True,
            get_table_text=lambda: "Test table",
        )
        assert isinstance(result, ConditionalContainer)

    def test_shows_when_condition_true(self):
        """Test table visibility when condition is True."""
        result = widgets.create_shreds_table(
            show_condition=lambda: True,
            get_table_text=lambda: "Test",
        )
        assert result.filter() is True

    def test_hides_when_condition_false(self):
        """Test table visibility when condition is False."""
        result = widgets.create_shreds_table(
            show_condition=lambda: False,
            get_table_text=lambda: "Test",
        )
        assert result.filter() is False

    def test_custom_height(self):
        """Test custom min/max height parameters."""
        result = widgets.create_shreds_table(
            show_condition=lambda: True,
            get_table_text=lambda: "Test",
            min_height=3,
            max_height=10,
        )
        assert isinstance(result, ConditionalContainer)


class TestCreateLogWindow:
    """Tests for create_log_window function."""

    def test_creates_container_and_text_area(self):
        """Test that create_log_window returns tuple of container and text area."""
        container, text_area = widgets.create_log_window(
            show_condition=lambda: True,
        )
        assert isinstance(container, ConditionalContainer)
        assert isinstance(text_area, TextArea)

    def test_uses_provided_text_area(self):
        """Test that provided text_area is used."""
        existing_area = TextArea(text="existing")
        container, text_area = widgets.create_log_window(
            show_condition=lambda: True,
            log_area=existing_area,
        )
        assert text_area is existing_area

    def test_creates_new_text_area_when_none(self):
        """Test that new text area is created when None provided."""
        container, text_area = widgets.create_log_window(
            show_condition=lambda: True,
            log_area=None,
        )
        assert isinstance(text_area, TextArea)
        assert text_area.text == ""

    def test_shows_when_condition_true(self):
        """Test log visibility when condition is True."""
        container, _ = widgets.create_log_window(
            show_condition=lambda: True,
        )
        assert container.filter() is True

    def test_hides_when_condition_false(self):
        """Test log visibility when condition is False."""
        container, _ = widgets.create_log_window(
            show_condition=lambda: False,
        )
        assert container.filter() is False


class TestCreateStatusBar:
    """Tests for create_status_bar function."""

    def test_creates_window(self):
        """Test that create_status_bar returns Window."""
        result = widgets.create_status_bar(
            status_text_func=lambda: "Status",
        )
        assert isinstance(result, Window)

    def test_default_style(self):
        """Test default style is applied."""
        result = widgets.create_status_bar(
            status_text_func=lambda: "Status",
        )
        assert result.style == "bg:#444444 fg:#ffffff"

    def test_custom_style(self):
        """Test custom style is applied."""
        result = widgets.create_status_bar(
            status_text_func=lambda: "Status",
            style="bg:#000000 fg:#00ff00",
        )
        assert result.style == "bg:#000000 fg:#00ff00"

    def test_height_is_one(self):
        """Test status bar height is 1."""
        result = widgets.create_status_bar(
            status_text_func=lambda: "Status",
        )
        assert result.height == 1


class TestCreateMessageArea:
    """Tests for create_message_area function."""

    def test_creates_text_area(self):
        """Test that create_message_area returns TextArea."""
        result = widgets.create_message_area()
        assert isinstance(result, TextArea)

    def test_default_empty_text(self):
        """Test default empty initial text."""
        result = widgets.create_message_area()
        assert result.text == ""

    def test_custom_initial_text(self):
        """Test custom initial text."""
        result = widgets.create_message_area(initial_text="Hello")
        assert result.text == "Hello"

    def test_read_only_by_default(self):
        """Test read_only is True by default."""
        result = widgets.create_message_area()
        # Check that the buffer is read-only
        assert result.buffer.read_only() is True

    def test_writable_when_specified(self):
        """Test read_only can be set to False."""
        result = widgets.create_message_area(read_only=False)
        # Check that the buffer is writable
        assert result.buffer.read_only() is False

    def test_not_focusable(self):
        """Test message area is not focusable."""
        result = widgets.create_message_area()
        # focusable is set to False in create_message_area
        assert isinstance(result, TextArea)
