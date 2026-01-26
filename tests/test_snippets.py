"""Tests for snippet functionality."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from numchuck.cli.snippets import get_snippet_info
from numchuck.paths import (
    get_snippet_path,
    get_snippet_path_with_source,
    list_all_snippets,
    list_snippets,
)


class TestSnippetPaths:
    """Tests for snippet path functions."""

    def test_list_snippets_empty_dir(self, tmp_path: Path) -> None:
        """Test listing snippets in empty directory."""
        with patch("numchuck.paths.get_snippets_dir", return_value=tmp_path):
            snippets = list_snippets()
            assert snippets == []

    def test_list_snippets_with_files(self, tmp_path: Path) -> None:
        """Test listing snippets finds .ck files."""
        (tmp_path / "sine.ck").write_text("// sine")
        (tmp_path / "drum.ck").write_text("// drum")
        (tmp_path / "readme.txt").write_text("ignore me")

        with patch("numchuck.paths.get_snippets_dir", return_value=tmp_path):
            snippets = list_snippets()
            assert sorted(snippets) == ["drum", "sine"]

    def test_list_snippets_nonexistent_dir(self, tmp_path: Path) -> None:
        """Test listing snippets in nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"
        with patch("numchuck.paths.get_snippets_dir", return_value=nonexistent):
            snippets = list_snippets()
            assert snippets == []

    def test_get_snippet_path_exists(self, tmp_path: Path) -> None:
        """Test getting path for existing snippet."""
        (tmp_path / "sine.ck").write_text("// sine")

        with patch("numchuck.paths.get_snippets_dir", return_value=tmp_path):
            path = get_snippet_path("sine")
            assert path is not None
            assert path.exists()

    def test_get_snippet_path_not_exists(self, tmp_path: Path) -> None:
        """Test getting path for nonexistent snippet."""
        with patch("numchuck.paths.get_snippets_dir", return_value=tmp_path):
            path = get_snippet_path("nonexistent")
            assert path is None


class TestLocalGlobalPrecedence:
    """Tests for local vs global snippet precedence."""

    def test_local_snippet_takes_precedence(self, tmp_path: Path) -> None:
        """Test that local snippets take precedence over global."""
        local_dir = tmp_path / "local" / ".numchuck" / "snippets"
        global_dir = tmp_path / "global" / ".numchuck" / "snippets"
        local_dir.mkdir(parents=True)
        global_dir.mkdir(parents=True)

        (local_dir / "test.ck").write_text("// local version")
        (global_dir / "test.ck").write_text("// global version")

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path / "local"), patch(
            "numchuck.paths.Path.home", return_value=tmp_path / "global"
        ):
            path, source = get_snippet_path_with_source("test")
            assert source == "local"
            assert "local version" in path.read_text()

    def test_global_snippet_when_no_local(self, tmp_path: Path) -> None:
        """Test that global snippet is found when no local exists."""
        local_dir = tmp_path / "local" / ".numchuck" / "snippets"
        global_dir = tmp_path / "global" / ".numchuck" / "snippets"
        local_dir.mkdir(parents=True)
        global_dir.mkdir(parents=True)

        # Only global has the snippet
        (global_dir / "test.ck").write_text("// global version")

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path / "local"), patch(
            "numchuck.paths.Path.home", return_value=tmp_path / "global"
        ):
            path, source = get_snippet_path_with_source("test")
            assert source == "global"
            assert "global version" in path.read_text()

    def test_snippet_not_found(self, tmp_path: Path) -> None:
        """Test that nonexistent snippet returns None."""
        local_dir = tmp_path / "local" / ".numchuck" / "snippets"
        global_dir = tmp_path / "global" / ".numchuck" / "snippets"
        local_dir.mkdir(parents=True)
        global_dir.mkdir(parents=True)

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path / "local"), patch(
            "numchuck.paths.Path.home", return_value=tmp_path / "global"
        ):
            path, source = get_snippet_path_with_source("nonexistent")
            assert path is None
            assert source is None


