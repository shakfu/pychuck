#include "chuck_version.h"
#include <catch2/catch_test_macros.hpp>
#include <sstream>

TEST_CASE("ApiVersion constructor with default command", "[ApiVersion]") {
  SECTION("Invalid command") {
    // Provide a command that does not exist, the constructor should throw an
    // exception
    REQUIRE_THROWS_AS(ApiVersion("Invalid version string"), std::runtime_error);
    REQUIRE_THROWS_AS(ApiVersion("10.1-dev"), std::runtime_error);
  }
}

TEST_CASE("ApiVersion constructor with version string", "[ApiVersion]") {
  SECTION("Valid version string") { REQUIRE_NOTHROW(ApiVersion("10.1")); }

  SECTION("Invalid version string") {
    // Provide an invalid version string, the constructor should throw an
    // exception
    REQUIRE_THROWS_AS(ApiVersion("Invalid version string"), std::runtime_error);
  }

  SECTION("Invalid version string format - letters") {
    REQUIRE_THROWS_AS(ApiVersion("abc.def"), std::runtime_error);
  }

  SECTION("Invalid version string format - no dot") {
    REQUIRE_THROWS_AS(ApiVersion("20 30"), std::runtime_error);
  }

  SECTION("Empty version string") {
    REQUIRE_THROWS_AS(ApiVersion(""), std::runtime_error);
  }
}

TEST_CASE("ApiVersion makeVersion static method", "[ApiVersion]") {
  ApiVersion version = ApiVersion::makeVersion("1.2");
  REQUIRE(version.getVersionString() == "1.2");
}

TEST_CASE("Output stream operator", "[ApiVersion]") {
  ApiVersion version(6, 9);
  std::ostringstream os;
  os << version;
  REQUIRE(os.str() == "6.9");
}

TEST_CASE("ApiVersion version numbers are correctly parsed", "[ApiVersion]") {
  SECTION("Constructor with version string") {
    ApiVersion chuck("10.1");
    REQUIRE(chuck.major == 10);
    REQUIRE(chuck.minor == 1);
  }
}

TEST_CASE("ApiVersion parameterized constructor") {
  ApiVersion apiVer(2, 3);
  REQUIRE(apiVer.getVersionString() == "2.3");
}

TEST_CASE("ApiVersion makeVersion, makeSystemVersion") {
  ApiVersion apiVer = ApiVersion::makeVersion("4.5");
  REQUIRE(apiVer.getVersionString() == "4.5");
}

TEST_CASE("ApiVersion::set_version", "[ApiVersion]") {
  ApiVersion version;
  SECTION("Valid version string") {
    version.set_version("4.5");
    REQUIRE(version == ApiVersion(4, 5));
  }

  SECTION("Invalid version string throws") {
    REQUIRE_THROWS_AS(version.set_version("4..5"), std::runtime_error);
    REQUIRE_THROWS_AS(version.set_version(""), std::runtime_error);
    REQUIRE_THROWS_AS(version.set_version("4."), std::runtime_error);
  }
}

// Unit tests
TEST_CASE("ApiVersion comparison operators", "[ApiVersion]") {
  ApiVersion chuck1("10.1");
  ApiVersion chuck2("10.2");
  ApiVersion chuck3("11.0");

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
