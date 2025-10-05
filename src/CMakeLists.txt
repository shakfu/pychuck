# set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/pychuck)
# set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/src/pychuck)

nanobind_add_module(
  # Name of the extension
  _pychuck

  # Target the stable ABI for Python 3.12+, which reduces
  # the number of binary wheels that must be built. This
  # does nothing on older Python versions
  STABLE_ABI

  # Build libnanobind statically and merge it into the
  # extension (which itself remains a shared library)
  #
  # If your project builds multiple extensions, you can
  # replace this flag by NB_SHARED to conserve space by
  # reusing a shared libnanobind across libraries
  NB_STATIC

  # Source code goes here
  ${CMAKE_SOURCE_DIR}/src/_pychuck.cpp
)

target_include_directories(_pychuck
    PRIVATE
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/core
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host
)

target_link_libraries(_pychuck
    PUBLIC
    "$<$<PLATFORM_ID:Darwin>:-framework CoreAudio>"
    "$<$<PLATFORM_ID:Darwin>:-framework CoreMIDI>"
    "$<$<PLATFORM_ID:Darwin>:-framework CoreFoundation>"
    "$<$<PLATFORM_ID:Darwin>:-framework IOKit>"
    "$<$<PLATFORM_ID:Darwin>:-framework Carbon>"
    "$<$<PLATFORM_ID:Darwin>:-framework AppKit>"
    "$<$<PLATFORM_ID:Darwin>:-framework Foundation>"
    "$<$<PLATFORM_ID:Darwin>:-F/System/Library/PrivateFrameworks>"
    "$<$<PLATFORM_ID:Darwin>:-weak_framework MultitouchSupport>"
    chuck_lib
)

set_target_properties(_pychuck PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/pychuck"
    ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/pychuck"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/pychuck"
)


# Install directive for scikit-build-core
# install(TARGETS _pychuck LIBRARY DESTINATION .)


