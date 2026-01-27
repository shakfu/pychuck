"""Tests for the paths module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from numchuck import paths


class TestGetNumchuckDir:
    """Test get_numchuck_dir function."""

    def test_returns_cwd_numchuck_if_exists(self, tmp_path, monkeypatch):
        """Test that local .numchuck takes precedence."""
        # Create local .numchuck directory
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()

        monkeypatch.chdir(tmp_path)

        result = paths.get_numchuck_dir()

        assert result == local_numchuck

    def test_returns_home_numchuck_if_no_local(self, tmp_path, monkeypatch):
        """Test that home .numchuck is used when no local exists."""
        # No local .numchuck in tmp_path
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.get_numchuck_dir()

        assert result == tmp_path / "fake_home" / ".numchuck"

    def test_local_takes_precedence_over_home(self, tmp_path, monkeypatch):
        """Test that local directory is preferred over home."""
        # Create both local and home .numchuck
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        home_numchuck = tmp_path / "fake_home" / ".numchuck"
        home_numchuck.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.get_numchuck_dir()

        # Should return local, not home
        assert result == local_numchuck


class TestGetNumchuckHome:
    """Test get_numchuck_home function."""

    def test_returns_home_numchuck(self, tmp_path):
        """Test that home .numchuck path is returned."""
        with patch.object(Path, "home", return_value=tmp_path):
            result = paths.get_numchuck_home()

        assert result == tmp_path / ".numchuck"

    def test_ignores_local_numchuck(self, tmp_path, monkeypatch):
        """Test that local .numchuck doesn't affect home path."""
        # Create local .numchuck
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.get_numchuck_home()

        # Should still return home path
        assert result == tmp_path / "fake_home" / ".numchuck"


class TestDirectoryGetters:
    """Test various get_*_dir functions."""

    def test_get_snippets_dir(self, tmp_path, monkeypatch):
        """Test get_snippets_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_snippets_dir()

        assert result == local_numchuck / "snippets"

    def test_get_history_file(self, tmp_path, monkeypatch):
        """Test get_history_file returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_history_file()

        assert result == local_numchuck / "numchuck_history"

    def test_get_sessions_dir(self, tmp_path, monkeypatch):
        """Test get_sessions_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_sessions_dir()

        assert result == local_numchuck / "sessions"

    def test_get_logs_dir(self, tmp_path, monkeypatch):
        """Test get_logs_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_logs_dir()

        assert result == local_numchuck / "logs"

    def test_get_config_file(self, tmp_path, monkeypatch):
        """Test get_config_file returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_config_file()

        assert result == local_numchuck / "config.toml"

    def test_get_projects_dir(self, tmp_path, monkeypatch):
        """Test get_projects_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_projects_dir()

        assert result == local_numchuck / "projects"

    def test_get_recordings_dir(self, tmp_path, monkeypatch):
        """Test get_recordings_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_recordings_dir()

        assert result == local_numchuck / "recordings"

    def test_get_examples_dir(self, tmp_path, monkeypatch):
        """Test get_examples_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_examples_dir()

        assert result == local_numchuck / "examples"

    def test_get_themes_dir(self, tmp_path, monkeypatch):
        """Test get_themes_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_themes_dir()

        assert result == local_numchuck / "themes"

    def test_get_chugins_dir(self, tmp_path, monkeypatch):
        """Test get_chugins_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_chugins_dir()

        assert result == local_numchuck / "chugins"

    def test_get_keybindings_dir(self, tmp_path, monkeypatch):
        """Test get_keybindings_dir returns correct path."""
        local_numchuck = tmp_path / ".numchuck"
        local_numchuck.mkdir()
        monkeypatch.chdir(tmp_path)

        result = paths.get_keybindings_dir()

        assert result == local_numchuck / "keybindings"


