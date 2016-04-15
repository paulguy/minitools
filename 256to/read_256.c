#include "read_256.h"

#define SWAP16(X) \
  X = ((X & 0x00FF) << 8) | \
      ((X & 0xFF00) >> 8); \

#define SWAP32(X) \
  X = ((X & 0x000000FF) << 24) | \
      ((X & 0x0000FF00) <<  8) | \
      ((X & 0x00FF0000) >>  8) | \
      ((X & 0xFF000000) >> 24); \

const short int nViewsToRealCount[12] = {
  -1, 1, 8, 4, 4, 8, -1, -1, 8, 5, 1, 5
}; // -1 are invalid

int readShapesHeader(ShapesContext *c) {
  if(fread(c->hdr, 1, sizeof(ShapesHeader), c->in) < sizeof(ShapesHeader)) {
    return(-1);
  }

  SWAP16(c->hdr->version);
  SWAP16(c->hdr->type);
  SWAP16(c->hdr->nColors);
  SWAP16(c->hdr->nPalettes);
  SWAP32(c->hdr->palettesOffset);
  SWAP16(c->hdr->nHighShapes);
  SWAP32(c->hdr->highShapesTablesOffset);
  SWAP16(c->hdr->nLowShapes);
  SWAP32(c->hdr->lowShapesTablesOffset);
  SWAP16(c->hdr->nImages);
  SWAP32(c->hdr->imagesTablesOffsets);
  SWAP16(c->hdr->scaleFactor);
  SWAP32(c->hdr->size);

  return(0);
}

int readHighLevelShape(ShapesContext *c, int i) {
  if(fread(c->highShapes[i], 1, sizeof(HighLevelShape), c->in) < sizeof(HighLevelShape)) {
    return(-1);
  }
  
  SWAP16(c->highShapes[i]->type);
  SWAP16(c->highShapes[i]->flags);
  SWAP16(c->highShapes[i]->nViews);
  SWAP16(c->highShapes[i]->nFrames);
  SWAP16(c->highShapes[i]->animDelay);
  SWAP16(c->highShapes[i]->keyFrame);
  SWAP16(c->highShapes[i]->transferMode);
  SWAP16(c->highShapes[i]->transferModePeriod);
  SWAP16(c->highShapes[i]->firstFrameSound);
  SWAP16(c->highShapes[i]->keyFrameSound);
  SWAP16(c->highShapes[i]->lastFrameSound);
  SWAP16(c->highShapes[i]->scaleFactor);

  if(GET_REAL_VIEW_COUNT(c->highShapes[i]) == -1) {
    return(-1);
  }

  return(0);
}

int readHighLevelShapes(ShapesContext *c) {
  int i;
  int highOffsets[c->hdr->nHighShapes];
  
  if(fseek(c->in, c->hdr->highShapesTablesOffset, SEEK_SET) < 0) {
    return(-1);
  }
  
  if(fread(highOffsets, 1, c->hdr->nHighShapes * sizeof(int), c->in) <
     c->hdr->nHighShapes * sizeof(int)) {
    return(-1);
  }

  for(i = 0; i < c->hdr->nHighShapes; i++) {
    SWAP32(highOffsets[i]);
    if(fseek(c->in, highOffsets[i], SEEK_SET) < 0) {
      return(-1);
    }
    if(readHighLevelShape(c, i) < 0) {
      return(-1);
    }
  }
  
  return(0);
}

