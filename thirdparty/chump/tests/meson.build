test_sources = [
    'exec_test.cpp',
    'fetch_test.cpp',
    'package_test.cpp',
    'package_list_test.cpp',
    'chuck_version_test.cpp',
    'api_version_test.cpp',
    'util_test.cpp'
]

integration_sources = [
    'integration.cpp',
]

catch2_dep = dependency('catch2-with-main')

testexe = executable('testexe', test_sources,
                     include_directories : inc,
                     dependencies: [chump_lib_dep, catch2_dep],
                     link_with : chump_lib)

test('chump_test', testexe)

integrationexe = executable('integrationexe', integration_sources,
                            include_directories : inc,
                            dependencies: [chump_lib_dep, catch2_dep],
                            link_with : chump_lib)

test('integration_test', integrationexe)