class TestEnsureNumchuckDirectories:
    """Test ensure_numchuck_directories function."""

    def test_creates_all_directories(self, tmp_path):
        """Test that all required directories are created."""
        with patch.object(Path, "home", return_value=tmp_path):
            paths.ensure_numchuck_directories()

        numchuck_dir = tmp_path / ".numchuck"
        assert numchuck_dir.exists()
        assert (numchuck_dir / "snippets").exists()
        assert (numchuck_dir / "sessions").exists()
        assert (numchuck_dir / "logs").exists()
        assert (numchuck_dir / "projects").exists()
        assert (numchuck_dir / "recordings").exists()
        assert (numchuck_dir / "examples").exists()
        assert (numchuck_dir / "themes").exists()
        assert (numchuck_dir / "chugins").exists()
        assert (numchuck_dir / "keybindings").exists()

    def test_idempotent_when_directories_exist(self, tmp_path):
        """Test that function is safe to call multiple times."""
        with patch.object(Path, "home", return_value=tmp_path):
            paths.ensure_numchuck_directories()
            # Call again - should not raise
            paths.ensure_numchuck_directories()

        # All directories should still exist
        numchuck_dir = tmp_path / ".numchuck"
        assert numchuck_dir.exists()
        assert (numchuck_dir / "snippets").exists()


class TestListSnippets:
    """Test list_snippets function."""

    def test_returns_empty_when_no_snippets_dir(self, tmp_path, monkeypatch):
        """Test that empty list is returned when snippets dir doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path):
            result = paths.list_snippets()

        assert result == []

    def test_returns_snippet_names_without_extension(self, tmp_path, monkeypatch):
        """Test that snippet names are returned without .ck extension."""
        # Create snippets directory with files
        snippets_dir = tmp_path / ".numchuck" / "snippets"
        snippets_dir.mkdir(parents=True)
        (snippets_dir / "sine.ck").write_text("SinOsc s => dac;")
        (snippets_dir / "noise.ck").write_text("Noise n => dac;")
        (snippets_dir / "readme.txt").write_text("not a snippet")

        monkeypatch.chdir(tmp_path)

        result = paths.list_snippets()

        assert "sine" in result
        assert "noise" in result
        assert "readme" not in result  # .txt files excluded

    def test_returns_sorted_list(self, tmp_path, monkeypatch):
        """Test that snippets are returned in sorted order."""
        snippets_dir = tmp_path / ".numchuck" / "snippets"
        snippets_dir.mkdir(parents=True)
        (snippets_dir / "zebra.ck").write_text("")
        (snippets_dir / "alpha.ck").write_text("")
        (snippets_dir / "beta.ck").write_text("")

        monkeypatch.chdir(tmp_path)

        result = paths.list_snippets()

        assert result == ["alpha", "beta", "zebra"]


class TestGetSnippetPath:
    """Test get_snippet_path function."""

    def test_returns_path_when_snippet_exists(self, tmp_path, monkeypatch):
        """Test that path is returned when snippet exists."""
        snippets_dir = tmp_path / ".numchuck" / "snippets"
        snippets_dir.mkdir(parents=True)
        snippet_file = snippets_dir / "test.ck"
        snippet_file.write_text("SinOsc s => dac;")

        monkeypatch.chdir(tmp_path)

        result = paths.get_snippet_path("test")

        assert result == snippet_file

    def test_returns_none_when_snippet_not_found(self, tmp_path, monkeypatch):
        """Test that None is returned when snippet doesn't exist."""
        snippets_dir = tmp_path / ".numchuck" / "snippets"
        snippets_dir.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        result = paths.get_snippet_path("nonexistent")

        assert result is None


