"""
CLI commands for managing ChucK packages.

Provides commands to list, install, update, and uninstall ChucK packages
using the chump package manager.
"""

from __future__ import annotations

import sys


def _get_manager():
    """Get package manager instance, handling import errors gracefully."""
    try:
        from ..packages import PackageManager

        return PackageManager()
    except ImportError as e:
        print(f"Error: Package management not available: {e}")
        print("Make sure numchuck was built with chump support.")
        sys.exit(1)


def cmd_pkg_list(installed_only: bool = False) -> None:
    """List all packages.

    Args:
        installed_only: If True, only show installed packages
    """
    pm = _get_manager()
    packages = pm.list_packages(installed_only=installed_only)

    if not packages:
        if installed_only:
            print("No packages installed.")
            print("\nUse 'numchuck pkg install <name>' to install a package.")
        else:
            print("No packages found in manifest.")
            print("\nTry 'numchuck pkg refresh' to update the package list.")
        return

    # Calculate column widths
    max_name = max(len(p.name) for p in packages)
    max_version = max(
        len(p.installed_version or p.latest_version or "") for p in packages
    )

    # Print header
    print(f"{'Package':<{max_name}}  {'Version':<{max_version}}  Status")
    print("-" * (max_name + max_version + 15))

    # Print packages
    for pkg in sorted(packages, key=lambda p: p.name.lower()):
        version = pkg.installed_version or pkg.latest_version or "?"
        if pkg.installed:
            status = "[installed]"
            # Check if update available
            if pkg.latest_version and pkg.installed_version:
                if pkg.latest_version != pkg.installed_version:
                    status = f"[installed, update available: {pkg.latest_version}]"
        else:
            status = ""

        print(f"{pkg.name:<{max_name}}  {version:<{max_version}}  {status}")

    print()
    print(f"Total: {len(packages)} packages")
    installed_count = sum(1 for p in packages if p.installed)
    if installed_count > 0:
        print(f"Installed: {installed_count}")


def cmd_pkg_info(name: str) -> None:
    """Show detailed information about a package.

    Args:
        name: Package name
    """
    pm = _get_manager()
    pkg = pm.get_package(name)

    if pkg is None:
        print(f"Package '{name}' not found.")
        print("\nUse 'numchuck pkg list' to see available packages.")
        return

    print(f"Package: {pkg.name}")
    print(f"Description: {pkg.description}")
    print()

    if pkg.authors:
        print(f"Authors: {', '.join(pkg.authors)}")

    if pkg.homepage:
        print(f"Homepage: {pkg.homepage}")

    if pkg.repository:
        print(f"Repository: {pkg.repository}")

    if pkg.license:
        print(f"License: {pkg.license}")

    if pkg.keywords:
        print(f"Keywords: {', '.join(pkg.keywords)}")

    print()

    if pkg.installed:
        print(f"Status: Installed (version {pkg.installed_version})")
        print(f"Install path: {pm.install_path(name)}")
        if pkg.latest_version and pkg.latest_version != pkg.installed_version:
            print(f"Update available: {pkg.latest_version}")
    else:
        print(f"Status: Not installed")
        if pkg.latest_version:
            print(f"Latest version: {pkg.latest_version}")


def cmd_pkg_install(package_spec: str) -> None:
    """Install a package.

    Args:
        package_spec: Package name, optionally with version (e.g., "Patch@1.0.0")
    """
    pm = _get_manager()

    # Parse package@version format
    if "@" in package_spec:
        name, version = package_spec.split("@", 1)
    else:
        name = package_spec
        version = None

    # Check if already installed
    if pm.is_installed(name):
        print(f"Package '{name}' is already installed.")
        print(f"Use 'numchuck pkg update {name}' to update it.")
        return

    print(f"Installing {name}{'@' + version if version else ''}...")

    if pm.install(name, version):
        print(f"Successfully installed {name}")
        print(f"Install path: {pm.install_path(name)}")
    else:
        print(f"Failed to install {name}")
        sys.exit(1)


def cmd_pkg_uninstall(name: str, force: bool = False) -> None:
    """Uninstall a package.

    Args:
        name: Package name
        force: If True, force removal even if files have been modified
    """
    pm = _get_manager()

    if not pm.is_installed(name):
        print(f"Package '{name}' is not installed.")
        return

    print(f"Uninstalling {name}...")

    if pm.uninstall(name, force):
        print(f"Successfully uninstalled {name}")
    else:
        print(f"Failed to uninstall {name}")
        if not force:
            print("Try 'numchuck pkg uninstall --force' to force removal.")
        sys.exit(1)


def cmd_pkg_update(name: str | None = None) -> None:
    """Update a package or all packages.

    Args:
        name: Package name to update, or None to update all
    """
    pm = _get_manager()

    if name is None:
        # Update all installed packages
        packages = pm.list_packages(installed_only=True)
        if not packages:
            print("No packages installed to update.")
            return

        print(f"Checking updates for {len(packages)} installed packages...")
        updated = 0
        for pkg in packages:
            if pkg.latest_version and pkg.installed_version != pkg.latest_version:
                print(
                    f"Updating {pkg.name} ({pkg.installed_version} -> {pkg.latest_version})..."
                )
                if pm.update(pkg.name):
                    updated += 1
                else:
                    print(f"  Failed to update {pkg.name}")

        if updated == 0:
            print("All packages are up to date.")
        else:
            print(f"Updated {updated} packages.")
    else:
        if not pm.is_installed(name):
            print(f"Package '{name}' is not installed.")
            print(f"Use 'numchuck pkg install {name}' to install it.")
            return

        pkg = pm.get_package(name)
        if pkg and pkg.latest_version == pkg.installed_version:
            print(f"Package '{name}' is already at the latest version.")
            return

        print(f"Updating {name}...")
        if pm.update(name):
            print(f"Successfully updated {name}")
        else:
            print(f"Failed to update {name}")
            sys.exit(1)


def cmd_pkg_refresh() -> None:
    """Update the package manifest from the server."""
    pm = _get_manager()

    print("Refreshing package manifest...")

    if pm.update_manifest():
        print("Package manifest updated successfully.")
    else:
        print("Package manifest is already up to date.")


def cmd_pkg_search(query: str) -> None:
    """Search for packages.

    Args:
        query: Search query
    """
    pm = _get_manager()
    results = pm.search(query)

    if not results:
        print(f"No packages matching '{query}' found.")
        return

    print(f"Packages matching '{query}':")
    print()

    for pkg in results:
        status = " [installed]" if pkg.installed else ""
        print(f"  {pkg.name}{status}")
        print(f"    {pkg.description}")
        print()

    print(f"Found {len(results)} packages.")


def cmd_pkg_path() -> None:
    """Show the packages directory path."""
    pm = _get_manager()
    print(f"Packages directory: {pm.packages_dir}")
    print(f"ChucK version: {pm.chuck_version}")
