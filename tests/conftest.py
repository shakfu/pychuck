"""Pytest configuration and fixtures."""

import sys

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "realtime: marks tests requiring real audio hardware (skipped on CI)"
    )
    config.addinivalue_line(
        "markers", "asyncio: marks tests as async"
    )
    config.addinivalue_line(
        "markers", "tui: marks tests requiring a terminal/console (skipped on CI)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip TUI tests on Windows due to prompt_toolkit console issues."""
    if sys.platform == "win32":
        skip_tui = pytest.mark.skip(reason="TUI tests not supported on Windows")
        for item in items:
            if "tui" in item.keywords:
                item.add_marker(skip_tui)
