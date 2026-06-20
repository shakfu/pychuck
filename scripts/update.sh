#!/usr/bin/env bash

# update.sh
#
# This script updates to latest clones of chuck and chugins

CHUCK_REPO=https://github.com/ccrma/chuck.git
CHUGINS_REPO=https://github.com/ccrma/chugins.git
THIRDPARTY_DIR=thirdparty


function update_chuck() {
	git clone ${CHUCK_REPO} chuck-src && \
	mkdir -p ${THIRDPARTY_DIR}/chuck-new && \
	mv chuck-src/src/core ${THIRDPARTY_DIR}/chuck-new/ && \
	mv chuck-src/src/host ${THIRDPARTY_DIR}/chuck-new/ && \
	rm -rf chuck-src && \
	cp ${THIRDPARTY_DIR}/chuck/CMakeLists.txt ${THIRDPARTY_DIR}/chuck-new/ && \
	cp ${THIRDPARTY_DIR}/chuck/core/CMakeLists.txt ${THIRDPARTY_DIR}/chuck-new/core/ && \
	cp ${THIRDPARTY_DIR}/chuck/host/CMakeLists.txt ${THIRDPARTY_DIR}/chuck-new/host/ && \
	mv ${THIRDPARTY_DIR}/chuck ${THIRDPARTY_DIR}/chuck-old && \
	mv ${THIRDPARTY_DIR}/chuck-new ${THIRDPARTY_DIR}/chuck
}



function move_to_new() {
	mv chugins-src/"$1" ${THIRDPARTY_DIR}/chugins-new/"$1"
}

function update_new_chugin() {
	move_to_new "$1" && \
	cp ${THIRDPARTY_DIR}/chugins/"$1"/CMakeLists.txt ${THIRDPARTY_DIR}/chugins-new/"$1" && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/makefile* && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/*.dsw && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/*.dsp && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/*.xcodeproj && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/*.vcxproj && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/*.sln && \
	rm -rf ${THIRDPARTY_DIR}/chugins-new/"$1"/.gitignore && \
	find ${THIRDPARTY_DIR}/chugins-new/"$1" -type f \
		\( -name '*.o' -o -name '*.obj' -o -name '*.chug' \
		   -o -name '*.a' -o -name '*.so' -o -name '*.dylib' \) -delete
}


# Re-apply numchuck local patches to vendored chuck source. A wholesale chuck
# update overwrites core/ and host/, silently dropping any source patch (e.g.
# the Windows shutdown delay -- see docs/windows_fix.md, which regressed exactly
# this way). Hard-fail if a patch no longer applies so the conflict is noticed
# instead of shipping a broken Windows build.
function apply_chuck_patches() {
	local patch
	for patch in scripts/patches/*.patch; do
		[ -e "$patch" ] || continue
		echo "applying chuck patch: ${patch}"
		if ! git apply "$patch"; then
			echo "ERROR: failed to apply ${patch}" >&2
			echo "       chuck source likely changed upstream; resolve manually." >&2
			echo "       chuck-old preserved for reference." >&2
			return 1
		fi
	done
}


function update() {
	update_chuck && \
	apply_chuck_patches && \
	rm -rf ${THIRDPARTY_DIR}/chuck-old
	# rm -rf ${THIRDPARTY_DIR}/chugins-old
}

update