int readAnimations(ShapesContext *c) {
  unsigned int i, j;
  int highOffsets[c->hdr->nHighShapes];
  int curAnimationsMemPtr;
  size_t amountToRead;
  
  if(fseek(c->in, c->hdr->highShapesTablesOffset, SEEK_SET) < 0) {
    return(-1);
  }
  
  if(fread(highOffsets, 1, c->hdr->nHighShapes * sizeof(int), c->in) <
     c->hdr->nHighShapes * sizeof(int)) {
    return(-1);
  }
  
  curAnimationsMemPtr = 0;
  for(i = 0; i < c->hdr->nHighShapes; i++) {
    if(c->highShapes[i]->nFrames == 0)  // No frames so no data to populate
      continue;
    SWAP32(highOffsets[i]);
    if(fseek(c->in, highOffsets[i] + sizeof(HighLevelShape), SEEK_SET) < 0) {
      return(-1);
    }
    amountToRead = c->highShapes[i]->nFrames * GET_REAL_VIEW_COUNT(c->highShapes[i]);
    if(fread(&(c->animationsMem[curAnimationsMemPtr]), 1, amountToRead * sizeof(short), c->in)
       < amountToRead) {
      return(-1);
    }
    for(j = 0; j < amountToRead; j++) {
      SWAP16(c->animationsMem[curAnimationsMemPtr + j]);
    }
    curAnimationsMemPtr += amountToRead;
  }
  
  return(0);
}

int readLowLevelShape(ShapesContext *c, int i) {
  if(fread(c->lowShapes[i], 1, sizeof(LowLevelShape), c->in) < sizeof(LowLevelShape)) {
    return(-1);
  }
  
  SWAP16(c->lowShapes[i]->flags);
  SWAP32(c->lowShapes[i]->minLightIntensity);
  SWAP16(c->lowShapes[i]->imageIndex);
  SWAP16(c->lowShapes[i]->xOrigin);
  SWAP16(c->lowShapes[i]->yOrigin);
  SWAP16(c->lowShapes[i]->xKey);
  SWAP16(c->lowShapes[i]->yKey);
  SWAP16(c->lowShapes[i]->left);
  SWAP16(c->lowShapes[i]->right);
  SWAP16(c->lowShapes[i]->top);
  SWAP16(c->lowShapes[i]->bottom);
  SWAP16(c->lowShapes[i]->worldXOrigin);
  SWAP16(c->lowShapes[i]->worldYOrigin);

  return(0);
}

int readLowLevelShapes(ShapesContext *c) {
  int i;
  int lowOffsets[c->hdr->nLowShapes];
  
  if(fseek(c->in, c->hdr->lowShapesTablesOffset, SEEK_SET) < 0) {
    return(-1);
  }

  if(fread(lowOffsets, 1, c->hdr->nLowShapes * sizeof(int), c->in) <
     c->hdr->nLowShapes * sizeof(int)) {
    return(-1);
  }

  for(i = 0; i < c->hdr->nLowShapes; i++) {
    SWAP32(lowOffsets[i]);
    if(fseek(c->in, lowOffsets[i], SEEK_SET) < 0) {
      return(-1);
    }
    if(readLowLevelShape(c, i) < 0) {
      return(-1);
    }
  }

  return(0);
}

int readImage(ShapesContext *c, int i) {
  if(fread(c->images[i], 1, sizeof(Image), c->in) < sizeof(Image)) {
    return(-1);
  }
  
  SWAP16(c->images[i]->width);
  SWAP16(c->images[i]->height);
  SWAP16(c->images[i]->bytesPerLine);
  SWAP16(c->images[i]->bitDepth);

  return(0);
}

int readImages(ShapesContext *c) {
  int i;
  int imageOffsets[c->hdr->nImages];
  
  if(fseek(c->in, c->hdr->imagesTablesOffsets, SEEK_SET) < 0) {
    return(-1);
  }

  if(fread(imageOffsets, 1, c->hdr->nImages * sizeof(int), c->in) <
     c->hdr->nImages * sizeof(int)) {
    return(-1);
  }

  for(i = 0; i < c->hdr->nImages; i++) {
    SWAP32(imageOffsets[i]);
    if(fseek(c->in, imageOffsets[i], SEEK_SET) < 0) {
      return(-1);
    }
    if(readImage(c, i) < 0) {
      return(-1);
    }
  }
  
  return(0);
}

