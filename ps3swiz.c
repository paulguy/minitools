#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wand/MagickWand.h>

#define MAXTEXSIZE (65536)

#define ThrowWandException(wand) \
{ \
  char *description; \
 \
  ExceptionType severity; \
 \
  description = MagickGetException(wand, &severity); \
  (void) fprintf(stderr,"%s %s %lu %s\n", GetMagickModule(), description); \
  description = (char *)MagickRelinquishMemory(description); \
}

int _getSrcPos(int size, int x, int y) {
  //printf("%d %d %d, ", size, x, y);
/*  if(size == 2) {
    if(x == 0) {
      if(y == 0) {
        return(0); // 0, 0
      }
      return(2); // 0, 1
    } else {
      if(y == 0) {
        return(1); // 1, 0
      }
    }
    
    return(3); // 1, 1
  }
*/
  if(size == 4)
    return(0);

  if(x < size / 2) {
    if(y < size / 2) {
      // top left quadrant
      return(_getSrcPos(size / 2, x, y));
    } else { // y >= size / 2
      // bottom left quadrant
      return(_getSrcPos(size / 2, x, y - size / 2) + (size * size / 2));
    }
  } else { // x >= size / 2
    if(y < size / 2) {
      // top right quadrant
      return(_getSrcPos(size / 2, x - size / 2, y) + (size * size / 4));
    }
  }
  // x >= size / 2 && y >= size / 2, prevent compiler from complaining.
  
  // bottom right quadrant
  return(_getSrcPos(size / 2, x - size / 2, y - size / 2) + (size * size / 4 * 3));
}

int getSrcPos(int width, int height, int x, int y) {
  if(width > height) { // wide
    return(_getSrcPos(height, x - ((x / height) * height), y)
           + ((x / height) * height));
  } else if(width < height) { // tall
    return(_getSrcPos(height, x, y - ((y / width) * width))
           + (((y / width) * width) * width));
  }
  
  // square
  return(_getSrcPos(width, x, y));
}

void swiz2(int *in, int *out, int width, int height) {
  int x, y, srcpos;
  
  for(y = 0; y < height; y+=4) {
    for(x = 0; x < width; x+=4) {
      srcpos = getSrcPos(width, height, x, y);
      out[y * width + x] = in[srcpos];
      out[y * width + x + 1] = in[srcpos+1];
      out[(y + 1) * width + x] = in[srcpos+2];
      out[(y + 1) * width + x + 1] = in[srcpos+3];
      out[y * width + x + 2] = in[srcpos+4];
      out[y * width + x + 1 + 2] = in[srcpos+5];
      out[(y + 1) * width + x + 2] = in[srcpos+6];
      out[(y + 1) * width + x + 1 + 2] = in[srcpos+7];
      out[(y + 2) * width + x] = in[srcpos+8];
      out[(y + 2) * width + x + 1] = in[srcpos+9];
      out[(y + 1 + 2) * width + x] = in[srcpos+10];
      out[(y + 1 + 2) * width + x + 1] = in[srcpos+11];
      out[(y + 2) * width + x + 2] = in[srcpos+12];
      out[(y + 2) * width + x + 1 + 2] = in[srcpos+13];
      out[(y + 1 + 2) * width + x + 2] = in[srcpos+14];
      out[(y + 1 + 2) * width + x + 1 + 2] = in[srcpos+15];
    }
  }
}

int main(int argc, char **argv) {
  MagickBooleanType status;

  MagickWand *magick_wand;
  size_t width, height;
  int *srcpixels, *destpixels;
  
  unsigned int i;

  if (argc != 3) {
    (void) fprintf(stdout,"Usage: %s in out\n",argv[0]);
    exit(0);
  }
  
  MagickWandGenesis();
  magick_wand = NewMagickWand();
  status = MagickReadImage(magick_wand, argv[1]);
  if (status == MagickFalse) {
    ThrowWandException(magick_wand);
    goto error0;
  }
  
  // Get first image and dump dimensions and pixels in to RGBA format.
  MagickResetIterator(magick_wand);
  width = MagickGetImageWidth(magick_wand);
  height = MagickGetImageHeight(magick_wand);
  for(i = 1; i < MAXTEXSIZE*2; i *= 2) {
    if(width == i)
      break;
  }
  if(i == MAXTEXSIZE*2) {
    fprintf(stderr, "Texture dimensions must be a power of 2.");
    MagickWandTerminus();
    goto error0;
  }
  for(i = 1; i < MAXTEXSIZE*2; i *= 2) {
    if(height == i)
      break;
  }
  if(i == MAXTEXSIZE*2) {
    fprintf(stderr, "Texture dimensions must be a power of 2.");
    MagickWandTerminus();
    goto error0;
  }
  srcpixels = malloc(width * height * sizeof(int));
  if(srcpixels == NULL) {
    MagickWandTerminus();
    goto error0;
  }
  destpixels = malloc(width * height * sizeof(int));
  if(destpixels == NULL) {
    MagickWandTerminus();
    free(srcpixels);
    goto error0;
  }
  
  // get pixel data then swizzle it.
  status = MagickExportImagePixels(magick_wand, 0, 0, width, height, "RGBA", CharPixel, srcpixels);
  if(status == MagickFalse) {
    ThrowWandException(magick_wand);
    goto error1;
  }

  memset(destpixels, 0x80, width * height * 4);
  swiz2(srcpixels, destpixels, width, height);

  // insert it back in and save.
  status = MagickImportImagePixels(magick_wand, 0, 0, width, height, "RGBA", CharPixel, destpixels);
  if(status == MagickFalse) {
    ThrowWandException(magick_wand);
    goto error1;
  }

  status = MagickWriteImages(magick_wand, argv[2], MagickTrue);
  if(status == MagickFalse) {
    ThrowWandException(magick_wand);
    goto error1;
  }
  magick_wand = DestroyMagickWand(magick_wand);

  free(srcpixels);
  free(destpixels);
  MagickWandTerminus();
  return(0);

error1:
  free(srcpixels);
  free(destpixels);
error0:
  return(-1);
}
