# set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_RELEASE ${CMAKE_SOURCE_DIR}/src/numchuck)
# set(CMAKE_INSTALL_PREFIX ${CMAKE_SOURCE_DIR}/src/numchuck)

nanobind_add_module(
  # Name of the extension
  _numchuck

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
  ${CMAKE_SOURCE_DIR}/src/_numchuck.cpp
  ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host/chuck_audio.cpp
  ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host/RtAudio/RtAudio.cpp
)

target_compile_options(_numchuck
    PUBLIC
    $<$<PLATFORM_ID:Linux>:-fno-strict-aliasing>
    $<$<PLATFORM_ID:Linux>:-fPIC>
)

# Define platform-specific RtAudio macros
target_compile_definitions(_numchuck
    PRIVATE
    $<$<PLATFORM_ID:Darwin>:__MACOSX_CORE__>
    $<$<PLATFORM_ID:Linux>:__PLATFORM_LINUX__>
    $<$<PLATFORM_ID:Linux>:__LINUX_ALSA__>
    $<$<PLATFORM_ID:Linux>:__CK_SNDFILE_NATIVE__>
    $<$<AND:$<PLATFORM_ID:Linux>,$<BOOL:${LINUX_PULSE}>>:__LINUX_PULSE__>
    $<$<AND:$<PLATFORM_ID:Linux>,$<BOOL:${LINUX_JACK}>>:__UNIX_JACK__>
    $<$<PLATFORM_ID:Windows>:__PLATFORM_WIN32__>
    $<$<PLATFORM_ID:Windows>:__WINDOWS_DS__>
    HAVE_CONFIG_H
)

target_include_directories(_numchuck
    PRIVATE
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/core
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host/RtAudio
    ${CMAKE_SOURCE_DIR}/thirdparty/chuck/host/RtAudio/include
)

target_link_libraries(_numchuck
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
    $<$<PLATFORM_ID:Linux>:-lasound>
    $<$<PLATFORM_ID:Linux>:-lstdc++>
    $<$<PLATFORM_ID:Linux>:-ldl>
    $<$<PLATFORM_ID:Linux>:-lm>
    $<$<PLATFORM_ID:Linux>:-lsndfile>
    $<$<PLATFORM_ID:Linux>:-lpthread>
    $<$<AND:$<PLATFORM_ID:Linux>,$<BOOL:${LINUX_JACK}>>:-ljack>
    $<$<AND:$<PLATFORM_ID:Linux>,$<BOOL:${LINUX_PULSE}>>:-lpulse-simple>
    $<$<AND:$<PLATFORM_ID:Linux>,$<BOOL:${LINUX_PULSE}>>:-lpulse>
    chuck_lib
)

set_target_properties(_numchuck PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
    ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
    LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
)

# Install directive for scikit-build-core
install(TARGETS _numchuck LIBRARY DESTINATION numchuck)

# Web server module (optional)
if(NUMCHUCK_ENABLE_WEB)
    message(STATUS "Building web server module (_web)")

    nanobind_add_module(
        _web
        STABLE_ABI
        NB_STATIC
        ${CMAKE_SOURCE_DIR}/src/_web.cpp
        ${CMAKE_SOURCE_DIR}/thirdparty/mongoose/mongoose.c
    )

    target_include_directories(_web
        PRIVATE
        ${CMAKE_SOURCE_DIR}/thirdparty/mongoose
        ${CMAKE_SOURCE_DIR}/thirdparty/chuck/core
    )

    # Platform-specific definitions for Mongoose
    target_compile_definitions(_web
        PRIVATE
        MG_ENABLE_LINES=0
        $<$<PLATFORM_ID:Windows>:MG_ENABLE_WINSOCK2=1>
    )

    # Platform-specific link libraries
    target_link_libraries(_web
        PRIVATE
        $<$<PLATFORM_ID:Windows>:ws2_32>
    )

    set_target_properties(_web PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
        ARCHIVE_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
        LIBRARY_OUTPUT_DIRECTORY_RELEASE "${CMAKE_SOURCE_DIR}/src/numchuck"
    )

    install(TARGETS _web LIBRARY DESTINATION numchuck)
endif()

