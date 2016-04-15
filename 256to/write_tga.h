#include <stdio.h>
#include <stdlib.h>

#define TGA_ATTRIBUTE_ALPHA_MASK  (0x0F)
#define TGA_ATTRIBUTE_NO_ALPHA    (0x00)
#define TGA_ATTRIBUTE_16BIT_TRANS (0x01)
#define TGA_ATTRIBUTE_32BIT_ALPHA (0x08)

#define TGA_ATTRIBUTE_ORIGIN_MASK (0x30)
#define TGA_ATTRIBUTE_ORIGIN_0    (0x00)
#define TGA_ATTRIBUTE_ORIGIN_1    (0x10)
#define TGA_ATTRIBUTE_ORIGIN_2    (0x20)
#define TGA_ATTRIBUTE_ORIGIN_3    (0x30)

typedef struct __attribute__((packed, aligned(1))) {
  unsigned char IDLength;        /* 00h  Size of Image ID field */
  unsigned char ColorMapType;    /* 01h  Color map type */
  unsigned char ImageType;       /* 02h  Image type code */
  unsigned short CMapStart;      /* 03h  Color map origin */
  unsigned short CMapLength;     /* 05h  Color map length */
  unsigned char CMapDepth;       /* 07h  Depth of color map entries */
  unsigned short XOffset;        /* 08h  X origin of image */
  unsigned short YOffset;        /* 0Ah  Y origin of image */
  unsigned short Width;          /* 0Ch  Width of image */
  unsigned short Height;         /* 0Eh  Height of image */
  unsigned char PixelDepth;      /* 10h  Image pixel size */
  unsigned char ImageDescriptor; /* 11h  Image descriptor byte */
} TGAHeader;

typedef struct {
  TGAHeader hdr;
  
  unsigned char *palette;
  
  unsigned char *data;
} TGAContext;

TGAContext *TGA_createFromData(unsigned char *data, unsigned char *palette,
                               unsigned short CMapLength, unsigned short width,
                               unsigned short height);
void TGA_free(TGAContext *c);
int TGA_write(TGAContext *c, FILE *out);
