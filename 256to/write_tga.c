#include "write_tga.h"

TGAContext *TGA_createFromData(unsigned char *data, unsigned char *palette,
                               unsigned short CMapLength, unsigned short width,
                               unsigned short height) {
  TGAContext *c;
  
  if(CMapLength > 256) {
    return(NULL);
  }
  
  c = malloc(sizeof(TGAContext));
  if(c == NULL) {
    return(NULL);
  }
  
  c->palette = palette;
  c->data = data;
  
  c->hdr.IDLength = 0; // no ID fields
  c->hdr.ColorMapType = 1; // normal colormap
  c->hdr.ImageType = 1; // uncompressed colormapped data
  c->hdr.CMapStart = 0; // follows header
  c->hdr.CMapLength = CMapLength;
  c->hdr.CMapDepth = 32; // RGBA
  c->hdr.XOffset = 0; // not clear what this does
  c->hdr.YOffset = 0;
  c->hdr.Width = width;
  c->hdr.Height = height;
  c->hdr.PixelDepth = 8;
  c->hdr.ImageDescriptor = TGA_ATTRIBUTE_32BIT_ALPHA | TGA_ATTRIBUTE_ORIGIN_2;

  return(c);
}

void TGA_free(TGAContext *c) {
  free(c);
}

int TGA_write(TGAContext *c, FILE *out) {
  if(fwrite(&(c->hdr), 1, sizeof(TGAHeader), out) < sizeof(TGAHeader)) {
    return(-1);
  }
  
  if(fwrite(c->palette, 1, c->hdr.CMapLength * 4, out) < c->hdr.CMapLength * 4) {
    return(-1);
  }
  
  if(fwrite(c->data, 1, c->hdr.Width * c->hdr.Height, out) <
     (unsigned short)(c->hdr.Width * c->hdr.Height)) {
    return(-1);
  }
  
  return(0);
}
