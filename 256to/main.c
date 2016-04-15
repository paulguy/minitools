#include <stdio.h>
#include <stdlib.h>

#include "read_256.h"
#include "write_tga.h"

int main(int argc, char **argv) {
  ShapesContext *c;
  TGAContext *t;
  Image *img;
  PaletteEntry **pal;
  unsigned char *imgData;
  FILE *in, *out;
  short int images, palettes, palsize;
  unsigned char palette[1024];
  unsigned short i, j;
  char tgafile[] = "pal#####_gfx#####.tga";
  
  if(argc < 2) {
    fprintf(stderr, "USAGE: %s <Shapes file>\n", argv[0]);
    goto error0;
  }

  fprintf(stderr, "Loading shapes from %s.\n",  argv[1]);
  in = fopen(argv[1], "rb");
  if(in == NULL) {
    fprintf(stderr, "Failed to open %s for read.\n", argv[1]);
    goto error0;
  }
  
  c = loadShapes(in);
  if(c == NULL) {
    fprintf(stderr, "Failed to load shapes from %s.\n", argv[1]);
    fclose(in);
    goto error0;
  }
  
  fclose(in);
  
  printShapesContext(c);
  
  fprintf(stderr, "Writing TGA files.\n");
  images = getImagesCount(c);
  palettes = getPaletteCount(c);
  palsize = getPaletteSize(c);
  for(i = 0; i < palettes; i++) {
    pal = getPalette(c, i);
    for(j = 0; j < palsize; j++) {
      palette[j * 4 + 0] = pal[j]->blue;
      palette[j * 4 + 1] = pal[j]->green;
      palette[j * 4 + 2] = pal[j]->red;
      palette[j * 4 + 3] = 255;
    }

    for(j = 0; j < images; j++) {
      snprintf(tgafile, sizeof(tgafile), "pal%05hd_gfx%05hd.tga", i, j);

      out = fopen(tgafile, "wb");
      if(out == NULL) {
        goto error1;
      }
      
      img = getImage(c, j);
      if(img == NULL) {
        fprintf(stderr, "Couldn't get image %d.\n", j);
        goto error2;
      }
      imgData = getImageData(c, j);
      if(imgData == NULL) {
        fprintf(stderr, "Couldn't get image data %d.\n", j);
        goto error2;
      }

      t = TGA_createFromData(imgData, palette, palsize, img->width, img->height);
      if(TGA_write(t, out) < 0) {
        fprintf(stderr, "Failed to write TGA to %s.\n", tgafile);
        goto error2;
      }
      fclose(out);
    }
  }
  
  freeShapesContext(c);

  return(EXIT_SUCCESS);

error2:
  fclose(out);
error1:
  freeShapesContext(c);
error0:
  return(EXIT_FAILURE);
}
