
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})

# Generate parser files on macOS or Linux (if bison/flex available).
#
# These are generated into the build tree, never into core/. Generating in
# place rewrote the committed chuck.tab.c, chuck.tab.h, chuck.yy.c and
# chuck.output on every configure, which left the vendored tree permanently
# dirty in git and made scripts/update.sh refuse to update it (it declines to
# overwrite uncommitted changes to upstream-owned files). The committed copies
# stay in core/ as the fallback for hosts without bison/flex.
set(CHUCK_PARSER_DIR ${CMAKE_CURRENT_BINARY_DIR}/parser)
set(CHUCK_PARSER_GENERATED FALSE)

if(NOT WIN32)
	find_program(BISON_EXECUTABLE bison)
	find_program(FLEX_EXECUTABLE flex)
	if(BISON_EXECUTABLE AND FLEX_EXECUTABLE)
		file(MAKE_DIRECTORY ${CHUCK_PARSER_DIR})
		# one execute_process per tool: multiple COMMANDs in a single call are
		# piped together, which hides each tool's exit status
		execute_process(
			COMMAND ${BISON_EXECUTABLE} -dv -b chuck ${CMAKE_CURRENT_SOURCE_DIR}/chuck.y
			WORKING_DIRECTORY ${CHUCK_PARSER_DIR}
			RESULT_VARIABLE BISON_RESULT
		)
		execute_process(
			COMMAND ${FLEX_EXECUTABLE} -ochuck.yy.c ${CMAKE_CURRENT_SOURCE_DIR}/chuck.lex
			WORKING_DIRECTORY ${CHUCK_PARSER_DIR}
			RESULT_VARIABLE FLEX_RESULT
		)
		if(BISON_RESULT EQUAL 0 AND FLEX_RESULT EQUAL 0)
			set(CHUCK_PARSER_GENERATED TRUE)
		else()
			message(WARNING
				"bison/flex failed (${BISON_RESULT}/${FLEX_RESULT}); "
				"falling back to the committed parser sources")
		endif()
	endif()
endif()

if(WIN32)
	set(C_CORE
		chuck_yacc.c
		util_network.c
		util_raw.c
		util_xforms.c
	)
else()
	# macOS and Linux use bison/flex generated files: the fresh ones from the
	# build tree when bison/flex ran, otherwise the copies committed under core/
	if(CHUCK_PARSER_GENERATED)
		set(CHUCK_TAB_C ${CHUCK_PARSER_DIR}/chuck.tab.c)
		set(CHUCK_YY_C ${CHUCK_PARSER_DIR}/chuck.yy.c)
	else()
		set(CHUCK_TAB_C chuck.tab.c)
		set(CHUCK_YY_C chuck.yy.c)
	endif()
	set(C_CORE
		${CHUCK_TAB_C}
		${CHUCK_YY_C}
		util_network.c
		util_raw.c
		util_xforms.c
	)
endif()

message(STATUS "C_CORE files: ${C_CORE}")

set(CXX_CORE
	chuck.cpp
	chuck_absyn.cpp
	chuck_errmsg.cpp
	chuck_frame.cpp
	chuck_parse.cpp
	chuck_carrier.cpp
	chuck_compile.cpp
	chuck_dl.cpp
	chuck_emit.cpp
	chuck_globals.cpp
	chuck_instr.cpp
	chuck_io.cpp
	chuck_lang.cpp
	chuck_oo.cpp
	chuck_otf.cpp
	chuck_scan.cpp
	chuck_shell.cpp
	chuck_stats.cpp
	chuck_symbol.cpp
	chuck_table.cpp
	chuck_type.cpp
	chuck_ugen.cpp
	chuck_vm.cpp
	hidio_sdl.cpp
	midiio_rtmidi.cpp
	rtmidi.cpp
	uana_extract.cpp
	uana_xform.cpp
	ugen_filter.cpp
	ugen_osc.cpp
	ugen_stk.cpp
	ugen_xxx.cpp
	ulib_ai.cpp
	ulib_doc.cpp
	ulib_machine.cpp
	ulib_math.cpp
	ulib_opsc.cpp
	ulib_std.cpp
	util_buffers.cpp
	util_console.cpp
	util_hid.cpp
	util_math.cpp
	util_platforms.cpp
	util_opsc.cpp
	util_serial.cpp
	util_string.cpp
	util_thread.cpp
)

