#include <stdio.h>

#define PALETTESIZE (256)

typedef struct __attribute__((packed, aligned(1))) {
  unsigned char magic[4];
  unsigned int width;
  unsigned int height;
  unsigned int unk0;
  unsigned int unk1;
  unsigned int compDataSize;
} ResHdr;

typedef struct __attribute__((packed, aligned(1))) {
  unsigned char red;
  unsigned char green;
  unsigned char blue;
  unsigned char alpha;
} PaletteEntry;

typedef struct {
  ResHdr hdr;
  PaletteEntry palette[sizeof(PaletteEntry) * PALETTESIZE] __attribute__((aligned(1)));
  
  unsigned char *compData;
  unsigned char *imageData;
} ResContext;

ResContext *readResource(FILE *in);
void freeResource(ResContext *c);
