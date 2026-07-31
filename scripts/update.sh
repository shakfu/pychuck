#!/usr/bin/env bash
#
# update.sh
#
# Refresh the vendored upstream trees.
#
#   thirdparty/chuck/{core,host}  <-  ccrma/chuck        <chuck>/src/{core,host}
#   examples/                     <-  ccrma/chuck        <chuck>/examples
#   thirdparty/chugins/           <-  ccrma/chugins
#
# Every one of these trees carries numchuck-local content that upstream knows
# nothing about: the CMakeLists.txt files, the pre-generated bison/flex output
# committed for the Windows build, the python/ and test/ example sets, the
# built chugins under examples/chugins, and the chugins that do not come from
# ccrma/chugins at all (AbletonLink, AudioUnit, CLAP, Fauck, PdPatch, VST3).
#
# So each tree is rebuilt as: upstream, minus the entries listed as superseded
# or as build cruft, plus every path that exists locally but not upstream.
# Nothing has to be enumerated for a local file to survive an update.
#
# The consequence: a local *edit* to a file upstream also owns is lost on
# update. Keep those as patches under scripts/patches/ (chuck) and
# scripts/patches/chugins/ so they are re-applied after every update --
# docs/windows_fix.md documents a regression caused by exactly this. For the
# same reason the script refuses to run against a dirty vendored tree.

set -euo pipefail
shopt -s nullglob dotglob

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

CHUCK_REPO=${CHUCK_REPO:-https://github.com/ccrma/chuck.git}
CHUGINS_REPO=${CHUGINS_REPO:-https://github.com/ccrma/chugins.git}

BUILD_DIR=build
THIRDPARTY_DIR=thirdparty
CHUCK_SRC=${BUILD_DIR}/chuck-src
CHUGINS_SRC=${BUILD_DIR}/chugins-src
CHUCK_DIR=${THIRDPARTY_DIR}/chuck
CHUGINS_DIR=${THIRDPARTY_DIR}/chugins
EXAMPLES_DIR=examples
PATCH_DIR=scripts/patches
CHUGINS_PATCH_DIR=${PATCH_DIR}/chugins

# upstream example entries superseded by the numchuck overlay: hanoi/, otf/ and
# util/ hold the maintained copies, README.md replaces README, book/ is a large
# set of tutorial sources not shipped here.
PRUNE_EXAMPLES=(
	README
	book
	hanoi.ck
	hanoi++.ck
	hanoi2.ck
	hanoi3.ck
	help.ck
	otf_01.ck
	otf_02.ck
	otf_03.ck
	otf_04.ck
	otf_05.ck
	otf_06.ck
	otf_07.ck
	status.ck
)

# upstream chugins entries not carried: the makefile/Visual Studio/debian build
# systems this project replaces with CMake, and Faust/ (superseded by the
# locally vendored Fauck/).
PRUNE_CHUGINS=(
	.github
	.gitattributes
	.gitmodules
	.travis.yml
	chugins.dsw
	chugins.sln
	debian
	Faust
	makefile
)

# per-chugin build cruft, pruned wherever it appears in the upstream tree
PRUNE_CHUGINS_GLOBS=(
	'makefile'
	'makefile.*'
	'Makefile'
	'*.dsp'
	'*.dsw'
	'*.sln'
	'*.vcxproj'
	'*.vcxproj.*'
	'*.xcodeproj'
	'.gitignore'
	'*.o'
	'*.obj'
	'*.chug'
	'*.a'
	'*.so'
	'*.dylib'
)

CHUCK_REF=""
CHUGINS_REF=""
DO_CHUCK=0
DO_EXAMPLES=0
DO_CHUGINS=0
KEEP_OLD=0
FORCE=0


function info() {
	echo "==> $*"
}

function warn() {
	echo "warning: $*" >&2
}

function die() {
	echo "ERROR: $*" >&2
	exit 1
}

function usage() {
	cat <<-'EOF'
	usage: scripts/update.sh [options] [target ...]

	Refresh the vendored upstream trees, carrying forward every path that
	exists locally but not upstream.

	targets:
	  chuck       thirdparty/chuck from ccrma/chuck, then re-apply patches
	  examples    examples/ from ccrma/chuck
	  chugins     thirdparty/chugins from ccrma/chugins
	  all         all of the above (the default)

	options:
	  --ref REF           chuck branch or tag to clone (default: upstream HEAD)
	  --chugins-ref REF   chugins branch or tag to clone
	  --keep-old          keep the replaced trees under build/ for inspection
	  --force             update even if a vendored tree has uncommitted changes
	  -h, --help          show this message
	EOF
}

function parse_args() {
	local target selected=0

	while [ $# -gt 0 ]; do
		case "$1" in
			--keep-old)   KEEP_OLD=1 ;;
			--force)      FORCE=1 ;;
			--ref)        shift; [ $# -gt 0 ] || die "--ref needs a value"; CHUCK_REF="$1" ;;
			--chugins-ref) shift; [ $# -gt 0 ] || die "--chugins-ref needs a value"; CHUGINS_REF="$1" ;;
			-h|--help)    usage; exit 0 ;;
			-*)           die "unknown option: $1 (try --help)" ;;
			*)
				target="$1"
				selected=1
				case "${target}" in
					chuck)    DO_CHUCK=1 ;;
					examples) DO_EXAMPLES=1 ;;
					chugins)  DO_CHUGINS=1 ;;
					all)      DO_CHUCK=1; DO_EXAMPLES=1; DO_CHUGINS=1 ;;
					*)        die "unknown target: ${target} (try --help)" ;;
				esac
				;;
		esac
		shift
	done

	if [ "${selected}" -eq 0 ]; then
		DO_CHUCK=1
		DO_EXAMPLES=1
		DO_CHUGINS=1
	fi
}

