#include "util.h"

#include <catch2/catch_test_macros.hpp>

namespace fs = std::filesystem;

TEST_CASE("parsePackageName") {
  SECTION("valid cases") {
    auto [name, ver] = parsePackageName("Test");

    CHECK(name == "Test");
    CHECK_FALSE(ver);

    std::tie(name, ver) = parsePackageName("Test=0.9.1");
    CHECK(name == "Test");
    REQUIRE(ver);
    CHECK(ver == "0.9.1");
  }

  SECTION("invalid cases") {
    auto [name, ver] = parsePackageName("Test0.9.1");

    CHECK(name == "Test0.9.1");
    CHECK_FALSE(ver);
  }
}

TEST_CASE("is_subpath", "[path]") {
  REQUIRE(is_subpath("./", "./"));
  REQUIRE(is_subpath("a/b/c", "a/b"));
  REQUIRE(is_subpath("a/b/c", "a/b/c"));
  REQUIRE_FALSE(is_subpath("a/b/c", "b"));
  REQUIRE_FALSE(is_subpath("a", "a/b/c"));

  REQUIRE(is_subpath("a/b/c/..", "a/"));
  REQUIRE_FALSE(is_subpath("./", "./../oops"));

  REQUIRE(is_subpath("./poop", "./"));
  REQUIRE_FALSE(is_subpath("./..", "./"));
  REQUIRE_FALSE(is_subpath("./../../../..", "./"));
}

TEST_CASE("packagePath returns correct path") {
  Package p = {"test_package"};
  fs::path install_dir = "/usr/local/packages";

  REQUIRE(packagePath(p, install_dir) ==
          fs::path("/usr/local/packages/test_package"));
}

TEST_CASE("chumpDir returns correct path based on OS") {
  fs::path home = getHomeDirectory();

#ifdef _WIN32
  fs::path expected = home / "Documents" / "ChucK" / "packages";
#else
  fs::path expected = home / ".chuck" / "packages";
#endif

  REQUIRE(chumpDir() == expected);
}

TEST_CASE("whichOS identifies the correct OS") {
#if defined(_WIN32) || defined(_WIN64) || defined(__CYGWIN__)
  REQUIRE(whichOS() == "windows");
#elif defined(__APPLE__)
  REQUIRE(whichOS() == "mac");
#elif defined(__linux__)
  REQUIRE(whichOS() == "linux");
#else
  REQUIRE(whichOS() == "");
#endif
}

TEST_CASE("fileTypeToDir maps FileType to directory") {
  REQUIRE(fileTypeToDir(PACKAGE_FILE) == fs::path());
  REQUIRE(fileTypeToDir(DATA_FILE) == fs::path("_data"));
  REQUIRE(fileTypeToDir(EXAMPLE_FILE) == fs::path("_examples"));
  REQUIRE(fileTypeToDir(DOCS_FILE) == fs::path("_docs"));
  REQUIRE(fileTypeToDir(DEPS_FILE) == fs::path("_deps"));
  REQUIRE(fileTypeToDir(ZIP_FILE) == fs::path());
}
