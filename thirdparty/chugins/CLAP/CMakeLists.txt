include(FetchContent)

FetchContent_Declare(
    clap
    GIT_REPOSITORY https://github.com/free-audio/clap.git
    GIT_TAG        1.2.6
)

set(CLAP_BUILD_TESTS OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(clap)

add_chugin(
    LINK_LIBS
        clap
        "$<$<PLATFORM_ID:Darwin>:-framework CoreFoundation>"
)