# Report the CHUCK_VERSION_STRING recorded in a chuck_def.h.
function chuck_version() {
	local header="$1"
	if [ ! -f "${header}" ]; then
		echo "unknown"
		return 0
	fi
	sed -n 's/^#define[[:space:]]*CHUCK_VERSION_STRING[[:space:]]*"\(.*\)".*/\1/p' "${header}" | head -1
}

# Refuse to clobber uncommitted edits to files upstream also owns; untracked
# additions are safe because the overlay pass carries them forward.
function assert_not_dirty() {
	local path="$1" dirty
	[ "${FORCE}" -eq 0 ] || return 0
	[ -d .git ] || return 0
	dirty="$(git status --porcelain -- "${path}" | grep -v '^??' || true)"
	[ -n "${dirty}" ] || return 0

	echo "ERROR: ${path} has uncommitted changes to upstream-owned files:" >&2
	echo "${dirty}" >&2
	echo >&2
	echo "       An update overwrites them. Commit them, or capture them as a" >&2
	echo "       patch under ${PATCH_DIR}/ so they are re-applied after every" >&2
	echo "       update (see docs/windows_fix.md). Use --force to override." >&2
	exit 1
}

# Copy every entry under <src-root> that has no counterpart under
# <upstream-root> into <dst-root>, recursing into directories the two trees
# share. This is what preserves the numchuck-local content of a vendored tree
# without having to enumerate it.
OVERLAY_KEPT=()

function overlay_local_only() {
	local src_root="$1" up_root="$2" dst_root="$3" rel="${4:-}"
	local dir="${src_root}${rel:+/$rel}"
	local entry name child

	[ -d "${dir}" ] || return 0

	for entry in "${dir}"/*; do
		name="${entry##*/}"
		child="${rel:+${rel}/}${name}"
		if [ ! -e "${up_root}/${child}" ] && [ ! -L "${up_root}/${child}" ]; then
			mkdir -p "${dst_root}${rel:+/$rel}"
			cp -Rp "${entry}" "${dst_root}/${child}"
			OVERLAY_KEPT+=("${child}")
		elif [ -d "${entry}" ] && [ ! -L "${entry}" ]; then
			overlay_local_only "${src_root}" "${up_root}" "${dst_root}" "${child}"
		fi
	done
}

