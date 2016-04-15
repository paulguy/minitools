#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PALETTE_ENTRY_SELFLUMINESCENT (0x80)

typedef struct __attribute__((packed, aligned(1))) {
  unsigned char flags;
  unsigned char num; // 0 indexed order
  unsigned short int red;
  unsigned short int green;
  unsigned short int blue;
} PaletteEntry;

#define IMAGE_DIRECTION_MASK (0x80)
#define IMAGE_DIRECTION_LEFT_RIGHT (0x80)
#define IMAGE_DIRECTION_TOP_DOWN (0x00)
#define IMAGE_TRANSPARENCY (0x40)

typedef struct __attribute__((packed, aligned(1))) {
  short int width;
  short int height;
  short int bytesPerLine;
  short int flags;
  short int bitDepth; // 8
  char padding[16];
} Image;
// additional useless values of width * 4 + 4 whcih are normally calculated at
// runtime

#define LOW_LEVEL_SHAPE_XMIRROR     (0x8000)
#define LOW_LEVEL_SHAPE_YMIRROR     (0x4000)
#define LOW_LEVEL_SHAPE_KEYOBSCURE  (0x2000)

typedef struct __attribute__((packed, aligned(1))) {
  unsigned short int flags;
  
  int minLightIntensity;
  
  short int imageIndex; // Index to an image
  
  short int xOrigin;
  short int yOrigin;
  
  short int xKey;
  short int yKey;
  
  short int left;
  short int right;
  short int top;
  short int bottom;
  
  short int worldXOrigin;
  short int worldYOrigin;
  
  char padding[8];
} LowLevelShape;

typedef struct __attribute__((packed, aligned(1))) {
  short int type; // 0
  unsigned short int flags; // 0
  
  unsigned char nameLen;
  char name[33];
  
  short int nViews; // rotational views
  short int nFrames; // frames per animation
  short int animDelay; // ticks per frame
  
  short int keyFrame; // "special" frame
  
  short int transferMode;
  short int transferModePeriod; // no documentation
  
  short int firstFrameSound;
  short int keyFrameSound;
  short int lastFrameSound; // sound resources played at certain times
  
  short int scaleFactor; // also dunno
  
  char padding[30];
} HighLevelShape;
// followed by indexes to LowLevelShapes, for real views count * nFrames.
// nViews can't be used directly, it needs to be converted.

typedef enum {
  SHAPE_CLASS_INVALID = 0,
  SHAPE_CLASS_TEXTURE,
  SHAPE_CLASS_SPRITE,
  SHAPE_CLASS_INTERFACE,
  SHAPE_CLASS_SCENERY
} ShapeType;

typedef struct __attribute__((packed, aligned(1))) {
  short int version; // 3
  ShapeType type:16; // short int
  
  unsigned short int flags;
  
  short int nColors; // colors per palette
  short int nPalettes; // palettes
  int palettesOffset; // start of palettes
  
  unsigned short int nHighShapes; // "high level" shapes (animations)
  int highShapesTablesOffset; // start of "high level" shapes descripters pointers
  
  short int nLowShapes; // "low level" shapes (individual graphics)
  int lowShapesTablesOffset; // start of "low level" shapes descripters pointers
  
  short int nImages; // actual graphics
  int imagesTablesOffsets; // start of pointers to graphics
  
  short int scaleFactor; // i dunno
  int size; // total size
  
  char padding[506];
} ShapesHeader;

typedef struct {
  FILE *in;
  
  ShapesHeader *hdr;
  
  char *highShapesMem;
  HighLevelShape **highShapes;
  
  char *lowShapesMem;
  LowLevelShape **lowShapes;
  
  char *imagesMem;
  Image **images;

  unsigned char *palettesMem;
  PaletteEntry **paletteArraysMem;
  PaletteEntry ***palettes;
  
  // hdr->nHighShapes
  short *animationsMem;
  short **animationsArrayMem;
  short ***views;

  // hdr->nImages
  unsigned char *bitmapsMem;
  unsigned char **bitmaps;
} ShapesContext;

#define MAX_VIEWS (8)

extern const short int nViewsToRealCount[12];
#define GET_REAL_VIEW_COUNT(X) (X->nViews > 0 && X->nViews < 12 ? nViewsToRealCount[X->nViews] : -1)

ShapesContext *loadShapes(FILE *in);
void freeShapesContext(ShapesContext *c);
void printShapesContext(ShapesContext *c);
int getImagesCount(ShapesContext *c);
Image *getImage(ShapesContext *c, short int i);
unsigned char *getImageData(ShapesContext *c, short int i);
int getPaletteCount(ShapesContext *c);
PaletteEntry **getPalette(ShapesContext *c, short int i);
int getPaletteSize(ShapesContext *c);
