#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "read_res.h"
#include "write_tga.h"

int main(int argc, char **argv) {
  ResContext *c;
  TGAContext *t;
  FILE *in, *out;
  unsigned char palette[sizeof(PaletteEntry) * PALETTESIZE];
  unsigned int i;
  char *extension;
  int basenameSize;
  
  if(argc < 2) {
    fprintf(stderr, "USAGE: %s <resource file>\n", argv[0]);
    return(EXIT_FAILURE);
  }

  fprintf(stderr, "Loading resource from %s.\n",  argv[1]);
  in = fopen(argv[1], "rb");
  if(in == NULL) {
    fprintf(stderr, "Failed to open %s for read.\n", argv[1]);
    return(EXIT_FAILURE);
  }
  
  c = readResource(in);
  if(c == NULL) {
    fprintf(stderr, "Failed to load resource from %s.\n", argv[1]);
    fclose(in);
    return(EXIT_FAILURE);
  }
  
  fclose(in);

  memcpy(palette, c->palette, sizeof(PaletteEntry) * PALETTESIZE);

  for(i = 0; i < PALETTESIZE; i++) {
    palette[i * 4 + 0] = c->palette[i].red;
    palette[i * 4 + 1] = c->palette[i].green;
    palette[i * 4 + 2] = c->palette[i].blue;
    palette[i * 4 + 3] = c->palette[i].alpha;
  }

  extension = strrchr(argv[1], ',');
  if(extension == NULL) {
    basenameSize = strlen(argv[1]);
  } else {
    basenameSize = extension - argv[1];
  }
  
  char basename[basenameSize + 1];
  char tgafile[basenameSize + 5];

  memcpy(basename, argv[1], basenameSize);
  basename[basenameSize] = '\0';
  snprintf(tgafile, basenameSize + 5, "%s.tga", basename);

  out = fopen(tgafile, "wb");
  if(out == NULL) {
    goto error1;
  }
  
  t = TGA_createFromData(c->imageData, palette, PALETTESIZE, c->hdr.width, c->hdr.height);
  if(t == NULL) {
    fprintf(stderr, "Failed to create TGA object.\n");
    goto error2;
  }
  if(TGA_write(t, out) < 0) {
    fprintf(stderr, "Failed to write TGA to %s.\n", tgafile);
    goto error3;
  }

  TGA_free(t);

  fclose(out);
  
  freeResource(c);

  return(EXIT_SUCCESS);

error3:
  TGA_free(t);
error2:
  fclose(out);
error1:
  freeResource(c);

  return(EXIT_FAILURE);
}
