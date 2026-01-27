#include "package.h"
#include <catch2/catch_test_macros.hpp>

TEST_CASE("Parsing valid version string") {
  SECTION("Valid version string") {
    PackageVersion got("1.2.3");
    REQUIRE(got.major == 1);
    REQUIRE(got.minor == 2);
    REQUIRE(got.patch == 3);
  }

  SECTION("Version string with zero values") {
    PackageVersion got("0.0.0");
    REQUIRE(got.major == 0);
    REQUIRE(got.minor == 0);
    REQUIRE(got.patch == 0);
  }

  SECTION("Version string with large values") {
    PackageVersion got("123456789.987654321.1234567890");
    REQUIRE(got.major == 123456789);
    REQUIRE(got.minor == 987654321);
    REQUIRE(got.patch == 1234567890);
  }
}

TEST_CASE("Parsing invalid version string") {
  SECTION("Invalid format: Missing minor version") {
    std::string versionStr = "1..3";
    REQUIRE_THROWS_AS(PackageVersion(versionStr), std::invalid_argument);
  }

  SECTION("Invalid format: negative umber") {
    std::string versionStr = "1.2.-3";
    REQUIRE_THROWS_AS(PackageVersion(versionStr), std::invalid_argument);
  }

  SECTION("Invalid format: Extra dot") {
    std::string versionStr = "1.2.3.";
    REQUIRE_THROWS_AS(PackageVersion(versionStr), std::invalid_argument);
  }

  SECTION("Invalid format: Non-numeric character") {
    std::string versionStr = "1.2.x";
    REQUIRE_THROWS_AS(PackageVersion(versionStr), std::invalid_argument);
  }

  SECTION("Invalid format: Empty string") {
    std::string versionStr = "";
    REQUIRE_THROWS_AS(PackageVersion(versionStr), std::invalid_argument);
  }
}

TEST_CASE("Comparison operators for PackageVersion struct") {
  PackageVersion v1(1, 2, 3);
  PackageVersion v2(1, 2, 3);
  PackageVersion v3(1, 2, 4);

  SECTION("Equality (==)") {
    REQUIRE(v1 == v2);
    REQUIRE_FALSE(v1 == v3);
  }

  SECTION("Inequality (!=)") {
    REQUIRE_FALSE(v1 != v2);
    REQUIRE(v1 != v3);
  }

  SECTION("Less than (<)") {
    REQUIRE_FALSE(v1 < v2);
    REQUIRE(v1 < v3);
    REQUIRE_FALSE(v3 < v1);
  }

  SECTION("Less than or equal to (<=)") {
    REQUIRE(v1 <= v2);
    REQUIRE(v1 <= v3);
    REQUIRE_FALSE(v3 <= v1);
  }

  SECTION("Greater than (>)") {
    REQUIRE_FALSE(v1 > v2);
    REQUIRE_FALSE(v1 > v3);
    REQUIRE(v3 > v1);
  }

  SECTION("Greater than or equal to (>=)") {
    REQUIRE(v1 >= v2);
    REQUIRE_FALSE(v1 >= v3);
    REQUIRE(v3 >= v1);
  }
}

