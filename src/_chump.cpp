// _chump.cpp - Python bindings for chump package manager
//
// This module provides Python bindings for the chump package manager,
// allowing numchuck to install, update, and manage ChucK packages.

#include <nanobind/nanobind.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "chuck_version.h"
#include "manager.h"
#include "package.h"
#include "util.h"

#include <filesystem>
#include <memory>
#include <stdexcept>

namespace nb = nanobind;
using namespace nb::literals;
namespace fs = std::filesystem;

// Python-friendly package info struct
struct PackageInfo {
    std::string name;
    std::vector<std::string> authors;
    std::string description;
    std::string homepage;
    std::string repository;
    std::string license;
    std::vector<std::string> keywords;
    bool installed;
    std::optional<std::string> installed_version;
    std::optional<std::string> latest_version;
};

// Python-friendly version info struct
struct VersionInfo {
    std::string version;
    std::string os;
    std::string arch;
    std::optional<std::string> api_version;
    std::string language_version_min;
    std::optional<std::string> language_version_max;
};

// Main manager wrapper class
class ChumpManager {
public:
    // Constructor that takes version string (called from Python with version from _numchuck)
    ChumpManager(const std::string& chuck_version_str = "1.5.4.3",
                 int api_major = 10, int api_minor = 3) {
        // Get system info
        std::string os = whichOS();
        Architecture arch = whichArch();

        // Get chump directory and ensure it exists
        fs::path chump_dir = chumpDir();
        if (!fs::exists(chump_dir)) {
            fs::create_directories(chump_dir);
        }

        // Get manifest path and URL
        fs::path manifest_path = chump_dir / "manifest.json";
        std::string manifest_url = manifestURL(
            "https://chuck.stanford.edu/release/chump/manifest/");

        // Parse ChucK version from string
        ChuckVersion ck_ver(chuck_version_str);
        ApiVersion api_ver(api_major, api_minor);

        // Store version for later
        chuck_version_ = chuck_version_str;

        // Create the manager (render_tui = false for library use)
        manager_ = std::make_unique<Manager>(
            manifest_path.string(),
            chump_dir,
            ck_ver,
            api_ver,
            os,
            arch,
            manifest_url,
            false  // render_tui
        );
    }

    std::vector<PackageInfo> listPackages() {
        std::vector<Package> packages = manager_->listPackages();
        std::vector<PackageInfo> result;
        result.reserve(packages.size());

        for (const auto& pkg : packages) {
            PackageInfo info;
            info.name = pkg.name;
            info.authors = pkg.authors;
            info.description = pkg.description;
            info.homepage = pkg.homepage;
            info.repository = pkg.repository;
            info.license = pkg.license;
            info.keywords = pkg.keywords;
            info.installed = manager_->is_installed(pkg);

            // Get installed version if present
            if (info.installed) {
                fs::path install_dir = manager_->install_path(pkg);
                auto installed = getInstalledVersion(install_dir);
                if (installed) {
                    info.installed_version = installed->getVersionString();
                }
            }

            // Get latest available version
            auto latest = manager_->latestPackageVersion(pkg.name);
            if (latest) {
                info.latest_version = latest->getVersionString();
            }

            result.push_back(std::move(info));
        }

        return result;
    }

    std::optional<PackageInfo> getPackage(const std::string& name) {
        auto pkg_opt = manager_->getPackage(name);
        if (!pkg_opt) {
            return std::nullopt;
        }

        const Package& pkg = pkg_opt.value();
        PackageInfo info;
        info.name = pkg.name;
        info.authors = pkg.authors;
        info.description = pkg.description;
        info.homepage = pkg.homepage;
        info.repository = pkg.repository;
        info.license = pkg.license;
        info.keywords = pkg.keywords;
        info.installed = manager_->is_installed(pkg);

        if (info.installed) {
            fs::path install_dir = manager_->install_path(pkg);
            auto installed = getInstalledVersion(install_dir);
            if (installed) {
                info.installed_version = installed->getVersionString();
            }
        }

        auto latest = manager_->latestPackageVersion(pkg.name);
        if (latest) {
            info.latest_version = latest->getVersionString();
        }

        return info;
    }