class TestListAllSnippets:
    """Test list_all_snippets function."""

    def test_returns_empty_when_no_snippets(self, tmp_path, monkeypatch):
        """Test empty list when no snippets directories exist."""
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.list_all_snippets()

        assert result == []

    def test_lists_local_snippets(self, tmp_path, monkeypatch):
        """Test that local snippets are listed with 'local' source."""
        local_snippets = tmp_path / ".numchuck" / "snippets"
        local_snippets.mkdir(parents=True)
        (local_snippets / "local_snippet.ck").write_text("")

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.list_all_snippets()

        assert ("local_snippet", "local") in result

    def test_lists_global_snippets(self, tmp_path, monkeypatch):
        """Test that global snippets are listed with 'global' source."""
        global_snippets = tmp_path / "fake_home" / ".numchuck" / "snippets"
        global_snippets.mkdir(parents=True)
        (global_snippets / "global_snippet.ck").write_text("")

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.list_all_snippets()

        assert ("global_snippet", "global") in result

    def test_local_shadows_global_with_same_name(self, tmp_path, monkeypatch):
        """Test that local snippet hides global snippet with same name."""
        # Create both local and global snippet with same name
        local_snippets = tmp_path / ".numchuck" / "snippets"
        local_snippets.mkdir(parents=True)
        (local_snippets / "shared.ck").write_text("local version")

        global_snippets = tmp_path / "fake_home" / ".numchuck" / "snippets"
        global_snippets.mkdir(parents=True)
        (global_snippets / "shared.ck").write_text("global version")

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            result = paths.list_all_snippets()

        # Should only have local version
        shared_entries = [r for r in result if r[0] == "shared"]
        assert len(shared_entries) == 1
        assert shared_entries[0] == ("shared", "local")


class TestGetSnippetPathWithSource:
    """Test get_snippet_path_with_source function."""

    def test_returns_local_snippet_first(self, tmp_path, monkeypatch):
        """Test that local snippet is preferred over global."""
        # Create both local and global
        local_snippets = tmp_path / ".numchuck" / "snippets"
        local_snippets.mkdir(parents=True)
        local_file = local_snippets / "test.ck"
        local_file.write_text("local")

        global_snippets = tmp_path / "fake_home" / ".numchuck" / "snippets"
        global_snippets.mkdir(parents=True)
        (global_snippets / "test.ck").write_text("global")

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            path, source = paths.get_snippet_path_with_source("test")

        assert path == local_file
        assert source == "local"

    def test_returns_global_when_no_local(self, tmp_path, monkeypatch):
        """Test that global snippet is returned when no local exists."""
        global_snippets = tmp_path / "fake_home" / ".numchuck" / "snippets"
        global_snippets.mkdir(parents=True)
        global_file = global_snippets / "test.ck"
        global_file.write_text("global")

        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            path, source = paths.get_snippet_path_with_source("test")

        assert path == global_file
        assert source == "global"

    def test_returns_none_when_not_found(self, tmp_path, monkeypatch):
        """Test that (None, None) is returned when snippet not found."""
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path / "fake_home"):
            path, source = paths.get_snippet_path_with_source("nonexistent")

        assert path is None
        assert source is None


class TestListProjects:
    """Test list_projects function."""

    def test_returns_empty_when_no_projects_dir(self, tmp_path, monkeypatch):
        """Test empty list when projects directory doesn't exist."""
        monkeypatch.chdir(tmp_path)

        with patch.object(Path, "home", return_value=tmp_path):
            result = paths.list_projects()

        assert result == []

    def test_returns_project_directory_names(self, tmp_path, monkeypatch):
        """Test that project directory names are returned."""
        projects_dir = tmp_path / ".numchuck" / "projects"
        projects_dir.mkdir(parents=True)
        (projects_dir / "project1").mkdir()
        (projects_dir / "project2").mkdir()
        (projects_dir / "not_a_project.txt").write_text("")  # File, not dir

        monkeypatch.chdir(tmp_path)

        result = paths.list_projects()

        assert "project1" in result
        assert "project2" in result
        assert "not_a_project.txt" not in result


class TestCreateProject:
    """Test create_project function."""

    def test_creates_project_directory(self, tmp_path, monkeypatch):
        """Test that project directory is created."""
        numchuck_dir = tmp_path / ".numchuck"
        numchuck_dir.mkdir()

        monkeypatch.chdir(tmp_path)

        result = paths.create_project("my_project")

        assert result.exists()
        assert result.name == "my_project"
        assert result.parent.name == "projects"


class TestGetProjectPath:
    """Test get_project_path function."""

    def test_returns_project_path(self, tmp_path, monkeypatch):
        """Test that correct project path is returned."""
        numchuck_dir = tmp_path / ".numchuck"
        numchuck_dir.mkdir()

        monkeypatch.chdir(tmp_path)

        result = paths.get_project_path("my_project")

        assert result == numchuck_dir / "projects" / "my_project"
