#!/usr/bin/env bash

# update.sh
#
# This script updates to latest clones of chuck and chugins

CHUCK_REPO=https://github.com/ccrma/chuck.git
CHUGINS_REPO=https://github.com/ccrma/chugins.git
PROJECTS_DIR=source/projects


function update_chuck() {
	git clone ${CHUCK_REPO} chuck-src && \
	mkdir -p ${PROJECTS_DIR}/chuck-new && \
	mv chuck-src/src/core ${PROJECTS_DIR}/chuck-new/ && \
	mv chuck-src/src/host ${PROJECTS_DIR}/chuck-new/ && \
	rm -rf chuck-src && \
	cp ${PROJECTS_DIR}/chuck/CMakeLists.txt ${PROJECTS_DIR}/chuck-new/ && \
	cp ${PROJECTS_DIR}/chuck/core/CMakeLists.txt ${PROJECTS_DIR}/chuck-new/core/ && \
	cp ${PROJECTS_DIR}/chuck/host/CMakeLists.txt ${PROJECTS_DIR}/chuck-new/host/ && \
	cp -rf ${PROJECTS_DIR}/chuck/host_embed ${PROJECTS_DIR}/chuck-new/ &&  \
	mv ${PROJECTS_DIR}/chuck ${PROJECTS_DIR}/chuck-old && \
	mv ${PROJECTS_DIR}/chuck-new ${PROJECTS_DIR}/chuck
}



function move_to_new() {
	mv chugins-src/"$1" ${PROJECTS_DIR}/chugins-new/"$1"
}

function update_new_chugin() {
	move_to_new "$1" && \
	cp ${PROJECTS_DIR}/chugins/"$1"/CMakeLists.txt ${PROJECTS_DIR}/chugins-new/"$1" && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/makefile* && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/*.dsw && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/*.dsp && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/*.xcodeproj && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/*.vcxproj && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/*.sln && \
	rm -rf ${PROJECTS_DIR}/chugins-new/"$1"/.gitignore
}


function update() {
	update_chuck
	rm -rf ${PROJECTS_DIR}/chuck-old
	rm -rf ${PROJECTS_DIR}/chugins-old
}

update


