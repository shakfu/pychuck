#include <fstream>

namespace fs = std::filesystem;

void populate_versions(Package *p, fs::path pkg_path);
Package read_package(fs::path filepath);
PackageVersion read_package_version(fs::path filepath);

// traverse through a package directory and populate p with versions
void populate_versions(Package *p, fs::path pkg_path) {
  for (auto const &path : fs::directory_iterator{pkg_path}) {
    // std::cout << path << std::endl;

    if (fs::is_directory(path)) {
      populate_versions(p, path);
    } else if (path.path().extension() == ".json" &&
               path.path().filename() != "package.json") {
      PackageVersion pkg_ver = read_package_version(path);
      p->versions.push_back(pkg_ver);
    }
  }
}

Package read_package(fs::path filepath) {
  std::cerr << "Reading " << filepath << std::endl;
  std::ifstream f(filepath);

  if (!f.good()) {
    throw std::invalid_argument("Unable to open Package definition \"" +
                                filepath.string() + "\"");
  }

  json data = json::parse(f);

  Package p = data.get<Package>();

  return p;
}

PackageVersion read_package_version(fs::path filepath) {
  std::cerr << "Reading " << filepath << std::endl;
  std::ifstream f(filepath);

  if (!f.good()) {
    throw std::invalid_argument("Unable to open PackageVersion definition \"" +
                                filepath.string() + "\"");
  }

  json data = json::parse(f);

  PackageVersion p = data.get<PackageVersion>();

  return p;
}
