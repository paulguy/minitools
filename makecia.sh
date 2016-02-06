#!/bin/sh

DIR=$(dirname "$1")
BASENAME=${DIR}/$(basename -s .cci "$1")
EXHEADERFILE=${DIR}/exheader.bin
RSFFILE=${BASENAME}.rsf
CXIFILE=${BASENAME}.cxi
CIAFILE=${BASENAME}.cia

echo "Directory: ${DIR}"
echo "Base name: ${BASENAME}"
echo "ExHeader file: ${EXHEADERFILE}"
echo "RSF File: ${RSFFILE}"
echo "CXI File: ${CXIFILE}"

set -x
python3 /home/paul/3ds/rsfgen.py "$1" "${EXHEADERFILE}" >"${RSFFILE}"
/home/paul/3ds/Project_CTR/makerom/makerom -f ncch -icon "${DIR}/exefs/icon.bin" \
-banner "${DIR}/exefs/banner.bin" -exefslogo -code "${DIR}/exefs/code.bin" \
-exheader "${DIR}/exheader.bin" -plainrgn "${DIR}/plainrgn.bin" -romfs \
"${DIR}/romfs.bin" -rsf "${RSFFILE}" -o "${CXIFILE}"
/home/paul/3ds/Project_CTR/makerom/makerom -f cia -content "${CXIFILE}:0" \
-o "${CIAFILE}"
#rm "${RSFFILE}" "${CXIFILE}"
