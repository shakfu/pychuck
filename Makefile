PROJECT_NAME = numchuck
VERSION = 0.1.9

PLATFORM = $(shell uname)
CONFIG = Release
ROOT := $(PWD)
BUILD := $(ROOT)/build
SCRIPTS := $(ROOT)/scripts
THIRDPARTY = $(ROOT)/thirdparty
LIB = $(THIRDPARTY)/install/lib
CHUCK = $(THIRDPARTY)/install/bin/chuck
DIST = $(BUILD)/dist/$(PROJECT_NAME)
ARCH=$(shell uname -m)

# variants
BUNDLED=0
MULTI=0
UNIVERSAL=0

ifeq ($(PLATFORM), Darwin)
OS = "macos"
GENERATOR ?= "-GXcode"
ifeq ($(UNIVERSAL), 1)
DIST_NAME = $(PROJECT_NAME)-$(VERSION)-macos-universal
EXTRA_OPTIONS += -DCM_MACOS_UNIVERSAL=ON
endif
else
OS = "windows"
GENERATOR ?= ""
endif

DIST_NAME = $(PROJECT_NAME)-$(VERSION)-$(OS)-$(ARCH)
DMG = $(DIST_NAME).dmg
ZIP = $(DIST_NAME).zip


.PHONY: all build clean test coverage install repl snap typecheck lint format \
		qa check publish publish-test test-review

all: build

build:
	@uv sync --reinstall-package numchuck

clean:
	@rm -rf build

test:
	@uv run pytest

test-review:
	@uv run pytest --review

coverage:
	@uv run pytest --cov=numchuck --cov-report term-missing:skip-covered --cov-report=html

repl:
	@uv run numchuck repl

snap:
	@git add --all . && git commit -m 'snap' && git push

typecheck:
	@uv run mypy --strict src/

lint:
	@uv run ruff check --fix src/

format:
	@uv run ruff format src/

qa: test lint typecheck format

check:
	@uv run twine check dist/*.whl

publish-test: check
	@uv run twine upload -r testpypi dist/*

publish: check
	@uv run twine upload dist/*
