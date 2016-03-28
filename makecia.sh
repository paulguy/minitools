#!/bin/sh

DIR=$(dirname "$1")
BASENAME=${DIR}/$(basename -s .cci "$1")
CIAFILE=${BASENAME}.cia

echo "Directory: ${DIR}"
echo "Input file: $1"
echo "Base name: ${BASENAME}"
echo "Output File: ${CIAFILE}"

echo "Generating main application RSF..."
python3 ../rsfgen.py --romfsdir "${DIR}/mainromfs" "$1" >"${BASENAME}_main.rsf"

echo "Generating manual RSF..."
python3 ../rsfgen.py --partition 1 --romfsdir "${DIR}/manualromfs" "$1" \
>"${BASENAME}_manual.rsf"

[ -d dlpromfs ] && (echo "Generating download play RSF..." ; \
python3 ../rsfgen.py --partition 2 --romfsdir "${DIR}/manualromfs" "$1" \
>"${BASENAME}_dlp.rsf")

echo "Building main application CXI..."
../Project_CTR/makerom/makerom -f ncch -icon "${DIR}/mainexefs/icon.bin" \
-banner "${DIR}/mainexefs/banner.bin" -exefslogo -code "${DIR}/mainexefs/code.bin" \
-exheader "${DIR}/exheader.bin" -plainrgn "${DIR}/plainrgn.bin" \
-rsf "${BASENAME}_main.rsf" -o "${BASENAME}_main.cxi"

echo "Building manual CXI..."
../Project_CTR/makerom/makerom -f ncch -rsf "${BASENAME}_manual.rsf" \
-o "${BASENAME}_manual.cxi"

[ -d dlpromfs ] && (echo "Building download play CXI..." ; \
../Project_CTR/makerom/makerom -f ncch -rsf "${BASENAME}_dlp.rsf" \
-o "${BASENAME}_dlp.cxi")

[ -d dlpromfs ] && (echo "Building CIA with download play..." ; \
../Project_CTR/makerom/makerom -f cia -content "${BASENAME}_main.cxi:0" \
-content "${BASENAME}_manual.cxi:1" -content "${BASENAME}_dlp.cxi:2" -o "${CIAFILE}")
[ ! -d dlpromfs ] && (echo "Building CIA..." ; \
../Project_CTR/makerom/makerom -f cia -content "${BASENAME}_main.cxi:0" \
-content "${BASENAME}_manual.cxi:1" -o "${CIAFILE}")
