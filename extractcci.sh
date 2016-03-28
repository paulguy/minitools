#!/bin/sh

DIR=$(dirname "$1")

echo "Directory: ${DIR}"

echo "Extracting main application..."
../Project_CTR/ctrtool/ctrtool -x -n 0 --exheader="${DIR}/exheader.bin" \
--plainrgn="${DIR}/plainrgn.bin" --exefsdir="${DIR}/mainexefs" \
--romfsdir="${DIR}/mainromfs" --decompresscode "$1"
echo "Extracting manual..."
../Project_CTR/ctrtool/ctrtool -x -n 1 --romfsdir="${DIR}/manualromfs" "$1"
echo "Extracting download play (This failing is fine if the game doesn't support this..."
../Project_CTR/ctrtool/ctrtool -x -n 2 --romfsdir="${DIR}/dlpromfs" "$1"
