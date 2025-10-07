"""
Tests for project versioning system.

Tests the versioning scheme:
- file.ck → file-1.ck (spork)
- file-1.ck → file-1-1.ck (first replace)
- file-1-1.ck → file-1-2.ck (second replace)
"""
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_projects_dir():
    """Create temporary directory for projects."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir)


def test_project_creation(temp_projects_dir):
    """Test project creation."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)
    assert project.project_dir.exists()
    assert project.name == "test"
    assert project.project_dir == temp_projects_dir / "test"


def test_spork_versioning(temp_projects_dir):
    """Test file versioning on spork."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)

    # First spork creates file-1.ck
    path1 = project.save_on_spork("myfile.ck", "// code v1", 1)
    assert path1.name == "myfile-1.ck"
    assert path1.exists()
    assert path1.read_text() == "// code v1"

    # Second spork of same file creates file-2.ck
    path2 = project.save_on_spork("myfile.ck", "// code v2", 2)
    assert path2.name == "myfile-2.ck"
    assert path2.exists()
    assert path2.read_text() == "// code v2"

    # Both files should exist
    assert path1.exists()
    assert path2.exists()


def test_replace_versioning(temp_projects_dir):
    """Test file versioning on replace."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)

    # Spork creates file-1.ck
    project.save_on_spork("myfile.ck", "// original", 1)

    # First replace creates file-1-1.ck
    path1 = project.save_on_replace(1, "// replace 1")
    assert path1.name == "myfile-1-1.ck"
    assert path1.exists()
    assert path1.read_text() == "// replace 1"

    # Second replace creates file-1-2.ck
    path2 = project.save_on_replace(1, "// replace 2")
    assert path2.name == "myfile-1-2.ck"
    assert path2.exists()
    assert path2.read_text() == "// replace 2"

    # Third replace creates file-1-3.ck
    path3 = project.save_on_replace(1, "// replace 3")
    assert path3.name == "myfile-1-3.ck"
    assert path3.exists()


def test_replace_nonexistent_shred(temp_projects_dir):
    """Test replace with nonexistent shred raises error."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)

    with pytest.raises(ValueError, match="Shred 99 not found"):
        project.save_on_replace(99, "// code")


def test_original_file_save(temp_projects_dir):
    """Test saving original file without versioning."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)

    path = project.save_original("test.ck", "// original")
    assert path.name == "test.ck"
    assert path.exists()
    assert path.read_text() == "// original"


def test_list_versions(temp_projects_dir):
    """Test listing all versions in project."""
    from pychuck.tui.project import Project

    project = Project("test", temp_projects_dir)

    # Create some versioned files
    project.save_on_spork("file1.ck", "// f1v1", 1)
    project.save_on_replace(1, "// f1v2")
    project.save_on_spork("file2.ck", "// f2v1", 2)

    versions = project.list_versions()
    assert len(versions) == 3

    # Check filenames
    names = [v.name for v in versions]
    assert "file1-1.ck" in names
    assert "file1-1-1.ck" in names
    assert "file2-2.ck" in names


def test_get_timeline(temp_projects_dir):
    """Test getting chronological timeline."""
    from pychuck.tui.project import Project
    import time

    project = Project("test", temp_projects_dir)

    # Create files with slight delay to ensure different mtimes
    project.save_on_spork("file1.ck", "// 1", 1)
    time.sleep(0.01)
    project.save_on_replace(1, "// 2")
    time.sleep(0.01)
    project.save_on_spork("file2.ck", "// 3", 2)

    timeline = project.get_timeline()
    assert len(timeline) == 3

    # Should be sorted by mtime
    mtimes = [entry['mtime'] for entry in timeline]
    assert mtimes == sorted(mtimes)

    # Check structure
    assert timeline[0]['filename'] == "file1-1.ck"
    assert timeline[0]['shred_id'] == 1
    assert timeline[0]['replace_version'] is None

    assert timeline[1]['filename'] == "file1-1-1.ck"
    assert timeline[1]['shred_id'] == 1
    assert timeline[1]['replace_version'] == 1


def test_project_version_parsing(temp_projects_dir):
    """Test parsing version info from filenames."""
    from pychuck.tui.project import ProjectVersion

    # Test base file
    v1 = ProjectVersion.from_filename("myfile.ck")
    assert v1.base_name == "myfile.ck"
    assert v1.shred_id is None
    assert v1.replace_version is None

    # Test sporked file
    v2 = ProjectVersion.from_filename("myfile-1.ck")
    assert v2.base_name == "myfile.ck"
    assert v2.shred_id == 1
    assert v2.replace_version is None

    # Test replaced file
    v3 = ProjectVersion.from_filename("myfile-1-2.ck")
    assert v3.base_name == "myfile.ck"
    assert v3.shred_id == 1
    assert v3.replace_version == 2


def test_project_version_filename_generation():
    """Test generating filenames from version info."""
    from pychuck.tui.project import ProjectVersion

    # Base file
    v1 = ProjectVersion("test.ck", None, None)
    assert v1.filename() == "test.ck"

    # Sporked
    v2 = ProjectVersion("test.ck", 1, None)
    assert v2.filename() == "test-1.ck"

    # Replaced
    v3 = ProjectVersion("test.ck", 1, 2)
    assert v3.filename() == "test-1-2.ck"


def test_project_version_next_replace():
    """Test getting next replacement version."""
    from pychuck.tui.project import ProjectVersion

    # First replace
    v1 = ProjectVersion("test.ck", 1, None)
    v2 = v1.next_replace()
    assert v2.replace_version == 1
    assert v2.filename() == "test-1-1.ck"

    # Second replace
    v3 = v2.next_replace()
    assert v3.replace_version == 2
    assert v3.filename() == "test-1-2.ck"
