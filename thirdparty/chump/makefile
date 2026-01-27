
########################## DEFAULT MAKE TARGET ################################
# default target: print usage message and quit
current:
	@echo "[chump build]: please use one of the following configurations:"
	@echo "   make mac, make linux, make win"

# creates build-release
build-release:
	meson setup builddir-release

build-debug:
	meson setup --buildtype=debug --debug builddir-debug -Db_coverage=true

build-release-win:
	meson setup --buildtype=release builddir-release --backend vs

build-release-mac:
	meson setup --buildtype=release builddir-release --backend xcode

setup-mac-x86_64:
	meson setup --buildtype=release --cross-file cross/x86_64-macos.txt builddir-x86_64

setup-mac-arm64:
	meson setup --buildtype=release --cross-file cross/arm64-macos.txt builddir-arm64

build-mac-x86_64: setup-mac-x86_64
	meson compile -C builddir-x86_64

build-mac-arm64: setup-mac-arm64
	meson compile -C builddir-arm64

install:
	meson install -C builddir-release

install-mac:
	meson install -C builddir-arm64

coverage: build-debug
	ninja coverage -C builddir-debug

.PHONY: linux linux-oss linux-jack linux-alsa linux-all
linux linux-oss linux-jack linux-alsa linux-all: build-release
	meson compile -C builddir-release

.PHONY: mac osx
mac osx: mac-universal

linux-debug: build-debug
	meson compile -C builddir-debug

mac-universal: build-mac-x86_64 build-mac-arm64
	pwd
	lipo -create -output chump ./builddir-x86_64/chump-cli/chump ./builddir-arm64/chump-cli/chump
	lipo -create -output Chumpinate.chug builddir-x86_64/chumpinate/Chumpinate.chug builddir-arm64/chumpinate/Chumpinate.chug

.PHONY: win win32 win64
win win32 win64: build-release-win
	meson compile -C builddir-release

test:
	meson test -C builddir-release -v chump:

test-mac:
	meson test -C builddir-arm64 -v chump:

# use clang format for c++ code
format:
	clang-format --style=llvm -i tests/*.cpp
	clang-format --style=llvm -i src/*.cpp
	clang-format --style=llvm -i chump-cli/*.cpp
	clang-format --style=llvm -i chumpinate/*.cpp
	clang-format --style=llvm -i include/*.h
	clang-format --style=llvm -i scripts/*.h
	# clang-format --style=llvm -i scripts/*.cpp
	clang-format --style=llvm -i scripts/generate_manifest.cpp

chumpinate_pkg_linux: linux chumpinate_ckdoc
	cd chumpinate; chuck -s build-pkg-linux.ck

chumpinate_pkg_win: win chumpinate_ckdoc
	cd chumpinate; chuck -s build-pkg-win.ck

chumpinate_pkg_mac: mac chumpinate_ckdoc
	cd chumpinate; chuck -s build-pkg-mac.ck

chumpinate_ckdoc:
	cd chumpinate; chuck -s --chugin-path:../builddir-release/chumpinate gen-ckdoc.ck

chumpinate_install_local: chumpinate_pkg_linux
	chump install-local ./chumpinate/Chumpinate/package.json chumpinate/Chumpinate/0.1.0/Chumpinate_linux.json ./chumpinate/Chumpinate_linux.zip

clean:
ifneq ("$(wildcard builddir-release)","")
	meson compile -C builddir-release --clean
endif
ifneq ("$(wildcard builddir-debug)","")
	meson compile -C builddir-debug --clean
endif
	rm -rf chump Chumpinate.chug

clean-all:
	rm -rf builddir-release builddir-debug builddir-x86_64 builddir-arm64 chump Chumpinate.chug
