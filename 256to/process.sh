for FILE in *.raw; do
  BASENAME=$(basename -s .raw ${FILE})
  echo "Processing ${BASENAME}.raw..."
  mkdir "${BASENAME}"
  cd "${BASENAME}"
  ../../../256to/256to ../${FILE} >report.txt
  cd ..
done