int readPalettes(ShapesContext *c) {
  PaletteEntry *p;
  int i;
  
  if(fseek(c->in, c->hdr->palettesOffset, SEEK_SET) < 0) {
    return(-1);
  }

  // it's all contiguous both in file and in memory, so just read it all
  // straight in
  if(fread(c->palettesMem, 1, sizeof(PaletteEntry) * c->hdr->nPalettes * c->hdr->nColors, c->in)
     < sizeof(PaletteEntry) * c->hdr->nPalettes * c->hdr->nColors) {
    return(-1);
  }
  
  for(i = 0; i < c->hdr->nPalettes * c->hdr->nColors; i++) {
    p = (PaletteEntry *)&c->palettesMem[i * sizeof(PaletteEntry)];
    SWAP16(p->red);
    SWAP16(p->green);
    SWAP16(p->blue);
  }

  return(0);
}

int readBitmap(ShapesContext *c, int i) {
  int line, pixel;
  short int numlines, numpixels;
  short int cmd;
  int j;

  numlines =
    (c->images[i]->flags & IMAGE_DIRECTION_MASK) == IMAGE_DIRECTION_LEFT_RIGHT ?
    c->images[i]->width : c->images[i]->height;
  numpixels =
    (c->images[i]->flags & IMAGE_DIRECTION_MASK) == IMAGE_DIRECTION_LEFT_RIGHT ?
    c->images[i]->height : c->images[i]->width;
  
  unsigned char linebuffer[numpixels];
  
  for(line = 0; line < numlines; line++) {
    bzero(linebuffer, numpixels);

    if(c->images[i]->bytesPerLine == -1) { // transparent holes
      for(pixel = 0; pixel <= numpixels;) {
        if(fread(&cmd, 1, sizeof(short), c->in) < sizeof(short)) {
          return(-1);
        }
        
        SWAP16(cmd);
        
        if(cmd < 0) {
          if(pixel + -cmd > numpixels) {
            return(-1);
          }
          pixel += -cmd;
        } else if(cmd > 0) {
          if(pixel + cmd > numpixels) {
            return(-1);
          }
          if(fread(&(linebuffer[pixel]), 1, cmd, c->in) 
             < (unsigned short int)cmd) {
            return(-1);
          }
          
          pixel += cmd;
        } else { // cmd == 0
          break;
        }
      }
    } else { // no holes
      if(fread(linebuffer, 1, numpixels, c->in) < (unsigned short int)numpixels) {
        return(-1);
      }
    }
    
    if((c->images[i]->flags & IMAGE_DIRECTION_MASK) == IMAGE_DIRECTION_LEFT_RIGHT) {
      for(j = 0; j < numpixels; j++) {
        c->bitmaps[i][line + (numlines * j)] = linebuffer[j];
      }
    } else {
      memcpy(&(c->bitmaps[i][line * numpixels]), linebuffer, numpixels);
    }
  }
    
    
  
  return(0);
}

int readBitmaps(ShapesContext *c) {
  int i;
  int imageOffsets[c->hdr->nImages];
  int scanlineBlockSize;
  
  if(fseek(c->in, c->hdr->imagesTablesOffsets, SEEK_SET) < 0) {
    return(-1);
  }

  if(fread(imageOffsets, 1, c->hdr->nImages * sizeof(int), c->in) <
     c->hdr->nImages * sizeof(int)) {
    return(-1);
  }

  for(i = 0; i < c->hdr->nImages; i++) {
    SWAP32(imageOffsets[i]);
    scanlineBlockSize = sizeof(Image) +
      ((c->images[i]->flags & IMAGE_DIRECTION_MASK) == IMAGE_DIRECTION_LEFT_RIGHT ?
       c->images[i]->width : c->images[i]->height) * 4 + 4;
    if(fseek(c->in, imageOffsets[i] + scanlineBlockSize, SEEK_SET) < 0) {
      return(-1);
    }
    if(readBitmap(c, i) < 0) {
      return(-1);
    }
  }
  
  return(0);
}

