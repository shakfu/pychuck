#include "package.h"
#include "package_directory.h"
#include "package_list.h"

// #include "CLI/CLI.hpp"

/*******************************************************************
 * Generates a complete manifest.json from the chuck-packages repo
 *****************************************************************/

#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

namespace fs = std::filesystem;

int main(int argc, const char **argv) {
  if (argc != 2) {
    std::cerr
        << "generate_manifest must have one arg: path to manifest directory"
        << std::endl;
    return -1;
  }

  fs::path packages_path = argv[1];
  fs::path packages_subdir = packages_path / "packages";

  if (!fs::exists(packages_subdir) || !fs::is_directory(packages_subdir)) {
    std::cout << "no 'packages' dir found in " << packages_path
              << " make sure you pointed to the chump-packages repo correctly"
              << std::endl;
    return -1;
  }

  std::vector<Package> packages;

  for (auto const &path : fs::directory_iterator{packages_subdir}) {
    if (!fs::is_directory(path))
      continue;

    // Each directory corresponds to a package

    // grab the package.json
    fs::path pkg_path = path.path() / "package.json";

    std::cerr << "Reading " << pkg_path << std::endl;

    if (!fs::exists(pkg_path)) {
      std::cerr
          << "Package definition " << pkg_path
          << "not found, are you in the chump-packages/packages directory?"
          << std::endl;
      continue;
    }

    Package pkg = read_package(pkg_path);

    populate_versions(&pkg, path);

    packages.push_back(pkg);
  }

  PackageList package_list(packages);

  json output;
  output["packages"] = packages;
  output["manifest-version"] = MANIFEST_VERSION_NO;
  std::cout << output.dump(4) << std::endl;

  return 0;
}
