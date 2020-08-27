/*
 * Copyright 2016 paulguy <paulguy119@gmail.com>
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
 
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

#define LEADIN_BYTE (0x00)
const char const FRONT_PORCH_BYTES[] = {0xE1, 0xC3, 0xA5};
#define ACTIVE_BYTE (0x5A)
const char const BACK_PORCH_BYTES[] = {0xD2, 0xB4, 0x96};
#define LEADOUT_BYTE (0x00)
#define FRONT_PORCH_SIZE (2680 / sizeof(int))
#define ACTIVE_SIZE (6400 / sizeof(int))
#define BACK_PORCH_SIZE (2680 / sizeof(int))

#define FRAME_SIZE (ACTIVE_SIZE * 4)
#define FRONT_PORCH_AUDIO_SIZE (FRONT_PORCH_SIZE)
#define ACTIVE_AUDIO_SIZE (ACTIVE_SIZE)
#define BACK_PORCH_AUDIO_SIZE (BACK_PORCH_SIZE)

#define BUFFERSIZE (32768)

const char const *VIDEOSUFFIX = "_video.raw";
const char const *AUDIOSUFFIX = "_audio.raw";

typedef struct {
  int size;
  int filled;
  int cursor;
  int *buffer;
  FILE *f;
  int eof;
} read_buffer;

typedef struct {
  char frame[FRAME_SIZE];
  char audio[ACTIVE_AUDIO_SIZE]; // ACTIVE_AUDIO_SIZE is the largest of the 3.
  int bytesread;
} framedata;

typedef enum {
  FRAME_STATE_OK,
  FRAME_STATE_EOF,
  FRAME_STATE_UNEXPECTED_VALUE,
  FRAME_STATE_END_REACHED,
  FRAME_STATE_SHORT,
  FRAME_STATE_ERROR
} FrameState;

read_buffer *read_buffer_open(char *f, int size);
void read_buffer_close(read_buffer *b);
int read_buffer_next(read_buffer *b);
int read_buffer_eof(read_buffer *b);
int read_buffer_step_back(read_buffer *b);

FrameState eat_leadin(read_buffer *b);
FrameState eat_front_porch(read_buffer *b, framedata *frame);
FrameState get_frame(read_buffer *b, framedata *frame);
FrameState eat_back_porch(read_buffer *b, framedata *frame);
FrameState resync(read_buffer *b);

int main(int argc, char **argv) {
  read_buffer *b;
  FILE *audioout, *videoout;
  FrameState s;
  framedata front, active, back;
  char *fileext;
  int error;
  int framecount = 0, segcount = 0;
  
  if(argc < 2) {
    fprintf(stderr, "USAGE: %s <filename>\n", argv[0]);
    exit(EXIT_FAILURE);
  }

  fprintf(stderr, "Input file: %s\n", argv[1]);
  
  fileext = strrchr(argv[1], '.');
  int fileNameLen;
  if(fileext == NULL || fileext == argv[1] || fileext[1] == '\0') {
    fileNameLen = strlen(argv[1]) + 1;
  } else {
    fileNameLen = fileext - argv[1] + 1;
  }
  char fileName[fileNameLen];
  if(fileext == NULL || fileext == argv[1] || fileext[1] == '\0') {
    strncpy(fileName, argv[1], fileNameLen);
  } else {
    memcpy(fileName, argv[1], fileNameLen - 1);
    fileName[fileNameLen - 1] = '\0';
  }
  int audioFileNameLen = fileNameLen + 3 + strlen(AUDIOSUFFIX) + 1;
  char audioFileName[audioFileNameLen];
  int videoFileNameLen = fileNameLen + 3 + strlen(VIDEOSUFFIX) + 1;
  char videoFileName[videoFileNameLen];

  snprintf(audioFileName, audioFileNameLen, "%s_NN%s", fileName, AUDIOSUFFIX);
  snprintf(videoFileName, videoFileNameLen, "%s_NN%s", fileName, VIDEOSUFFIX);  
  fprintf(stderr, "Output video file names: %s\n", videoFileName);
  fprintf(stderr, "Output audio file names: %s\n", audioFileName);
  
  b = read_buffer_open(argv[1], BUFFERSIZE);
  if(b == NULL) {
    fprintf(stderr, "Failed to open %s.\n", argv[1]);
    goto error0;
  }
  
  while(!read_buffer_eof(b)) {
    fprintf(stderr, "Finding segment...\n");
    s = eat_leadin(b);
    if(s == FRAME_STATE_UNEXPECTED_VALUE) {
      fprintf(stderr, "Unexpected word type value.\n");
      goto error1;
    } else if(s == FRAME_STATE_END_REACHED) {
      break;
    }

    snprintf(audioFileName, audioFileNameLen, "%s_%02d%s", fileName, segcount, AUDIOSUFFIX);
    snprintf(videoFileName, videoFileNameLen, "%s_%02d%s", fileName, segcount, VIDEOSUFFIX);  
    fprintf(stderr, "Track %d ", segcount);

    audioout = fopen(audioFileName, "wb");
    if(audioout == NULL) {
      fprintf(stderr, "Couldn't open %s for write.\n", audioFileName);
      goto error1;
    }
    videoout = fopen(videoFileName, "wb");
    if(videoout == NULL) {
      fprintf(stderr, "Couldn't open %s for write.\n", videoFileName);
      goto error2;
    }
    
    framecount = 0;
    for(;;) {
      fprintf(stderr, ".");
      s = eat_front_porch(b, &front);
      if(s == FRAME_STATE_UNEXPECTED_VALUE) {
        fprintf(stderr, "Warning: Unexpected word type value, resyncing...\n");
        if(resync(b) == FRAME_STATE_OK) {
          continue;
        } else {
          break;
        }
      } else if(s == FRAME_STATE_ERROR) {
        fprintf(stderr, "Error reading front porch.\n");
        goto error3;
      } else if(s == FRAME_STATE_END_REACHED) {
        fprintf(stderr, "Unexpected end reached in front porch.\n");
        goto error3;
      }

      s = get_frame(b, &active);
      if(s == FRAME_STATE_UNEXPECTED_VALUE) {
        fprintf(stderr, "Warning: Unexpected word type value, resyncing...\n");
        if(resync(b) == FRAME_STATE_OK) {
          continue;
        } else {
          break;
        }
      } else if(s == FRAME_STATE_ERROR) {
        fprintf(stderr, "Error reading frame.\n");
        goto error3;
      } else if(s == FRAME_STATE_END_REACHED) {
        fprintf(stderr, "Unexpected end reached in front porch.\n");
        goto error3;
      }

      s = eat_back_porch(b, &back);
      if(s == FRAME_STATE_UNEXPECTED_VALUE) {
        fprintf(stderr, "Warning: Unexpected word type value, resyncing...\n");
        if(resync(b) == FRAME_STATE_OK) {
          continue;
        } else {
          break;
        }
      } else if(s == FRAME_STATE_ERROR) {
        fprintf(stderr, "Error reading back porch.\n");
        goto error3;
      } else if(s == FRAME_STATE_END_REACHED) {
        break;
      }

      if(fwrite(front.audio, 1, front.bytesread, audioout) < front.bytesread) {
        fprintf(stderr, "Error writing audio.\n");
        goto error3;
      }
      if(fwrite(active.audio, 1, active.bytesread, audioout) < active.bytesread) {
        fprintf(stderr, "Error writing audio.\n");
        goto error3;
      }
      // always write out the entire frame, even if it's short.
      if(fwrite(active.frame, 1, FRAME_SIZE, videoout) < FRAME_SIZE) {
        fprintf(stderr, "Error writing audio.\n");
        goto error3;
      }
      if(fwrite(back.audio, 1, back.bytesread, audioout) < back.bytesread) {
        fprintf(stderr, "Error writing audio.\n");
        goto error3;
      }

      framecount++;
    }
    fprintf(stderr, "\n");
    fclose(videoout);
    fclose(audioout);
    
    segcount++;
  }
  fprintf(stderr, "Done.\n");
  
  read_buffer_close(b);
  
  exit(EXIT_SUCCESS);

error3:
  fclose(videoout);
error2:
  fclose(audioout);
error1:
  read_buffer_close(b);
error0:
  exit(EXIT_FAILURE);
}

read_buffer *read_buffer_open(char *f, int size) {
  read_buffer *b;
  
  b = malloc(sizeof(read_buffer));
  if(b == NULL) {
    fprintf(stderr, "read_buffer_open: Couldn't allocate memory.\n");
    return(NULL);
  }
  
  b->buffer = malloc(sizeof(int) * size);
  if(b->buffer == NULL) {
    fprintf(stderr, "read_buffer_open: Couldn't allocate memory.\n");
    goto error0;
  }
  
  b->f = fopen(f, "rb");
  if(b->f < 0) {
    fprintf(stderr, "read_buffer_open: Couldn't open file %s for read.\n", f);
    goto error1;
  }
  b->size = size;
  b->filled = 0;
  b->cursor = 0;
  b->eof = 0;
  
  return(b);

error1:
  free(b->buffer);
error0:
  free(b);
  
  return(NULL);
}

void read_buffer_close(read_buffer *b) {
  fclose(b->f);
  free(b->buffer);
  free(b);
}

int read_buffer_next(read_buffer *b) {
  int bytesread;
  
  if(b->eof != 0) {
    return(0);
  }
  
  if(b->cursor == b->filled) {
    if(b->filled > 0 && b->filled < b->size) {
      b->eof = 1;
      return(0);
    }
    bytesread = fread(b->buffer, 1, b->size * sizeof(int), b->f);
    if(bytesread < 0) {
      b->eof = 1;
      if(ferror(b->f)) {
        fprintf(stderr, "read_buffer_next: Read error occurred.\n");
      }
      return(0);
    }
    
    b->filled = bytesread / sizeof(int);
    b->cursor = 0;
    b->eof = 0;
  }
  
  b->cursor++;
  return(b->buffer[b->cursor - 1]);
}

int read_buffer_eof(read_buffer *b) {
  return(b->eof);
}

int read_buffer_step_back(read_buffer *b) {
  int bytesread;
  
  if(b->cursor == 0) {  // worst case, we need to completely refill the buffer
    if(fseek(b->f, -sizeof(int), SEEK_CUR) < 0) {
      fprintf(stderr, "read_buffer_step_back: Couldn't seek: %s\n", strerror(errno));
      return(-1);
    }
    
    bytesread = fread(b->buffer, 1, b->size * sizeof(int), b->f);
    if(bytesread < 0) {
      b->eof = 1;
      if(ferror(b->f)) {
        fprintf(stderr, "read_buffer_next: Read error occurred.\n");
      }
      return(0);
    }
    
    b->filled = bytesread;
    
    return(0);
  }
  
  b->cursor--;
  
  return(0);
}

FrameState eat_leadin(read_buffer *b) {
  int ret;
  
  while (((ret = read_buffer_next(b)) >> 24 & 0xFF) == LEADIN_BYTE);
  if((char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[0] &&
     (char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[1] &&
     (char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[2]) {
    if(read_buffer_eof(b) != 0) {
      return(FRAME_STATE_END_REACHED);
    }
    fprintf(stderr, "eat_leadin: Unexpected word type following leadin %08X.\n",
            ret);
    return(FRAME_STATE_UNEXPECTED_VALUE);
  }
  
  if(read_buffer_step_back(b) < 0) {
    fprintf(stderr, "eat_leadin: Couldn't step back.\n");
    return(FRAME_STATE_ERROR);
  }
  
  return(FRAME_STATE_OK);
}

FrameState eat_front_porch(read_buffer *b, framedata *frame) {
  int ret;

  for (frame->bytesread = 0; frame->bytesread < FRONT_PORCH_SIZE; frame->bytesread++) {
    if(read_buffer_eof(b) != 0) {
      fprintf(stderr, "eat_front_porch: Unexpected end of file.\n");
      return(FRAME_STATE_ERROR);
    }
    ret = read_buffer_next(b);
    if((char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[0] &&
       (char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[1] &&
       (char)(ret >> 24 & 0xFF) != FRONT_PORCH_BYTES[2]) {
      if((char)(ret >> 24 & 0xFF) == LEADOUT_BYTE) {
        return(FRAME_STATE_END_REACHED);
      } else if((ret >> 24 & 0xFF) == ACTIVE_BYTE) {
        fprintf(stderr, "eat_front_porch: Warning: short front porch");
        if(read_buffer_step_back(b) < 0) {
          fprintf(stderr, "eat_leadin: Couldn't step back.\n");
          return(FRAME_STATE_ERROR);
        }
        return(FRAME_STATE_OK);
      }
      fprintf(stderr, "eat_front_porch: Unexpected word type in front porch %08X.\n",
              ret);
      fprintf(stderr, "%d %d %d %d %d\n", b->size, b->filled, b->cursor, fseek(b->f, 0, SEEK_CUR), frame->bytesread);
      return(FRAME_STATE_UNEXPECTED_VALUE);
    }
    
    frame->audio[frame->bytesread] = ret >> 16 & 0xFF;
  }
  
  return(FRAME_STATE_OK);
}

FrameState get_frame(read_buffer *b, framedata *frame) {
  int ret;
  char px[4];

  for (frame->bytesread = 0; frame->bytesread < ACTIVE_SIZE; frame->bytesread++) {
    ret = read_buffer_next(b);
    if((ret >> 24 & 0xFF) != ACTIVE_BYTE) {
      if(read_buffer_eof(b) != 0) {
        fprintf(stderr, "get_frame: Unexpected end of file in active region.\n");
        return(FRAME_STATE_END_REACHED);
      }
      if((char)(ret >> 24 & 0xFF) == BACK_PORCH_BYTES[0] ||
         (char)(ret >> 24 & 0xFF) == BACK_PORCH_BYTES[1] ||
         (char)(ret >> 24 & 0xFF) == BACK_PORCH_BYTES[2]) {
        fprintf(stderr, "get_frame: Warning: short frame, won't look right!");
        if(read_buffer_step_back(b) < 0) {
          fprintf(stderr, "eat_leadin: Couldn't step back.\n");
          return(FRAME_STATE_ERROR);
        }
        return(FRAME_STATE_SHORT);
      }
      fprintf(stderr, "get_frame: Unexpected word type in active region %08X.\n",
              ret);
      fprintf(stderr, "%d %d %d %d %d\n", b->size, b->filled, b->cursor, fseek(b->f, 0, SEEK_CUR), frame->bytesread);
      return(FRAME_STATE_UNEXPECTED_VALUE);
    }      
      
    frame->audio[frame->bytesread] = ret >> 16 & 0xFF;
    px[0] = (char)(ret >> 12 & 0xF);
    px[1] = (char)(ret >> 8 & 0xF);
    px[2] = (char)(ret >> 4 & 0xF);
    px[3] = (char)(ret >> 0 & 0xF);
    frame->frame[frame->bytesread * 4 + 0] = px[0] | (px[0] << 4);
    frame->frame[frame->bytesread * 4 + 1] = px[1] | (px[1] << 4);
    frame->frame[frame->bytesread * 4 + 2] = px[2] | (px[2] << 4);
    frame->frame[frame->bytesread * 4 + 3] = px[3] | (px[3] << 4);
  }
  
  return(FRAME_STATE_OK);
}

FrameState eat_back_porch(read_buffer *b, framedata *frame) {
  int ret, i;

  for (frame->bytesread = 0; frame->bytesread < BACK_PORCH_SIZE; frame->bytesread++) {
    ret = read_buffer_next(b);
    if((char)(ret >> 24 & 0xFF) != BACK_PORCH_BYTES[0] &&
       (char)(ret >> 24 & 0xFF) != BACK_PORCH_BYTES[1] &&
       (char)(ret >> 24 & 0xFF) != BACK_PORCH_BYTES[2]) {
      if(read_buffer_eof(b) != 0) {
        fprintf(stderr, "eat_back_porch: Unexpected end of file in back porch.\n");
        return(FRAME_STATE_ERROR);
      }
      if((char)(ret >> 24 & 0xFF) == LEADOUT_BYTE) {
        return(FRAME_STATE_END_REACHED);
      }
      fprintf(stderr, "eat_back_porch: Unexpected word type in back porch %08X.\n",
              ret);
      return(FRAME_STATE_UNEXPECTED_VALUE);
    }
    
    frame->audio[frame->bytesread] = ret >> 16 & 0xFF;
  }
  
  return(FRAME_STATE_OK);
}

FrameState resync(read_buffer *b) {
  int ret;
  
  for (;;) {
    ret = read_buffer_next(b);
    if(read_buffer_eof(b) != 0) {
      fprintf(stderr, "resync: Couldn't resync before end of file.");
      return(FRAME_STATE_END_REACHED);
    }
    if((char)(ret >> 24 & 0xFF) == FRONT_PORCH_BYTES[0] ||
       (char)(ret >> 24 & 0xFF) == FRONT_PORCH_BYTES[1] ||
       (char)(ret >> 24 & 0xFF) == FRONT_PORCH_BYTES[2]) {
      break;
    }
  }
  
  if(read_buffer_step_back(b) < 0) {
    fprintf(stderr, "resync: Couldn't step back.\n");
    return(FRAME_STATE_ERROR);
  }
  
  return(FRAME_STATE_OK);
}