ShapesContext *loadShapes(FILE *in) {
  ShapesContext *c;
  int i, j;
  int animationsMemSize, animationsArraysMemSize;
  int bitmapsMemSize;
  
  c = malloc(sizeof(ShapesContext));
  if(c == NULL) {
    goto error0;
  }

  // header
  c->in = in;
  c->hdr = malloc(sizeof(ShapesHeader));
  if(c->hdr == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error1;
  }
  if(readShapesHeader(c) < 0) {
    fprintf(stderr, "Failed to read shapes header.\n");
    goto error2;
  }

  // high level shapes
  if(c->hdr->nHighShapes > 0) {
    c->highShapesMem = malloc(sizeof(HighLevelShape) * c->hdr->nHighShapes);
    if(c->highShapesMem == NULL) {
      fprintf(stderr, "Failed to allocate memory.\n");
      goto error2;
    }
    c->highShapes = malloc(sizeof(HighLevelShape *) * c->hdr->nHighShapes);
    if(c->highShapes == NULL) {
      fprintf(stderr, "Failed to allocate memory.\n");
      goto error3;
    }
    for(i = 0; i < c->hdr->nHighShapes; i++) {
      c->highShapes[i] = (HighLevelShape *)&(c->highShapesMem[i * sizeof(HighLevelShape)]);
    }
    if(readHighLevelShapes(c) < 0) {
      fprintf(stderr, "Failed to read high level shapes.\n");
      goto error6;
    }
    
    // animations
    
    // views points to an array of pointers pointing to the list of views for each high level shape
    // each list of views points to an array of pointers pointing to an animation for each view
    // each animation contains a pointer to an array of shorts containing indexes to low level shapes

    // determine space needed for data and array pools
    animationsMemSize = 0;
    for(i = 0; i < c->hdr->nHighShapes; i++) {
      animationsMemSize += sizeof(short) *
                           GET_REAL_VIEW_COUNT(c->highShapes[i]) *
                           c->highShapes[i]->nFrames;
    }
    animationsArraysMemSize = 0;
    for(i = 0; i < c->hdr->nHighShapes; i++) {
      animationsArraysMemSize += sizeof(short *) *
                                 GET_REAL_VIEW_COUNT(c->highShapes[i]);
    }
    
    // allocate memory
    c->animationsMem = malloc(animationsMemSize);
    if(c->animationsMem == NULL) {
      fprintf(stderr, "Failed to allocate memory.\n");
      goto error4;
    }
    c->animationsArrayMem = malloc(animationsArraysMemSize);
    if(c->animationsMem == NULL) {
      fprintf(stderr, "Failed to allocate memory.\n");
      goto error5;
    }
    c->views = malloc(sizeof(short **) * c->hdr->nHighShapes);
    if(c->views == NULL) {
      fprintf(stderr, "Failed to allocate memory.\n");
      goto error6;
    }
    
    // point arrays to data
    animationsArraysMemSize = 0;
    animationsMemSize = 0;
    for(i = 0; i < c->hdr->nHighShapes; i++) {
      c->views[i] = &(c->animationsArrayMem[animationsArraysMemSize]);
      
      if(c->highShapes[i]->nFrames > 0)  // oddly, this can be false
        animationsArraysMemSize += GET_REAL_VIEW_COUNT(c->highShapes[i]);
      
      for(j = 0; j < GET_REAL_VIEW_COUNT(c->highShapes[i]); j++) {
        c->views[i][j] = &(c->animationsMem[animationsMemSize]);
        animationsMemSize += c->highShapes[i]->nFrames;
      }
    }
    
    if(readAnimations(c) < 0) {
      fprintf(stderr, "Failed to read animations.\n");
      goto error7;
    }
  }

  // low level shapes
  c->lowShapesMem = malloc(sizeof(LowLevelShape) * c->hdr->nLowShapes);
  if(c->lowShapesMem == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error7;
  }
  c->lowShapes = malloc(sizeof(LowLevelShape *) * c->hdr->nLowShapes);
  if(c->lowShapes == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error8;
  }
  for(i = 0; i < c->hdr->nLowShapes; i++) {
    c->lowShapes[i] = (LowLevelShape *)&(c->lowShapesMem[i * sizeof(LowLevelShape)]);
  }
  if(readLowLevelShapes(c) < 0) {
    fprintf(stderr, "Failed to read low level shapes.\n");
    goto error9;
  }

  // images
  c->imagesMem = malloc(sizeof(Image) * c->hdr->nImages);
  if(c->imagesMem == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error9;
  }
  c->images = malloc(sizeof(Image *) * c->hdr->nImages);
  if(c->images == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error10;
  }
  for(i = 0; i < c->hdr->nImages; i++) {
    c->images[i] = (Image *)&(c->imagesMem[i * sizeof(Image)]);
  }
  if(readImages(c) < 0) {
    fprintf(stderr, "Failed to read images.\n");
    goto error11;
  }
  
  // palettes
  c->palettesMem = malloc(sizeof(PaletteEntry) * c->hdr->nPalettes * c->hdr->nColors);
  if(c->palettesMem == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error11;
  }
  c->paletteArraysMem = malloc(sizeof(PaletteEntry *) * c->hdr->nPalettes * c->hdr->nColors);
  if(c->paletteArraysMem == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error12;
  }
  c->palettes = malloc(sizeof(PaletteEntry **) * c->hdr->nPalettes);
  if(c->palettes == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error13;
  }
  for(j = 0; j < c->hdr->nPalettes; j++) {
    c->palettes[j] = &(c->paletteArraysMem[j * c->hdr->nColors]);
    for(i = 0; i < c->hdr->nColors; i++) {
      c->palettes[j][i] = (PaletteEntry *)&(c->palettesMem[i * sizeof(PaletteEntry)]);
    }
  }
  if(readPalettes(c) < 0) {
    fprintf(stderr, "Failed to read palettes.\n");
    goto error14;
  }

  // bitmaps
  
  // determine memory required for bitmaps
  bitmapsMemSize = 0;
  for(i = 0; i < c->hdr->nImages; i++) {
    bitmapsMemSize += c->images[i]->width * c->images[i]->height;
  }
  c->bitmapsMem = malloc(bitmapsMemSize);
  if(c->bitmapsMem == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error14;
  }
  c->bitmaps = malloc(sizeof(char *) * c->hdr->nImages);
  if(c->bitmaps == NULL) {
    fprintf(stderr, "Failed to allocate memory.\n");
    goto error15;
  }
  bitmapsMemSize = 0;
  for(i = 0; i < c->hdr->nImages; i++) {
    c->bitmaps[i] = &(c->bitmapsMem[bitmapsMemSize]);
    bitmapsMemSize += c->images[i]->width * c->images[i]->height;
  }
  if(readBitmaps(c) < 0) {
    fprintf(stderr, "Failed to read bitmaps.\n");
    goto error16;
  }

  return(c);

error16:
  free(c->bitmaps);
error15:
  free(c->bitmapsMem);
error14:
  free(c->palettes);
error13:
  free(c->paletteArraysMem);
error12:
  free(c->palettesMem);
error11:
  free(c->images);
error10:
  free(c->imagesMem);
error9:
  free(c->lowShapes);
error8:
  free(c->lowShapesMem);
error7:
  if(c->hdr->nHighShapes > 0)
    free(c->views);
error6:
  if(c->hdr->nHighShapes > 0)
    free(c->animationsArrayMem);
error5:
  if(c->hdr->nHighShapes > 0)
    free(c->animationsMem);
error4:
  if(c->hdr->nHighShapes > 0)
    free(c->highShapes);
error3:
  if(c->hdr->nHighShapes > 0)
    free(c->highShapesMem);
error2:
  free(c->hdr);
error1:
  free(c);
error0:
  return(NULL);
}

