"""Tests for the packages module."""

import pytest


def test_chump_import():
    """Test that _chump module can be imported."""
    try:
        from numchuck import _chump

        assert hasattr(_chump, "ChumpManager")
        assert hasattr(_chump, "PackageInfo")
        assert hasattr(_chump, "packages_dir")
        assert hasattr(_chump, "which_os")
        assert hasattr(_chump, "which_arch")
    except ImportError:
        pytest.skip("_chump module not built")


def test_packages_module_import():
    """Test that packages module can be imported."""
    try:
        from numchuck import packages

        assert hasattr(packages, "Package")
        assert hasattr(packages, "PackageManager")
        assert hasattr(packages, "packages_dir")
        assert hasattr(packages, "which_os")
        assert hasattr(packages, "which_arch")
    except ImportError:
        pytest.skip("packages module dependencies not available")


def test_which_os():
    """Test which_os returns a valid OS name."""
    try:
        from numchuck import _chump

        os_name = _chump.which_os()
        assert os_name in ("mac", "linux", "windows")
    except ImportError:
        pytest.skip("_chump module not built")


def test_which_arch():
    """Test which_arch returns a valid architecture name."""
    try:
        from numchuck import _chump

        arch = _chump.which_arch()
        assert arch in ("all", "x86", "x86_64", "arm64", "universal")
    except ImportError:
        pytest.skip("_chump module not built")


def test_packages_dir():
    """Test packages_dir returns a path string."""
    try:
        from numchuck import _chump

        path = _chump.packages_dir()
        assert isinstance(path, str)
        assert len(path) > 0
        # Should contain 'chuck' or 'ChucK' in the path
        assert "chuck" in path.lower()
    except ImportError:
        pytest.skip("_chump module not built")


def test_package_info_attributes():
    """Test PackageInfo has expected attributes."""
    try:
        from numchuck._chump import PackageInfo

        # PackageInfo is created by C++, we just test the class exists
        # and has the expected attribute accessors
        assert hasattr(PackageInfo, "name")
        assert hasattr(PackageInfo, "authors")
        assert hasattr(PackageInfo, "description")
        assert hasattr(PackageInfo, "installed")
    except ImportError:
        pytest.skip("_chump module not built")


def test_chump_manager_creation():
    """Test ChumpManager can be created."""
    try:
        from numchuck._chump import ChumpManager

        # This may fail if network is unavailable, but the class should exist
        manager = ChumpManager()
        assert manager is not None
        assert hasattr(manager, "list_packages")
        assert hasattr(manager, "get_package")
        assert hasattr(manager, "install")
        assert hasattr(manager, "uninstall")
        assert hasattr(manager, "update")
        assert hasattr(manager, "is_installed")
        assert hasattr(manager, "install_path")
        assert hasattr(manager, "packages_dir")
        assert hasattr(manager, "chuck_version")
    except ImportError:
        pytest.skip("_chump module not built")
    except RuntimeError:
        # May fail if network unavailable during manifest download
        pytest.skip("ChumpManager initialization failed (network issue?)")


def test_package_manager_python_wrapper():
    """Test PackageManager Python wrapper."""
    try:
        from numchuck.packages import PackageManager

        pm = PackageManager()
        assert pm is not None
        assert hasattr(pm, "list_packages")
        assert hasattr(pm, "get_package")
        assert hasattr(pm, "install")
        assert hasattr(pm, "uninstall")
        assert hasattr(pm, "update")
        assert hasattr(pm, "search")
        assert hasattr(pm, "is_installed")
        assert hasattr(pm, "packages_dir")
        assert hasattr(pm, "chuck_version")
    except ImportError:
        pytest.skip("packages module not available")
    except RuntimeError:
        pytest.skip("PackageManager initialization failed")


def test_package_dataclass():
    """Test Package dataclass."""
    try:
        from numchuck.packages import Package

        # Create a Package directly
        pkg = Package(
            name="TestPkg",
            authors=["Test Author"],
            description="Test description",
            homepage="https://example.com",
            repository="https://github.com/example/test",
            license="MIT",
            keywords=["test", "example"],
            installed=False,
            installed_version=None,
            latest_version="1.0.0",
        )

        assert pkg.name == "TestPkg"
        assert pkg.authors == ["Test Author"]
        assert pkg.description == "Test description"
        assert pkg.installed is False
        assert pkg.installed_version is None
        assert pkg.latest_version == "1.0.0"
        assert "TestPkg" in repr(pkg)
    except ImportError:
        pytest.skip("packages module not available")


def test_package_manager_list_packages():
    """Test listing packages."""
    try:
        from numchuck.packages import PackageManager

        pm = PackageManager()
        packages = pm.list_packages()

        # Should return a list (may be empty if no network)
        assert isinstance(packages, list)

        # If we have packages, check their structure
        if packages:
            pkg = packages[0]
            assert hasattr(pkg, "name")
            assert hasattr(pkg, "description")
            assert hasattr(pkg, "installed")
    except ImportError:
        pytest.skip("packages module not available")
    except RuntimeError:
        pytest.skip("PackageManager initialization failed")


def test_package_manager_search():
    """Test searching packages."""
    try:
        from numchuck.packages import PackageManager

        pm = PackageManager()

        # Search for a term that might exist
        results = pm.search("audio")

        # Should return a list (may be empty)
        assert isinstance(results, list)
    except ImportError:
        pytest.skip("packages module not available")
    except RuntimeError:
        pytest.skip("PackageManager initialization failed")


def test_cli_packages_parser():
    """Test CLI argument parsing for pkg commands."""
    try:
        from numchuck import _chump  # noqa: F401
    except ImportError:
        pytest.skip("_chump module not built - pkg subcommand not available")

    from numchuck.cli.main import create_parser

    parser = create_parser()

    # Test pkg list
    args = parser.parse_args(["pkg", "list"])
    assert args.command == "pkg"
    assert args.pkg_command == "list"

    # Test pkg list --installed
    args = parser.parse_args(["pkg", "list", "--installed"])
    assert args.installed is True

    # Test pkg info
    args = parser.parse_args(["pkg", "info", "TestPackage"])
    assert args.pkg_command == "info"
    assert args.name == "TestPackage"

    # Test pkg install
    args = parser.parse_args(["pkg", "install", "TestPackage@1.0.0"])
    assert args.pkg_command == "install"
    assert args.package == "TestPackage@1.0.0"

    # Test pkg uninstall
    args = parser.parse_args(["pkg", "uninstall", "TestPackage"])
    assert args.pkg_command == "uninstall"
    assert args.name == "TestPackage"

    # Test pkg uninstall --force
    args = parser.parse_args(["pkg", "uninstall", "--force", "TestPackage"])
    assert args.force is True

    # Test pkg update (all)
    args = parser.parse_args(["pkg", "update"])
    assert args.pkg_command == "update"
    assert args.name is None

    # Test pkg update (specific)
    args = parser.parse_args(["pkg", "update", "TestPackage"])
    assert args.name == "TestPackage"

    # Test pkg refresh
    args = parser.parse_args(["pkg", "refresh"])
    assert args.pkg_command == "refresh"

    # Test pkg search
    args = parser.parse_args(["pkg", "search", "audio"])
    assert args.pkg_command == "search"
    assert args.query == "audio"

    # Test pkg path
    args = parser.parse_args(["pkg", "path"])
    assert args.pkg_command == "path"