class TestListAllSnippets:
    """Tests for listing all snippets from both sources."""

    def test_list_all_snippets_combines_sources(self, tmp_path: Path) -> None:
        """Test that list_all_snippets combines local and global."""
        local_dir = tmp_path / "local" / ".numchuck" / "snippets"
        global_dir = tmp_path / "global" / ".numchuck" / "snippets"
        local_dir.mkdir(parents=True)
        global_dir.mkdir(parents=True)

        (local_dir / "local_only.ck").write_text("// local")
        (global_dir / "global_only.ck").write_text("// global")

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path / "local"), patch(
            "numchuck.paths.Path.home", return_value=tmp_path / "global"
        ):
            snippets = list_all_snippets()
            names = [name for name, source in snippets]
            assert "local_only" in names
            assert "global_only" in names

    def test_list_all_snippets_local_overrides_global(self, tmp_path: Path) -> None:
        """Test that local snippet overrides global with same name."""
        local_dir = tmp_path / "local" / ".numchuck" / "snippets"
        global_dir = tmp_path / "global" / ".numchuck" / "snippets"
        local_dir.mkdir(parents=True)
        global_dir.mkdir(parents=True)

        (local_dir / "shared.ck").write_text("// local")
        (global_dir / "shared.ck").write_text("// global")

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path / "local"), patch(
            "numchuck.paths.Path.home", return_value=tmp_path / "global"
        ):
            snippets = list_all_snippets()
            # Should only appear once, as local
            shared_entries = [(n, s) for n, s in snippets if n == "shared"]
            assert len(shared_entries) == 1
            assert shared_entries[0][1] == "local"


class TestCLISnippets:
    """Tests for CLI snippet functions."""

    def test_get_snippet_info_existing(self, tmp_path: Path) -> None:
        """Test getting info for existing snippet."""
        snippets_dir = tmp_path / ".numchuck" / "snippets"
        snippets_dir.mkdir(parents=True)
        (snippets_dir / "test.ck").write_text("// test snippet\nSinOsc s => dac;")

        with patch("numchuck.paths.Path.cwd", return_value=tmp_path), patch(
            "numchuck.paths.Path.home", return_value=tmp_path
        ):
            info = get_snippet_info("test")
            assert info is not None
            assert info["source"] in ("local", "global")
            assert "SinOsc" in info["content"]

    def test_get_snippet_info_nonexistent(self, tmp_path: Path) -> None:
        """Test getting info for nonexistent snippet."""
        with patch("numchuck.paths.Path.cwd", return_value=tmp_path), patch(
            "numchuck.paths.Path.home", return_value=tmp_path
        ):
            info = get_snippet_info("nonexistent_xyz")
            assert info is None


class TestSnippetCompilation:
    """Tests for compiling snippets."""

    def test_snippet_compiles_successfully(self, tmp_path: Path) -> None:
        """Test that a valid snippet compiles without error."""
        from numchuck.api import Chuck

        snippet_content = """
// Simple test snippet
SinOsc s => dac;
440.0 => s.freq;
1::second => now;
"""
        snippet_file = tmp_path / "test.ck"
        snippet_file.write_text(snippet_content)

        chuck = Chuck()
        try:
            success, shred_ids = chuck.compile_file(str(snippet_file))
            assert success, "Snippet failed to compile"
            assert len(shred_ids) > 0, "Snippet created no shreds"
        finally:
            chuck.close()

    def test_invalid_snippet_fails_compilation(self, tmp_path: Path) -> None:
        """Test that invalid snippet fails to compile."""
        from numchuck.api import Chuck

        snippet_file = tmp_path / "invalid.ck"
        snippet_file.write_text("this is not valid ChucK code !!!")

        chuck = Chuck()
        try:
            success, shred_ids = chuck.compile_file(str(snippet_file))
            assert not success, "Invalid snippet should not compile"
        finally:
            chuck.close()
