"""
ChucK package management interface.

This module provides a Pythonic interface to the chump package manager,
allowing you to install, update, and manage ChucK packages.

Example:
    >>> from numchuck.packages import PackageManager
    >>> pm = PackageManager()
    >>> packages = pm.list_packages()
    >>> pm.install("Patch")
    True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


@dataclass
class Package:
    """Represents a ChucK package.

    Attributes:
        name: Package name
        authors: List of package authors
        description: Package description
        homepage: Package homepage URL
        repository: Package repository URL
        license: Package license
        keywords: List of package keywords
        installed: Whether the package is installed
        installed_version: Currently installed version (if installed)
        latest_version: Latest available version
    """

    name: str
    authors: list[str]
    description: str
    homepage: str
    repository: str
    license: str
    keywords: list[str]
    installed: bool
    installed_version: str | None
    latest_version: str | None

    @classmethod
    def _from_info(cls, info: "Any") -> Package:
        """Create a Package from a _chump.PackageInfo object."""
        return cls(
            name=info.name,
            authors=list(info.authors),
            description=info.description,
            homepage=info.homepage,
            repository=info.repository,
            license=info.license,
            keywords=list(info.keywords),
            installed=info.installed,
            installed_version=info.installed_version,
            latest_version=info.latest_version,
        )

    def __repr__(self) -> str:
        status = "installed" if self.installed else "available"
        version = self.installed_version or self.latest_version or "?"
        return f"<Package '{self.name}' {version} ({status})>"


class PackageManager:
    """Python interface to the chump package manager.

    Provides methods for listing, installing, updating, and uninstalling
    ChucK packages.

    Example:
        >>> pm = PackageManager()
        >>> pm.list_packages()
        [<Package 'Patch' 1.0.0 (available)>, ...]
        >>> pm.install("Patch")
        True
        >>> pm.is_installed("Patch")
        True
    """

    def __init__(self) -> None:
        """Initialize the package manager.

        This creates a connection to the chump package system and will
        attempt to update the package manifest from the server.
        """
        from . import _chump, _numchuck

        # Get ChucK version from the bundled library
        chuck_version = _numchuck.version()
        # API version for ChucK 1.5.x is typically 10.x
        # Use reasonable defaults that work with most packages
        self._manager = _chump.ChumpManager(chuck_version, 10, 3)

    def list_packages(self, installed_only: bool = False) -> list[Package]:
        """List all available and/or installed packages.

        Args:
            installed_only: If True, only return installed packages

        Returns:
            List of Package objects
        """
        packages = [Package._from_info(p) for p in self._manager.list_packages()]

        if installed_only:
            packages = [p for p in packages if p.installed]

        return packages

    def get_package(self, name: str) -> Package | None:
        """Get information about a specific package.

        Args:
            name: Package name

        Returns:
            Package object if found, None otherwise
        """
        info = self._manager.get_package(name)
        if info is None:
            return None
        return Package._from_info(info)

    def install(self, name: str, version: str | None = None) -> bool:
        """Install a package.

        Args:
            name: Package name
            version: Specific version to install (optional)

        Returns:
            True if installation succeeded, False otherwise
        """
        package_spec = f"{name}={version}" if version else name
        return self._manager.install(package_spec)

    def uninstall(self, name: str, force: bool = False) -> bool:
        """Uninstall a package.

        Args:
            name: Package name
            force: If True, force removal even if files have been modified

        Returns:
            True if uninstallation succeeded, False otherwise
        """
        return self._manager.uninstall(name, force)

    def update(self, name: str | None = None) -> bool:
        """Update a package or all packages.

        Args:
            name: Package name to update, or None to update all installed packages

        Returns:
            True if update succeeded, False otherwise
        """
        if name is None:
            # Update all installed packages
            packages = self.list_packages(installed_only=True)
            success = True
            for pkg in packages:
                if not self._manager.update(pkg.name):
                    success = False
            return success
        return self._manager.update(name)

    def update_manifest(self) -> bool:
        """Update the package manifest from the server.

        Returns:
            True if the manifest was updated, False if already up-to-date
        """
        return self._manager.update_manifest()

    def is_installed(self, name: str) -> bool:
        """Check if a package is installed.

        Args:
            name: Package name

        Returns:
            True if installed, False otherwise
        """
        return self._manager.is_installed(name)

    def install_path(self, name: str) -> str:
        """Get the installation path for a package.

        Args:
            name: Package name

        Returns:
            Path to the package installation directory

        Raises:
            RuntimeError: If package is not found
        """
        return self._manager.install_path(name)

    @property
    def packages_dir(self) -> str:
        """Get the packages directory path."""
        return self._manager.packages_dir()

    @property
    def chuck_version(self) -> str:
        """Get the ChucK version used for package compatibility."""
        return self._manager.chuck_version()

    def search(self, query: str) -> list[Package]:
        """Search for packages by name, description, or keywords.

        Args:
            query: Search query string

        Returns:
            List of matching packages
        """
        query_lower = query.lower()
        packages = self.list_packages()
        results = []

        for pkg in packages:
            # Search in name, description, and keywords
            if query_lower in pkg.name.lower():
                results.append(pkg)
            elif query_lower in pkg.description.lower():
                results.append(pkg)
            elif any(query_lower in kw.lower() for kw in pkg.keywords):
                results.append(pkg)

        return results


def packages_dir() -> str:
    """Get the default packages directory path.

    Returns:
        Path to the packages directory (~/.chuck/packages on Unix,
        Documents/ChucK/packages on Windows)
    """
    from . import _chump

    return _chump.packages_dir()


def which_os() -> str:
    """Get the current operating system name.

    Returns:
        One of 'mac', 'linux', or 'windows'
    """
    from . import _chump

    return _chump.which_os()


def which_arch() -> str:
    """Get the current system architecture.

    Returns:
        One of 'all', 'x86', 'x86_64', 'arm64', or 'universal'
    """
    from . import _chump

    return _chump.which_arch()