function report_kept() {
	local label="$1" entry
	if [ ${#OVERLAY_KEPT[@]} -eq 0 ]; then
		warn "no local-only paths found under ${label} -- expected at least a CMakeLists.txt"
		return 0
	fi
	info "preserved ${#OVERLAY_KEPT[@]} local-only path(s) in ${label}:"
	for entry in "${OVERLAY_KEPT[@]}"; do
		echo "    ${entry}"
	done
}

# Copy the numchuck build files back over the staged tree. The overlay already
# preserves the ones upstream does not ship; this covers the ones it does
# (chugins/WarpBuf) and guards against upstream adding more of them later.
function restore_cmakelists() {
	local src_root="$1" dst_root="$2" rel

	while IFS= read -r rel; do
		rel="${rel#"${src_root}"/}"
		mkdir -p "${dst_root}/$(dirname "${rel}")"
		cp -p "${src_root}/${rel}" "${dst_root}/${rel}"
	done < <(find "${src_root}" -name CMakeLists.txt)
}

# Replace <target> with <staged>, parking the old tree under build/.
function swap_in() {
	local target="$1" staged="$2" backup
	backup="${BUILD_DIR}/$(basename "${target}")-old"

	rm -rf "${backup}"
	if [ -e "${target}" ]; then
		mv "${target}" "${backup}"
	fi
	mv "${staged}" "${target}"

	if [ "${KEEP_OLD}" -eq 1 ]; then
		info "previous tree kept at ${backup}"
	else
		rm -rf "${backup}"
	fi
}

# clone_repo <url> <dest> <ref>
function clone_repo() {
	local url="$1" dest="$2" ref="$3"
	local args=(--depth=1)

	if [ -n "${ref}" ]; then
		args+=(--branch "${ref}")
	fi

	info "cloning ${url}${ref:+ @ ${ref}}"
	mkdir -p "${BUILD_DIR}"
	rm -rf "${dest}"
	git clone "${args[@]}" "${url}" "${dest}" >/dev/null 2>&1 || die "clone failed: ${url}"

	info "upstream $(basename "${dest}") at $(git -C "${dest}" rev-parse --short HEAD)"
	rm -rf "${dest}/.git"
}

# Re-apply numchuck local patches to a freshly updated vendored tree. A
# wholesale update overwrites it, silently dropping any source patch (e.g. the
# Windows shutdown delay -- see docs/windows_fix.md, which regressed exactly
# this way). Hard-fail if a patch no longer applies so the conflict is noticed
# instead of shipping a broken build.
function apply_patches() {
	local dir="$1" required="${2:-0}" patch applied=0

	for patch in "${dir}"/*.patch; do
		info "applying patch: ${patch}"
		if ! git apply "${patch}"; then
			echo "ERROR: failed to apply ${patch}" >&2
			echo "       upstream source likely changed; resolve manually." >&2
			return 1
		fi
		applied=$((applied + 1))
	done

	if [ "${applied}" -eq 0 ] && [ "${required}" -eq 1 ]; then
		warn "no patches found in ${dir}/"
	fi
}

function update_chuck() {
	local staged="${BUILD_DIR}/chuck-new"

	[ -d "${CHUCK_SRC}/src/core" ] || die "no src/core in ${CHUCK_SRC}"

	info "vendored chuck $(chuck_version "${CHUCK_DIR}/core/chuck_def.h") -> \
$(chuck_version "${CHUCK_SRC}/src/core/chuck_def.h")"

	rm -rf "${staged}"
	mkdir -p "${staged}"
	cp -Rp "${CHUCK_SRC}/src/core" "${staged}/core"
	cp -Rp "${CHUCK_SRC}/src/host" "${staged}/host"

	# CMakeLists.txt, the committed bison/flex output, anything else local
	OVERLAY_KEPT=()
	overlay_local_only "${CHUCK_DIR}" "${CHUCK_SRC}/src" "${staged}"
	report_kept "${CHUCK_DIR}"
	restore_cmakelists "${CHUCK_DIR}" "${staged}"

	swap_in "${CHUCK_DIR}" "${staged}"
	apply_patches "${PATCH_DIR}" 1
}

function update_examples() {
	local upstream="${CHUCK_SRC}/examples"
	local staged="${BUILD_DIR}/examples-new"
	local entry before after

	[ -d "${upstream}" ] || die "no examples in ${CHUCK_SRC}"

	before=$(find "${EXAMPLES_DIR}" -type f 2>/dev/null | wc -l | tr -d ' ' || true)

	rm -rf "${staged}"
	cp -Rp "${upstream}" "${staged}"

	for entry in "${PRUNE_EXAMPLES[@]}"; do
		rm -rf "${staged:?}/${entry}"
	done

	# python/, max/, test/, the built chugins, data/amen.wav, midi/data, ...
	OVERLAY_KEPT=()
	overlay_local_only "${EXAMPLES_DIR}" "${upstream}" "${staged}"
	report_kept "${EXAMPLES_DIR}"

	# entries upstream added since the last update, worth a look
	for entry in "${staged}"/*; do
		[ -e "${EXAMPLES_DIR}/${entry##*/}" ] || info "new from upstream: ${entry##*/}"
	done

	swap_in "${EXAMPLES_DIR}" "${staged}"

	after=$(find "${EXAMPLES_DIR}" -type f | wc -l | tr -d ' ')
	info "examples: ${before} -> ${after} files"
}

function update_chugins() {
	local staged="${BUILD_DIR}/chugins-new"
	local entry glob

	[ -d "${CHUGINS_SRC}" ] || die "no chugins clone at ${CHUGINS_SRC}"
	[ -f "${CHUGINS_DIR}/CMakeLists.txt" ] || die "missing ${CHUGINS_DIR}/CMakeLists.txt"

	rm -rf "${staged}"
	cp -Rp "${CHUGINS_SRC}" "${staged}"

	for entry in "${PRUNE_CHUGINS[@]}"; do
		rm -rf "${staged:?}/${entry}"
	done

	# Prune before the overlay so that local files sharing these names (the
	# AudioUnit and Fauck makefiles, for instance) are restored afterwards.
	# chuck/ is the chugin SDK and chuginate/ is a project template: their
	# makefiles are payload, not this project's build system.
	for glob in "${PRUNE_CHUGINS_GLOBS[@]}"; do
		find "${staged}" \
			-path "${staged}/chuck" -prune -o \
			-path "${staged}/chuginate" -prune -o \
			-name "${glob}" -prune -exec rm -rf {} +
	done

	# AbletonLink/, AudioUnit/, CLAP/, Fauck/, PdPatch/, VST3/, every
	# per-chugin CMakeLists.txt, the local Sigmund and WarpBuf bits, ...
	OVERLAY_KEPT=()
	overlay_local_only "${CHUGINS_DIR}" "${CHUGINS_SRC}" "${staged}"
	report_kept "${CHUGINS_DIR}"
	restore_cmakelists "${CHUGINS_DIR}" "${staged}"

	# upstream tracks rubberband/libsndfile/libsamplerate under WarpBuf as
	# submodules; a plain clone leaves those as empty directories
	find "${staged}" -type d -empty -delete

	# sigmund.c duplicates symbols in sigmund-dsp.c, so it is kept out of the
	# build under a .orig suffix rather than dropped -- renaming the upstream
	# copy keeps it tracking upstream.
	if [ -f "${staged}/Sigmund/sigmund.c" ]; then
		mv -f "${staged}/Sigmund/sigmund.c" "${staged}/Sigmund/sigmund.c.orig"
	fi

	for entry in "${staged}"/*; do
		[ -e "${CHUGINS_DIR}/${entry##*/}" ] || info "new from upstream: ${entry##*/}"
	done

	# a chugin upstream added is not built until it is added to CMakeLists.txt
	for entry in "${staged}"/*/; do
		entry="$(basename "${entry}")"
		case "${entry}" in
			chuck|chuginate|notes) continue ;;
		esac
		if ! grep -q "add_subdirectory(${entry})" "${CHUGINS_DIR}/CMakeLists.txt"; then
			warn "${entry} is not in ${CHUGINS_DIR}/CMakeLists.txt -- not built"
		fi
	done

	swap_in "${CHUGINS_DIR}" "${staged}"
	apply_patches "${CHUGINS_PATCH_DIR}"
}

function main() {
	parse_args "$@"

	if [ "${DO_CHUCK}" -eq 1 ]; then
		assert_not_dirty "${CHUCK_DIR}"
	fi
	if [ "${DO_CHUGINS}" -eq 1 ]; then
		assert_not_dirty "${CHUGINS_DIR}"
	fi

	if [ "${DO_CHUCK}" -eq 1 ] || [ "${DO_EXAMPLES}" -eq 1 ]; then
		clone_repo "${CHUCK_REPO}" "${CHUCK_SRC}" "${CHUCK_REF}"
	fi
	if [ "${DO_CHUGINS}" -eq 1 ]; then
		clone_repo "${CHUGINS_REPO}" "${CHUGINS_SRC}" "${CHUGINS_REF}"
	fi

	if [ "${DO_CHUCK}" -eq 1 ]; then
		update_chuck
	fi
	if [ "${DO_EXAMPLES}" -eq 1 ]; then
		update_examples
	fi
	if [ "${DO_CHUGINS}" -eq 1 ]; then
		update_chugins
	fi

	rm -rf "${CHUCK_SRC}" "${CHUGINS_SRC}"

	info "done -- review with 'git status' and rebuild with 'make build'"
}

main "$@"
