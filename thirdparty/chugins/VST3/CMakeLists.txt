include(FetchContent)

FetchContent_Declare(
    vst3sdk
    GIT_REPOSITORY https://github.com/steinbergmedia/vst3sdk.git
    GIT_TAG        v3.8.0_build_66
    GIT_SUBMODULES_RECURSE TRUE
    EXCLUDE_FROM_ALL
)

# Disable everything we don't need from the VST3 SDK
set(SMTG_ADD_VSTGUI OFF CACHE BOOL "" FORCE)
set(SMTG_ENABLE_VSTGUI_SUPPORT OFF CACHE BOOL "" FORCE)
set(SMTG_ADD_VST3_PLUGINS_SAMPLES OFF CACHE BOOL "" FORCE)
set(SMTG_ADD_VST3_HOSTING_SAMPLES OFF CACHE BOOL "" FORCE)
set(SMTG_RUN_VST_VALIDATOR OFF CACHE BOOL "" FORCE)
set(SMTG_ADD_PLUGIN_COMPATIBILITY_SAMPLES OFF CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(vst3sdk)

# Platform-specific VST3 hosting module sources
set(VST3_SDK_ROOT "${vst3sdk_SOURCE_DIR}")

# plugprovider.cpp is not part of the sdk_hosting target, compile it directly
set(VST3_EXTRA_SOURCES
    "${VST3_SDK_ROOT}/public.sdk/source/vst/hosting/plugprovider.cpp"
)

if(CMAKE_HOST_APPLE)
    list(APPEND VST3_EXTRA_SOURCES
        "${VST3_SDK_ROOT}/public.sdk/source/vst/hosting/module_mac.mm"
    )
    set_source_files_properties(
        "${VST3_SDK_ROOT}/public.sdk/source/vst/hosting/module_mac.mm" PROPERTIES
        COMPILE_FLAGS "-fobjc-arc"
    )
elseif(CMAKE_HOST_LINUX)
    list(APPEND VST3_EXTRA_SOURCES
        "${VST3_SDK_ROOT}/public.sdk/source/vst/hosting/module_linux.cpp"
    )
elseif(CMAKE_HOST_WIN32)
    list(APPEND VST3_EXTRA_SOURCES
        "${VST3_SDK_ROOT}/public.sdk/source/vst/hosting/module_win32.cpp"
    )
endif()

add_chugin(
    OTHER_SOURCES
        ${VST3_EXTRA_SOURCES}
    COMPILE_DEFINITIONS
        HAVE_VST3_SDK
    LINK_LIBS
        base
        sdk
        sdk_common
        pluginterfaces
        sdk_hosting
        "$<$<PLATFORM_ID:Darwin>:-framework CoreFoundation>"
        "$<$<PLATFORM_ID:Darwin>:-framework CoreServices>"
        "$<$<PLATFORM_ID:Darwin>:-framework Foundation>"
)
