# CMakeLists.txt for chump library
# Builds chump as a static library for use by the _chump Python module

cmake_minimum_required(VERSION 3.15)

# Enable FetchContent for dependencies
include(FetchContent)

# nlohmann_json - header-only JSON library
FetchContent_Declare(
    nlohmann_json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(nlohmann_json)

# Find system libraries
find_package(CURL REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(ZLIB REQUIRED)

# minizip-ng for zip extraction
FetchContent_Declare(
    minizip-ng
    GIT_REPOSITORY https://github.com/zlib-ng/minizip-ng.git
    GIT_TAG 4.0.7
    GIT_SHALLOW TRUE
)
# Configure minizip-ng options before making it available
# Enable compatibility layer for unzip.h API
set(MZ_COMPAT ON CACHE BOOL "" FORCE)
set(MZ_BZIP2 OFF CACHE BOOL "" FORCE)
set(MZ_LZMA OFF CACHE BOOL "" FORCE)
set(MZ_ZSTD OFF CACHE BOOL "" FORCE)
set(MZ_LIBCOMP OFF CACHE BOOL "" FORCE)
set(MZ_FETCH_LIBS OFF CACHE BOOL "" FORCE)
set(MZ_FORCE_FETCH_LIBS OFF CACHE BOOL "" FORCE)
set(MZ_ZLIB ON CACHE BOOL "" FORCE)
set(MZ_OPENSSL ON CACHE BOOL "" FORCE)
set(MZ_SIGNING OFF CACHE BOOL "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(minizip-ng)

# Chump library sources
set(CHUMP_SOURCES
    ${CMAKE_CURRENT_SOURCE_DIR}/src/chuck_version.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/fetch.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/manager.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/package.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/package_list.cpp
    ${CMAKE_CURRENT_SOURCE_DIR}/src/util.cpp
)

# Create static library
add_library(chump_lib STATIC ${CHUMP_SOURCES})

# Include directories
target_include_directories(chump_lib
    PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE
    ${CMAKE_SOURCE_DIR}/thirdparty/chugins/chuck/include
    ${minizip-ng_SOURCE_DIR}
)

# Link dependencies
target_link_libraries(chump_lib
    PUBLIC
    nlohmann_json::nlohmann_json
    CURL::libcurl
    OpenSSL::SSL
    OpenSSL::Crypto
    ZLIB::ZLIB
    minizip
)

# Require C++17 for std::filesystem
target_compile_features(chump_lib PUBLIC cxx_std_17)

# Platform-specific settings
if(APPLE)
    target_compile_definitions(chump_lib PRIVATE __MACOSX_CORE__)
elseif(UNIX)
    target_compile_definitions(chump_lib PRIVATE __PLATFORM_LINUX__)
elseif(WIN32)
    target_compile_definitions(chump_lib PRIVATE __PLATFORM_WIN32__)
endif()
