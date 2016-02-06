#!/bin/sh

DIR=$(dirname "$1")

echo "Directory: ${DIR}"

set -x
../Project_CTR/ctrtool/ctrtool -x --exheader="${DIR}/exheader.bin" \
--plainrgn=${DIR}/plainrgn.bin --exefsdir="${DIR}/exefs" --romfs="${DIR}/romfs.bin" \
--decompresscode $1
