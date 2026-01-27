#include "fetch.h"
#include "package.h"
#include <catch2/catch_test_macros.hpp>

TEST_CASE("Check if a string is a valid URL", "[Fetch]") {
  Fetch f(false);

  // Positive examples (valid URLs)
  CHECK(f.isURL("http://example.com"));
  CHECK(f.isURL("https://www.example.com"));

  // Negative examples (not valid URLs)
  CHECK_FALSE(f.isURL("ftp://example.com"));

  // This is find for now, but something to reconsider
  CHECK_FALSE(f.isURL("www.example.com")); // Missing protocol
  CHECK_FALSE(f.isURL("invalid-url"));     // Not a URL format
  CHECK_FALSE(f.isURL("path/to/file.json"));
}

TEST_CASE("Fetch::fetch() tests") {
  Fetch f;
  Package p;
  PackageVersion v;
  SECTION("Invalid URL") {
    REQUIRE_FALSE(f.fetch("badurl", "./", p, v, "/tmp/", PACKAGE_FILE, ""));
  }
}
