"""
Reusable TUI widget factory functions.

Provides factory functions for creating common UI components
that can be used across different applications (REPL, editor).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.widgets import TextArea

if TYPE_CHECKING:
    pass


def create_help_window(
    show_condition: Callable[[], bool],
    help_text: str,
    min_height: int = 10,
    max_height: int = 30,
) -> ConditionalContainer:
    """Create a help window that shows/hides based on a condition.

    Args:
        show_condition: Callable returning True when window should be visible
        help_text: Text content for help window
        min_height: Minimum height of the window
        max_height: Maximum height of the window

    Returns:
        ConditionalContainer with help window
    """
    help_area = TextArea(
        text=help_text,
        scrollbar=True,
        focusable=False,
        read_only=True,
        wrap_lines=True,
    )

    return ConditionalContainer(
        Window(
            content=help_area.control,
            height=D(min=min_height, max=max_height),
            wrap_lines=True,
        ),
        filter=Condition(show_condition),
    )


def create_shreds_table(
    show_condition: Callable[[], bool],
    get_table_text: Callable[[], str],
    min_height: int = 5,
    max_height: int = 15,
) -> ConditionalContainer:
    """Create a shreds table that shows/hides based on a condition.

    Args:
        show_condition: Callable returning True when table should be visible
        get_table_text: Callable returning the formatted table text
        min_height: Minimum height of the table
        max_height: Maximum height of the table

    Returns:
        ConditionalContainer with shreds table
    """
    return ConditionalContainer(
        Window(
            content=FormattedTextControl(get_table_text),
            height=D(min=min_height, max=max_height),
        ),
        filter=Condition(show_condition),
    )


def create_log_window(
    show_condition: Callable[[], bool],
    log_area: TextArea | None = None,
) -> tuple[ConditionalContainer, TextArea]:
    """Create a log window that shows/hides based on a condition.

    Args:
        show_condition: Callable returning True when log should be visible
        log_area: Optional pre-created TextArea. If None, creates one.

    Returns:
        Tuple of (ConditionalContainer, TextArea) for the log window
    """
    if log_area is None:
        log_area = TextArea(
            text="",
            scrollbar=True,
            focusable=False,
            read_only=True,
        )

    container = ConditionalContainer(
        log_area,
        filter=Condition(show_condition),
    )

    return container, log_area


def create_status_bar(
    status_text_func: Callable[[], str],
    style: str = "bg:#444444 fg:#ffffff",
) -> Window:
    """Create a status bar at the bottom of the screen.

    Args:
        status_text_func: Function returning status bar text
        style: Style string for the status bar

    Returns:
        Window with status bar
    """
    return Window(
        content=FormattedTextControl(status_text_func),
        height=1,
        style=style,
    )


def create_message_area(
    initial_text: str = "",
    read_only: bool = True,
    scrollbar: bool = True,
) -> TextArea:
    """Create a text area for displaying messages.

    Args:
        initial_text: Initial text content
        read_only: Whether the area is read-only
        scrollbar: Whether to show scrollbar

    Returns:
        TextArea for messages
    """
    return TextArea(
        text=initial_text,
        read_only=read_only,
        scrollbar=scrollbar,
        focusable=False,
    )
