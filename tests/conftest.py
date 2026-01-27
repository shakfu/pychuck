"""Pytest configuration and fixtures."""

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