TEST_CASE("latest_version returns the highest compatible version",
          "[latest_version]") {
  // Mockup versions
  PackageVersion v1("1.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v2("2.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v3("3.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v4("3.0.1", "1.5.2.1", "1.5.2.4", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v5("3.0.2", "1.5.2.1", "1.5.2.4", "10.1", "any", ARCH_ALL,
                    {{"./", "file1"}, {"./", "file2"}});

  // Mockup Package with versions
  Package package{"TestPackage",
                  {"Author1", "Author2"},
                  "https://example.com",
                  "https://github.com/example/test",
                  "MIT",
                  "Test package description",
                  {"keyword1", "keyword2"},
                  "A very long description indeed",
                  "www.awesomepackage.com/doc",
                  {v1, v2, v3, v4}};

  SECTION("Test with compatible versions") {
    ChuckVersion language_ver =
        ChuckVersion("1.5.2.4 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";
    Architecture arch = X86_64;

    // Get the latest compatible version
    auto latest = package.latest_version(os, arch, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v4);
  }

  SECTION("Test with language_version_max") {
    ChuckVersion language_ver =
        ChuckVersion("1.5.2.5 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";
    Architecture arch = X86_64;

    // Get the latest compatible version
    auto latest = package.latest_version(os, arch, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v3);
  }

  SECTION("Test with incompatible versions") {
    ChuckVersion language_ver =
        ChuckVersion("1.4.2.4 (nunchucks)"); // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";                     // Mockup operating system
    Architecture arch = X86_64;

    // Get the latest compatible version
    auto latest = package.latest_version(os, arch, language_ver, api_ver);

    // Assert that no version is returned
    REQUIRE_FALSE(latest.has_value());
  }

  SECTION("Test 'any' os") {
    // Mockup Package with versions
    package = {"TestPackage",
               {"Author1", "Author2"},
               "https://example.com",
               "https://github.com/example/test",
               "MIT",
               "Test package description",
               {"keyword1", "keyword2"},
               "A very long description indeed",
               "www.awesomepackage.com/doc",
               {v1, v2, v3, v4, v5}};

    ChuckVersion language_ver =
        ChuckVersion("1.5.2.4 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";
    Architecture arch = X86_64;

    // Get the latest compatible version
    auto latest = package.latest_version(os, arch, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v5);
  }
}

TEST_CASE("version() test") {
  // Mockup versions
  PackageVersion v1("1.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v2("2.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v3("3.0.0", "1.5.2.1", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v4("3.0.1", "1.5.2.1", "1.5.2.4", "10.1", "linux", X86_64,
                    {{"./", "file1"}, {"./", "file2"}});
  PackageVersion v5("3.0.2", "1.5.2.1", "1.5.2.4", "10.1", "any", ARCH_ALL,
                    {{"./", "file1"}, {"./", "file2"}});

  // Mockup Package with versions
  Package package{"TestPackage",
                  {"Author1", "Author2"},
                  "https://example.com",
                  "https://github.com/example/test",
                  "MIT",
                  "Test package description",
                  {"keyword1", "keyword2"},
                  "A very long description indeed",
                  "www.awesomepackage.com/doc",
                  {v1, v2, v3, v4}};

  SECTION("Test with compatible versions") {
    ChuckVersion language_ver =
        ChuckVersion("1.5.2.1 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";
    PackageVersion version("1.0.0");

    // Get the latest compatible version
    auto ver = package.version(version, os, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(ver.has_value());
    REQUIRE(*ver == v1);
  }

  SECTION("Test with incompatible chuck version") {
    ChuckVersion language_ver =
        ChuckVersion("1.5.2.0 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    string os = "linux";
    PackageVersion version("1.0.0");

    // Get the latest compatible version
    auto ver = package.version(version, os, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE_FALSE(ver.has_value());
  }

  SECTION("Test 'any' os") {
    // Mockup Package with versions
    package = {"TestPackage",
               {"Author1", "Author2"},
               "https://example.com",
               "https://github.com/example/test",
               "MIT",
               "Test package description",
               {"keyword1", "keyword2"},
               "A very long description indeed",
               "www.awesomepackage.com/doc",
               {v1, v2, v3, v4, v5}};

    ChuckVersion language_ver =
        ChuckVersion("1.5.2.4 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    PackageVersion version("3.0.2");
    string os = "linux";

    // Get the latest compatible version
    auto latest = package.version(version, os, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v5);
  }

  SECTION("Test no 'api_version'") {
    // Mockup Package with versions
    PackageVersion v1_no_api("1.0.0", "1.5.2.1", "linux", X86_64,
                             {{"./", "file1"}, {"./", "file2"}});
    PackageVersion v2_no_api("2.0.0", "1.5.2.1", "linux", X86_64,
                             {{"./", "file1"}, {"./", "file2"}});

    package = {"TestPackage",
               {"Author1", "Author2"},
               "https://example.com",
               "https://github.com/example/test",
               "MIT",
               "Test package description",
               {"keyword1", "keyword2"},
               "A very long description indeed",
               "www.awesomepackage.com/doc",
               {v1_no_api, v2_no_api}};

    ChuckVersion language_ver =
        ChuckVersion("1.5.2.4 (chai)");      // Mockup ChuckVersion
    ApiVersion api_ver = ApiVersion("10.1"); // Mockup ApiVersion
    PackageVersion version("2.0.0");
    string os = "linux";
    Architecture arch = X86_64;

    // Get the latest compatible version
    auto latest = package.version(version, os, language_ver, api_ver);

    // Assert that the latest version is v3
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v2_no_api);

    latest = package.latest_version(os, arch, language_ver, api_ver);
    REQUIRE(latest.has_value());
    REQUIRE(*latest == v2_no_api);
  }
}