void freeShapesContext(ShapesContext *c) {
  free(c->bitmaps);
  free(c->bitmapsMem);
  free(c->palettes);
  free(c->paletteArraysMem);
  free(c->palettesMem);
  free(c->images);
  free(c->imagesMem);
  free(c->lowShapes);
  free(c->lowShapesMem);
  if(c->hdr->nHighShapes > 0) {
    free(c->views);
    free(c->animationsArrayMem);
    free(c->animationsMem);
    free(c->highShapes);
    free(c->highShapesMem);
  }
  free(c->hdr);
  free(c);
}

void printShapesContext(ShapesContext *c) {
  int i, j, k;
  char name[34];
  unsigned short int tmpflags;
  
  printf("# Main header\n");
  printf(". Version: %hd\n", c->hdr->version);
  printf(". Type: %hd ", c->hdr->type);
  switch(c->hdr->type) {
    case SHAPE_CLASS_TEXTURE:
      printf("(Texture)\n");
      break;
    case SHAPE_CLASS_SPRITE:
      printf("(Sprite)\n");
      break;
    case SHAPE_CLASS_INTERFACE:
      printf("(Interface)\n");
      break;
    case SHAPE_CLASS_SCENERY:
      printf("(Scenery)\n");
      break;
    default:
      printf("(Unknown Type)\n");
      break;
  }
  printf(". Flags: %hd\n", c->hdr->flags);
  printf(". Colors per palette: %hd\n", c->hdr->nColors);
  printf(". Palettes: %hd\n", c->hdr->nPalettes);
  printf(". Palettes location: %d\n", c->hdr->palettesOffset);
  printf(". High level shapes: %hd\n", c->hdr->nHighShapes);
  printf(". High level shapes tables location: %d\n", c->hdr->highShapesTablesOffset);
  printf(". Low level shapes: %hd\n", c->hdr->nLowShapes);
  printf(". Low level shapes tables location: %d\n", c->hdr->lowShapesTablesOffset);
  printf(". Images tables: %hd\n", c->hdr->nImages);
  printf(". Images tables location: %d\n", c->hdr->imagesTablesOffsets);
  printf(". Scale factor: %hd\n", c->hdr->scaleFactor);
  printf(". Total size: %d\n", c->hdr->size);
  
  if(c->hdr->nHighShapes > 0) {
    printf("\n\n# High Level Shapes\n");
    for(i = 0; i < c->hdr->nHighShapes; i++) {
      printf("## High Level Shape %d\n", i);
      printf(". Type: %hd\n", c->highShapes[i]->type);
      printf(". Flags: %hd\n", c->highShapes[i]->flags);
      printf(". Name Length: %hhu\n", c->highShapes[i]->nameLen);
      // prevent overflows/corruption
      c->highShapes[i]->nameLen = c->highShapes[i]->nameLen > 33 ?
                                  33 : c->highShapes[i]->nameLen;
      memcpy(name, c->highShapes[i]->name, c->highShapes[i]->nameLen);
      name[c->highShapes[i]->nameLen] = '\0';
      printf(". Name: \"%s\"\n", name);
      printf(". Number of Views: %hd (%d)\n", c->highShapes[i]->nViews,
             GET_REAL_VIEW_COUNT(c->highShapes[i]));
      printf(". Animation frames: %hd\n", c->highShapes[i]->nFrames);
      printf(". Ticks per frame: %hd\n", c->highShapes[i]->animDelay);
      printf(". Transfer mode: %hd\n", c->highShapes[i]->transferMode);
      printf(". Transfer mode period: %hd\n", c->highShapes[i]->transferModePeriod);
      printf(". First frame sound: %hd\n", c->highShapes[i]->firstFrameSound);
      printf(". Key Frame sound: %hd\n", c->highShapes[i]->keyFrameSound);
      printf(". Last Frame Sound: %hd\n", c->highShapes[i]->lastFrameSound);
      printf(". Scale Factor: %hd\n", c->highShapes[i]->scaleFactor);
      printf("### Animations (Low Level Shape Indexes)\n");
      for(j = 0; j < GET_REAL_VIEW_COUNT(c->highShapes[i]); j++) {
        printf(". View %d:", j);
        for(k = 0; k < c->highShapes[i]->nFrames; k++) {
          printf(" %hd", c->views[i][j][k]);
        }
        printf("\n");
      }
      printf("\n");
    }
  }
  
  printf("\n# Low Level Shapes\n");
  for(i = 0; i < c->hdr->nLowShapes; i++) {
    printf("## Low Level Shape %d\n", i);
    printf(". Flags: %hX", c->lowShapes[i]->flags);
    tmpflags = c->lowShapes[i]->flags;
    if(tmpflags != 0) {
      printf(" (");
      if(tmpflags & LOW_LEVEL_SHAPE_XMIRROR) {
        printf("XMIRROR");
        tmpflags ^= LOW_LEVEL_SHAPE_XMIRROR;
        if(tmpflags != 0) {
          printf(" ");
        }
      }
      if(tmpflags & LOW_LEVEL_SHAPE_YMIRROR) {
        printf("YMIRROR");
        tmpflags ^= LOW_LEVEL_SHAPE_YMIRROR;
        if(tmpflags != 0) {
          printf(" ");
        }
      }
      if(tmpflags & LOW_LEVEL_SHAPE_KEYOBSCURE) {
        printf("KEYOBSCURE");
        tmpflags ^= LOW_LEVEL_SHAPE_KEYOBSCURE;
      }
      if(tmpflags != 0) {
        printf(" UNKNOWN");
      }
      printf(")\n");
    } else {
      printf("\n");
    }
    printf(". Minimum light intensity: %d\n", c->lowShapes[i]->minLightIntensity);
    printf(". Image index: %hd\n", c->lowShapes[i]->imageIndex);
    printf(". Origin X: %hd\n", c->lowShapes[i]->xOrigin);
    printf(". Origin Y: %hd\n", c->lowShapes[i]->yOrigin);
    printf(". Hot spot X: %hd\n", c->lowShapes[i]->xKey);
    printf(". Hot spot Y: %hd\n", c->lowShapes[i]->yKey);
    printf(". World left: %hd\n", c->lowShapes[i]->left);
    printf(". World right: %hd\n", c->lowShapes[i]->right);
    printf(". World top: %hd\n", c->lowShapes[i]->top);
    printf(". World bottom: %hd\n", c->lowShapes[i]->bottom);
    printf(". World X origin: %hd\n", c->lowShapes[i]->worldXOrigin);
    printf(". World Y origin: %hd\n\n", c->lowShapes[i]->worldYOrigin);
  }
  
  printf("\n# Images\n");
  for(i = 0; i < c->hdr->nImages; i++) {
    printf("## Image %d\n", i);
    printf(". Width: %hd\n", c->images[i]->width);
    printf(". Height: %hd\n", c->images[i]->height);
    printf(". Bytes Per Line: %hd\n", c->images[i]->bytesPerLine);
    printf(". Flags: %hd (", c->images[i]->flags);
    tmpflags = c->images[i]->flags;
    if((c->images[i]->flags & IMAGE_DIRECTION_MASK) == IMAGE_DIRECTION_LEFT_RIGHT) {
      printf("DIRECTION_LEFT_RIGHT");
      tmpflags ^= IMAGE_DIRECTION_LEFT_RIGHT;
    } else {
      printf("DIRECTION_TOP_BOTTOM");
    }
    if(tmpflags & IMAGE_TRANSPARENCY) {
      printf(" TRANSPARENCY");
      tmpflags ^= IMAGE_TRANSPARENCY;
    }
    if(tmpflags != 0) {
      printf(" UNKNOWN");
    }
    if(i == c->hdr->nImages - 1) {
      printf(")\n");
    } else {
      printf(")\n\n");
    }
  }
}
  
int getImagesCount(ShapesContext *c) {
  return(c->hdr->nImages);
}

Image *getImage(ShapesContext *c, short int i) {
  if(i < 0 || i > c->hdr->nImages) {
    return(NULL);
  }
  
  return(c->images[i]);
}

unsigned char *getImageData(ShapesContext *c, short int i) {
  if(i < 0 || i > c->hdr->nImages) {
    return(NULL);
  }
  
  return(c->bitmaps[i]);
}

int getPaletteCount(ShapesContext *c) {
  return(c->hdr->nPalettes);
}

PaletteEntry **getPalette(ShapesContext *c, short int i) {
  if(i < 0 || i > c->hdr->nPalettes) {
    return(NULL);
  }
  
  return(c->palettes[i]);
}

int getPaletteSize(ShapesContext *c) {
  return(c->hdr->nColors);
}
