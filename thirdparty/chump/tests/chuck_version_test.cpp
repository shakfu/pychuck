#include "chuck_version.h"
#include <catch2/catch_test_macros.hpp>
#include <sstream>
#include <string>

TEST_CASE("ChuckVersion constructor with default command", "[ChuckVersion]") {
  SECTION("Invalid command") {
    // Provide a command that does not exist, the constructor should throw an
    // exception
    REQUIRE_THROWS_AS(ChuckVersion("Invalid version string"),
                      std::runtime_error);
  }
}

TEST_CASE("ChuckVersion constructor with version string", "[ChuckVersion]") {
  SECTION("Valid version string") {
    REQUIRE_NOTHROW(ChuckVersion("1.5.2.5-dev"));
  }

  SECTION("Invalid version string") {
    // Provide an invalid version string, the constructor should throw an
    // exception
    REQUIRE_THROWS_AS(ChuckVersion("Invalid version string"),
                      std::runtime_error);
  }
}

TEST_CASE("ChuckVersion version numbers are correctly parsed",
          "[ChuckVersion]") {
  SECTION("Constructor with version string") {
    ChuckVersion chuck("1.6.3.8");
    REQUIRE(chuck.mega == 1);
    REQUIRE(chuck.major == 6);
    REQUIRE(chuck.minor == 3);
    REQUIRE(chuck.patch == 8);
  }
  SECTION("Valid positive values initialization") {
    ChuckVersion version(1, 2, 3, 4);
    REQUIRE(version.mega == 1);
    REQUIRE(version.major == 2);
    REQUIRE(version.minor == 3);
    REQUIRE(version.patch == 4);
  }
}

TEST_CASE("ChuckVersion makeVersion, makeSystemVersion") {
  ChuckVersion ver = ChuckVersion::makeVersion("7.8.9.10");
  REQUIRE(ver.getVersionString() == "7.8.9.10");
}

TEST_CASE("ChuckVersion - getVersionString", "[version]") {

  SECTION("Positive cases") {
    CHECK(ChuckVersion(0, 0, 0, 0).getVersionString() == "0.0.0.0");
    CHECK(ChuckVersion(1, 0, 0, 0).getVersionString() == "1.0.0.0");
    CHECK(ChuckVersion(0, 1, 0, 0).getVersionString() == "0.1.0.0");
    CHECK(ChuckVersion(0, 0, 1, 0).getVersionString() == "0.0.1.0");
    CHECK(ChuckVersion(0, 0, 0, 1).getVersionString() == "0.0.0.1");
    CHECK(ChuckVersion(1, 2, 3, 4).getVersionString() == "1.2.3.4");
  }

  SECTION("Negative values") {
    CHECK(ChuckVersion(-1, 0, 0, 0).getVersionString() == "-1.0.0.0");
    CHECK(ChuckVersion(0, -1, 0, 0).getVersionString() == "0.-1.0.0");
    CHECK(ChuckVersion(0, 0, -1, 0).getVersionString() == "0.0.-1.0");
    CHECK(ChuckVersion(0, 0, 0, -1).getVersionString() == "0.0.0.-1");
  }
}

// Unit tests
TEST_CASE("ChuckVersion comparison operators", "[ChuckVersion]") {
  ChuckVersion chuck1("1.5.2.5 (chai)");
  ChuckVersion chuck2("1.5.2.6-dev (chai)");
  ChuckVersion chuck3("2.6.0.0 (alligator)");

  SECTION("Equality") {
    REQUIRE(chuck1 == chuck1);
    REQUIRE_FALSE(chuck1 == chuck2);
    REQUIRE_FALSE(chuck1 == chuck3);
  }

  SECTION("Inequality") {
    REQUIRE_FALSE(chuck1 != chuck1);
    REQUIRE(chuck1 != chuck2);
    REQUIRE(chuck1 != chuck3);
  }

  SECTION("Less than") {
    REQUIRE(chuck1 < chuck2);
    REQUIRE(chuck1 < chuck3);
    REQUIRE_FALSE(chuck2 < chuck1);
    REQUIRE_FALSE(chuck3 < chuck1);
  }

  SECTION("Less than or equal to") {
    REQUIRE(chuck1 <= chuck1);
    REQUIRE(chuck1 <= chuck2);
    REQUIRE(chuck1 <= chuck3);
    REQUIRE_FALSE(chuck2 <= chuck1);
    REQUIRE_FALSE(chuck3 <= chuck1);
  }

  SECTION("Greater than") {
    REQUIRE(chuck2 > chuck1);
    REQUIRE(chuck3 > chuck1);
    REQUIRE_FALSE(chuck1 > chuck2);
    REQUIRE_FALSE(chuck1 > chuck3);
  }

  SECTION("Greater than or equal to") {
    REQUIRE(chuck1 >= chuck1);
    REQUIRE(chuck2 >= chuck1);
    REQUIRE(chuck3 >= chuck1);
    REQUIRE_FALSE(chuck1 >= chuck2);
    REQUIRE_FALSE(chuck1 >= chuck3);
  }
}

TEST_CASE("Output stream operator", "[ChuckVersion]") {
  ChuckVersion version(1, 4, 5, 1);
  std::ostringstream os;
  os << version;
  REQUIRE(os.str() == "1.4.5.1");
}