    bool install(const std::string& package_name) {
        return manager_->install(package_name);
    }

    bool uninstall(const std::string& package_name, bool force = false) {
        return manager_->uninstall(package_name, force);
    }

    bool update(const std::string& package_name) {
        return manager_->update(package_name);
    }

    bool updateManifest() {
        return manager_->update_manifest();
    }

    bool isInstalled(const std::string& package_name) {
        auto pkg_opt = manager_->getPackage(package_name);
        if (!pkg_opt) {
            return false;
        }
        return manager_->is_installed(pkg_opt.value());
    }

    std::string installPath(const std::string& package_name) {
        auto pkg_opt = manager_->getPackage(package_name);
        if (!pkg_opt) {
            throw std::runtime_error("Package not found: " + package_name);
        }
        return manager_->install_path(pkg_opt.value()).string();
    }

    std::string packagesDir() {
        return chumpDir().string();
    }

    std::string chuckVersion() {
        return chuck_version_;
    }

private:
    std::unique_ptr<Manager> manager_;
    std::string chuck_version_;
};

NB_MODULE(_chump, m) {
    m.doc() = "Python bindings for chump package manager";

    // PackageInfo struct
    nb::class_<PackageInfo>(m, "PackageInfo", "Information about a ChucK package")
        .def_ro("name", &PackageInfo::name, "Package name")
        .def_ro("authors", &PackageInfo::authors, "Package authors")
        .def_ro("description", &PackageInfo::description, "Package description")
        .def_ro("homepage", &PackageInfo::homepage, "Package homepage URL")
        .def_ro("repository", &PackageInfo::repository, "Package repository URL")
        .def_ro("license", &PackageInfo::license, "Package license")
        .def_ro("keywords", &PackageInfo::keywords, "Package keywords")
        .def_ro("installed", &PackageInfo::installed, "Whether package is installed")
        .def_ro("installed_version", &PackageInfo::installed_version,
                "Installed version (if installed)")
        .def_ro("latest_version", &PackageInfo::latest_version,
                "Latest available version")
        .def("__repr__", [](const PackageInfo& p) {
            std::string status = p.installed ? "installed" : "available";
            return "<PackageInfo '" + p.name + "' (" + status + ")>";
        });

    // ChumpManager class
    nb::class_<ChumpManager>(m, "ChumpManager",
        "Manager for ChucK packages (chump)")
        .def(nb::init<const std::string&, int, int>(),
            "chuck_version"_a = "1.5.4.3", "api_major"_a = 10, "api_minor"_a = 3,
            "Create a new package manager instance")
        .def("list_packages", &ChumpManager::listPackages,
            "List all available and installed packages")
        .def("get_package", &ChumpManager::getPackage,
            "name"_a,
            "Get information about a specific package")
        .def("install", &ChumpManager::install,
            "package_name"_a,
            "Install a package (use name@version for specific version)")
        .def("uninstall", &ChumpManager::uninstall,
            "package_name"_a, "force"_a = false,
            "Uninstall a package")
        .def("update", &ChumpManager::update,
            "package_name"_a,
            "Update a package to the latest version")
        .def("update_manifest", &ChumpManager::updateManifest,
            "Update the package manifest from the server")
        .def("is_installed", &ChumpManager::isInstalled,
            "package_name"_a,
            "Check if a package is installed")
        .def("install_path", &ChumpManager::installPath,
            "package_name"_a,
            "Get the installation path for a package")
        .def("packages_dir", &ChumpManager::packagesDir,
            "Get the packages directory path")
        .def("chuck_version", &ChumpManager::chuckVersion,
            "Get the ChucK version used for package compatibility");

    // Module-level utility functions
    m.def("packages_dir", []() {
        return chumpDir().string();
    }, "Get the default packages directory path");

    m.def("which_os", []() {
        return whichOS();
    }, "Get the current operating system name");

    m.def("which_arch", []() {
        Architecture arch = whichArch();
        return architectureToString.at(arch);
    }, "Get the current system architecture");
}