if(APPLE)
	set(LO_C_CORE
		lo/address.c
		lo/blob.c
		lo/bundle.c
		lo/message.c
		lo/method.c
		lo/pattern_match.c
		lo/send.c
		lo/server.c
		lo/server_thread.c
		lo/timetag.c
	)
else()
	set(LO_C_CORE
		lo/address.c
		lo/blob.c
		lo/bundle.c
		lo/message.c
		lo/method.c
		lo/pattern_match.c
		lo/send.c
		lo/server.c
		lo/timetag.c
	)
endif()


add_library(chuck_lib STATIC)

target_sources(chuck_lib PRIVATE
	util_sndfile.c
	${C_CORE}
	${LO_C_CORE}
	${CXX_CORE}
)

# Explicitly mark .c files as C language
set_source_files_properties(
	util_sndfile.c
	${C_CORE}
	${LO_C_CORE}
	PROPERTIES
	LANGUAGE C
)

if (CMAKE_HOST_APPLE)
	set_source_files_properties(
		util_sndfile.c
		util_hid.cpp
		ulib_opsc.cpp
		ulib_doc.cpp
		ugen_stk.cpp
		${CHUCK_YY_C}
		PROPERTIES
		COMPILE_OPTIONS "-Wno-shorten-64-to-32"
	)
endif()


# Position-independent code required for shared library on Linux
target_compile_options(chuck_lib
	PRIVATE
	$<$<PLATFORM_ID:Linux>:-fPIC>
)

target_compile_definitions(chuck_lib
	PUBLIC
	$<$<PLATFORM_ID:Darwin>:__MACOSX_CORE__>
	$<$<PLATFORM_ID:Linux>:__PLATFORM_LINUX__>
	$<$<PLATFORM_ID:Linux>:__LINUX_ALSA__>
	$<$<PLATFORM_ID:Windows>:__PLATFORM_WINDOWS__>
	$<$<PLATFORM_ID:Windows>:__PLATFORM_WIN32__>
	$<$<CONFIG:Debug>:__CHUCK_DEBUG__>
	HAVE_CONFIG_H
)


target_include_directories(chuck_lib
	PUBLIC
	${CMAKE_SOURCE_DIR}
	${CMAKE_SOURCE_DIR}/lo
	PRIVATE
	# the generated parser sources sit in the build tree and still include
	# "chuck_absyn.h" / "chuck_errmsg.h", which no longer resolve relative to
	# the including file
	${CMAKE_CURRENT_SOURCE_DIR}
	${CHUCK_PARSER_DIR}
)

target_link_libraries(chuck_lib
	PUBLIC
	$<$<PLATFORM_ID:Linux>:dl>
	$<$<PLATFORM_ID:Linux>:pthread>
	$<$<PLATFORM_ID:Linux>:m>
	$<$<PLATFORM_ID:Windows>:kernel32>
	$<$<PLATFORM_ID:Windows>:user32>
	$<$<PLATFORM_ID:Windows>:gdi32>
	$<$<PLATFORM_ID:Windows>:winspool>
	$<$<PLATFORM_ID:Windows>:comdlg32>
	$<$<PLATFORM_ID:Windows>:advapi32>
	$<$<PLATFORM_ID:Windows>:shell32>
	$<$<PLATFORM_ID:Windows>:ole32>
	$<$<PLATFORM_ID:Windows>:oleaut32>
	$<$<PLATFORM_ID:Windows>:uuid>
	$<$<PLATFORM_ID:Windows>:odbc32>
	$<$<PLATFORM_ID:Windows>:odbccp32>
	# $<$<PLATFORM_ID:Windows>:/subsystem:console>
	# $<$<PLATFORM_ID:Windows>:/machine:I386>
	$<$<PLATFORM_ID:Windows>:dsound>
	# $<$<PLATFORM_ID:Windows>:dinput>
	$<$<PLATFORM_ID:Windows>:dinput8>
	$<$<PLATFORM_ID:Windows>:dxguid>
	$<$<PLATFORM_ID:Windows>:wsock32>
	$<$<PLATFORM_ID:Windows>:ws2_32>
	$<$<PLATFORM_ID:Windows>:winmm>
	$<$<PLATFORM_ID:Windows>:iphlpapi>
)

set_property(TARGET chuck_lib PROPERTY OUTPUT_NAME chuck)


