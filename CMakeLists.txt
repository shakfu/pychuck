cmake_minimum_required(VERSION 3.15...3.27)

set(CMAKE_OSX_DEPLOYMENT_TARGET "10.15" CACHE STRING "Minimum OS X deployment version" FORCE)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(CMAKE_HOST_WIN32)
    set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded")
endif()

project(pychuck_project LANGUAGES CXX)


enable_language(C)

if (CMAKE_VERSION VERSION_LESS 3.18)
  set(DEV_MODULE Development)
else()
  set(DEV_MODULE Development.Module)
endif()

# general macos options
option(CM_MACOS_HOMEBREW "On MacOS, build using Homebrew dependencies")
option(CM_MACOS_UNIVERSAL "On MacOS, build universal architecture externals")
option(CM_HOST_EMBED_EXAMPLE "Build embedded host example")

# use ccache if available
find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    message(STATUS "Found ccache in ${CCACHE_PROGRAM}")
    set_property(GLOBAL PROPERTY RULE_LAUNCH_COMPILE "${CCACHE_PROGRAM}")
endif()

if (APPLE)
    if (${CMAKE_GENERATOR} MATCHES "Xcode")
            if (${XCODE_VERSION} VERSION_LESS 10)
                message(STATUS "Xcode 10 or higher is required. Please install from the Mac App Store.")
                return ()
            endif ()
    endif ()

    if (NOT CMAKE_OSX_ARCHITECTURES)
        if(CM_MACOS_UNIVERSAL)
            set(CMAKE_OSX_ARCHITECTURES "x86_64;arm64" CACHE STRING "macOS architecture" FORCE)
        else()
            set(CMAKE_OSX_ARCHITECTURES ${CMAKE_SYSTEM_PROCESSOR} CACHE STRING "macOS architecture" FORCE)
        endif()
        message("CMAKE_OSX_ARCHITECTURES set to ${CMAKE_OSX_ARCHITECTURES}")
    endif()
endif()

if(CMAKE_HOST_APPLE) # i.e if is_macos and have_homebrew then get homebrew_prefix
    execute_process(
        COMMAND brew --prefix
        OUTPUT_VARIABLE homebrew_prefix
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(DEFINED homebrew_prefix AND CM_MACOS_HOMEBREW)
        set(local_prefix ${homebrew_prefix})
    else()
        set(local_prefix ${CMAKE_SOURCE_DIR}/build/thirdparty/install)
    endif()
endif()
message(STATUS "local_prefix: ${local_prefix}")

find_package(Python 3.8
  REQUIRED COMPONENTS Interpreter Development.Module
  OPTIONAL_COMPONENTS Development.SABIModule)

include(${CMAKE_SOURCE_DIR}/scripts/cmake/fn_add_chugin.cmake)

add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/nanobind)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/chuck)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/thirdparty/chugins)
add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/src)
