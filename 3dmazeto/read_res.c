#include <stdlib.h>
#include <string.h>

#include "read_res.h"

const unsigned char const resMagic[] = {0xA3, 0xA2, 0xA1, 0xA0};

int readImageData(ResContext *c) {
  unsigned int compPos;
  unsigned int decompPos;
  unsigned char cmd;
  unsigned char count;
  unsigned char color;
  
  compPos = 0;
  decompPos = 0;
  
  while(compPos < c->hdr.compDataSize) {
    cmd = c->compData[compPos];
    compPos++;
    
    if(cmd == 0) {
      if(compPos >= c->hdr.compDataSize) return(-1);
      count = c->compData[compPos] - 2;
      compPos++;
      
      if(compPos > c->hdr.compDataSize - count) return(-1);
      if(decompPos > (c->hdr.width * c->hdr.height) - count) return(-1);
      memcpy(&(c->imageData[decompPos]), &(c->compData[compPos]), count);
      compPos += count;
      decompPos += count;
    } else {
      if(compPos >= c->hdr.compDataSize) return(-1);
      color = c->compData[compPos];
      compPos++;
      
      if(decompPos > (c->hdr.width * c->hdr.height) - cmd) return(-1);
      memset(&(c->imageData[decompPos]), color, cmd);
      decompPos += cmd;
    }
  }
  
  return(0);
}

ResContext *readResource(FILE *in) {
  ResContext *c;
  
  c = malloc(sizeof(ResContext));
  if(c == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error0;
  }

  if(fread(&(c->hdr), 1, sizeof(ResHdr), in) < sizeof(ResHdr)) {
    fprintf(stderr, "Failed to read header.\n");
    goto error1;
  }
  
  if(memcmp(c->hdr.magic, resMagic, sizeof(resMagic)) != 0) {
    fprintf(stderr, "Bad signature.\n");
    goto error1;
  }
  
  if(fread(c->palette, 1, sizeof(PaletteEntry) * PALETTESIZE, in) <
     sizeof(PaletteEntry) * PALETTESIZE) {
    fprintf(stderr, "Failed to read palette.\n");
    goto error1;
  }
  
  c->hdr.compDataSize -= 2; // 2 bytes of junk at the end
  
  c->compData = malloc(c->hdr.compDataSize);
  if(c->compData == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error1;
  }
  
  if(fread(c->compData, 1, c->hdr.compDataSize, in) < c->hdr.compDataSize) {
    fprintf(stderr, "Failed to read compressed data.\n");
    goto error2;
  }
  
  c->imageData = malloc(c->hdr.width * c->hdr.height);
  if(c->imageData == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error2;
  }
  
  if(readImageData(c) < 0) {
    fprintf(stderr, "Failed to decompress data.\n");
    goto error3;
  }
  
  return(c);
  
error3:
  free(c->imageData);
error2:
  free(c->compData);
error1:
  free(c);
error0:
  return(NULL);
}

void freeResource(ResContext *c) {
  free(c->imageData);
  free(c->compData);
  free(c);
}
