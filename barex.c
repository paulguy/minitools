#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FILENAME_SIZE (FILENAME_MAX + 1)
#define BUFFERSIZE (1024)

const char const outSuffix[] = ".data";
// probably some fields in here but all the files I see have this the same...
const char const magic[] = {0x11, 0x00, 0x01, 0x00, 0x01, 0x00};

typedef struct __attribute__((packed, aligned(1))) {
  char magic[6];
  unsigned short unkTableSize;
  unsigned int unk0; // always 0x20?
  unsigned int unk1;
  unsigned int idxTableStart;
  unsigned int idxTableSize;
  unsigned int dataStart;
  unsigned int dataSize;
} BARFile;

int main(int argc, char **argv) {
  FILE *in, *out;
  char outPrefix[FILENAME_SIZE];
  char outName[FILENAME_SIZE];
  int fileNumDigits;
  int temp;
  unsigned int *idx;
  int i;
  char buffer[BUFFERSIZE];
  unsigned int start, length, copied;
  
  BARFile header;
  
  if(argc < 2) {
    fprintf(stderr, "USAGE: %s <BAR file>\n", argv[0]);
    goto error0;
  }
  
  in = fopen(argv[1], "rb");
  if(in == NULL) {
    fprintf(stderr, "Couldn't open %s for read.\n", argv[1]);
    goto error0;
  }
  
  // Read header
  if(fread(&header, 1, sizeof(BARFile), in) != sizeof(BARFile)) {
    fprintf(stderr, "Couldn't read header.\n");
    goto error1;
  }
  
  // Check magic
  if(memcmp(magic, &(header.magic), sizeof(magic)) != 0) {
    fprintf(stderr, "Bad magic.\n");
    goto error1;
  }
  
  // Get the output name prefix
  temp = strrchr(argv[1], '.') - argv[1];
  memcpy(outPrefix, argv[1], temp);
  outPrefix[temp] = '\0';

  // Get digits needed for file number field
  temp = header.idxTableSize;
  for(fileNumDigits = 1; ; fileNumDigits++) {
    temp /= 10;
    if(temp == 0) {
      break;
    }
  }
  
  // Check if filename fields would exceed filename buffer size
  temp = strrchr(argv[1], '.') - argv[1];
  if(strlen(outPrefix) + fileNumDigits + strlen(outSuffix) + 1 > FILENAME_SIZE) {
    fprintf(stderr, "Original filename length too long.\n");
    goto error1;
  }

  // Allocate memory for index table.  One extra for file end entry.
  idx = malloc(sizeof(unsigned int) * (header.idxTableSize + 1));
  if(idx == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error1;
  }

  // Seek to index table
  if(fseek(in, header.idxTableStart, SEEK_SET) == -1) {
    fprintf(stderr, "Failed to seek: %s.\n", strerror(errno));
    goto error1;
  }
  
  // Read index table
  if(fread(idx, 1, sizeof(int) * (header.idxTableSize + 1), in) !=
                   sizeof(int) * (header.idxTableSize + 1)) {
    fprintf(stderr, "Failed to read index table.\n");
    goto error2;
  }
  
  for(i = 0; i < header.idxTableSize; i++) {
    snprintf(outName, FILENAME_SIZE, "%s%0*d%s", outPrefix, fileNumDigits, i, outSuffix);
    fprintf(stderr, "Writing %s... ", outName);

    start = idx[i];
    length = idx[i + 1] - idx[i];
    if(fseek(in, start, SEEK_SET) == -1) {
      fprintf(stderr, "Failed to seek: %s.\n", strerror(errno));
      goto error2;
    }
    
    out = fopen(outName, "wb");
    if(out == NULL) {
      fprintf(stderr, "Failed to open %s for writing.", outName);
      goto error2;
    }
    
    copied = 0;
    while(copied < length) {
      int dataRead;
      
      dataRead = fread(buffer, 1, BUFFERSIZE, in);
      if(dataRead == 0) {
        fprintf(stderr, "Didn't read anything?  Shouldn't happen.  Short file, maybe.\n");
        goto error3;
      }
      copied += dataRead;
      if(fwrite(buffer, 1, dataRead, out) != dataRead) {
        fprintf(stderr, "Failed to write.\n");
        goto error3;
      }
    }
    
    fprintf(stderr, "Done.\n");
    fclose(out);
  }

  fprintf(stderr, "All done!\n");
  free(idx);
  fclose(in);
  return(EXIT_SUCCESS);

error3:
  fclose(out);
error2:
  free(idx);
error1:
  fclose(in);
error0:
  return(EXIT_FAILURE);
}
