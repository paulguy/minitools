#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL.h>

#define SCREENX		(640)
#define SCREENY		(480)
#define DELAYTIME	(30)

#define SURFACEOFFSET(SURF, X, Y)	(((SURF)->pitch * (Y)) + ((SURF)->format->BytesPerPixel * (X)))
#define SURFACEPTR(SURF, X, Y)		((int *)&(((char *)((SURF)->pixels))[SURFACEOFFSET((SURF), (X), (Y))]))
#define MIN(A, B)					((A) > (B) ? (B) : (A))

typedef enum {
	COORD_MODE_TOPLEFT,
	COORD_MODE_CENTER
} coord_mode;

typedef struct {
/* destination size
 *  on decrease
 *   OK if greater than 1
 *  on increase
 *   OK if less than screen size
 *   OK if less than image size (always scale down)
 */
	int destw;
	int desth;
/* source start
 *  on decrease
 *   OK if greater than 0
 *  on increase
 *   OK if less than image size - source size (always scale down)
 */
	int srcx;
	int srcy;
/* source size
 *  on decrease
 *   OK if greater than 1
 *  on increase
 *   OK if less than image size - source start
 */
	int srcw;
	int srch;
	int scalex; // pixel multiplying
	int scaley;
	coord_mode mode;
} scaleparams;

int copyscaled(SDL_Surface *dest, SDL_Surface *src, scaleparams *sp);
void printdims(FILE *out, scaleparams *sp);

int main(int argc, char **argv) {
	SDL_Surface* screen;
	SDL_Surface* image;
	SDL_Surface* temp;
	SDL_Event event;
	scaleparams sp, spold;
	int screenx = SCREENX;
	int screeny = SCREENY;
	int step;
	int running;

	if(argc < 2) {
		fprintf(stderr, "USAGE: %s <filename> [xsize [ysize [destw [desth]]]]\n", argv[0]);
		goto error;
	}

	if(SDL_Init(SDL_INIT_VIDEO) != 0) {
		fprintf(stderr, "Failed to initialize SDL!\n");
		goto error;
	}

	if(argc > 2) {
		screenx = atoi(argv[2]);
		if(screenx < 1) {
			screenx = SCREENX;
		} else {
			if(argc > 3) {
				screeny = atoi(argv[3]);
				if(screeny < 1)
					screeny = screenx;
			} else {
				screeny = screenx;
			}
		}
	}

	if((screen = SDL_SetVideoMode(screenx, screeny, 32, SDL_SWSURFACE | SDL_RESIZABLE)) == NULL) {
		fprintf(stderr, "Failed to set video mode.\n");
		goto uninit;
	}

	if((image = SDL_LoadBMP(argv[1])) == NULL) {
		fprintf(stderr, "Failed to load image %s.\n", argv[1]);
		goto uninit;
	}

	if((temp = SDL_ConvertSurface(image, screen->format, SDL_SWSURFACE)) == NULL) {
		fprintf(stderr, "Failed to convert surface to 32 bit.\n");
		goto unload;
	}
	SDL_FreeSurface(image);
	image = temp;

	// set up initial state
	sp = (scaleparams){
		.destw = image->w > screen->w ? screen->w : image->w,
		.desth = image->h > screen->h ? screen->h : image->h,
		.srcx = 0,
		.srcy = 0,
		.srcw = image->w > screen->w ? screen->w : image->w,
		.srch = image->h > screen->h ? screen->h : image->h,
		.scalex = 1,
		.scaley = 1,
		.mode = COORD_MODE_CENTER
	};
	memset(&spold, 0, sizeof(scaleparams));

	if(argc > 4) {
		sp.destw = atoi(argv[4]);
		if(sp.destw < 1)
			sp.destw = image->w > screen->w ? screen->w : image->w;

		if(argc > 5) {
			sp.desth = atoi(argv[5]);
			if(sp.desth < 1)
				sp.desth = sp.destw;
		} else {
			sp.desth = sp.destw;
		}

		if(sp.destw > screen->w)
			sp.destw = screen->w;
		if(sp.desth > screen->h)
			sp.desth = screen->h;
	}

	running = 1;
	while(running) {
		if(memcmp(&sp, &spold, sizeof(scaleparams)) != 0) {
			if(copyscaled(screen, image, &sp) != 0) {
				fprintf(stderr, "Failed to copy image to screen.\n");
				running = 0;
			}
			memcpy(&spold, &sp, sizeof(scaleparams));
		}
		SDL_Flip(screen);

		while(SDL_PollEvent(&event)) {
			switch(event.type) {
				case SDL_QUIT:
					running = 0;
					break;
				case SDL_KEYDOWN:
					if(event.key.keysym.mod & (KMOD_LSHIFT | KMOD_RSHIFT)) {
						step = 10;
					} else {
						step = 1;
					}
					switch(event.key.keysym.sym) {
						case SDLK_q:
							running = 0;
							break;
						case SDLK_w:
							if(sp.srcy - step < 0)
								sp.srcy = 0;
							else
								sp.srcy -= step;
							break;
						case SDLK_s:
							if(sp.srcy + step > image->h - sp.srch)
								sp.srcy = image->h - sp.srch;
							else
								sp.srcy += step;
							break;
						case SDLK_a:
							if(sp.srcx - step < 0)
								sp.srcx = 0;
							else
								sp.srcx -= step;
							break;
						case SDLK_d:
							if(sp.srcx + step > image->w - sp.srcw)
								sp.srcx = image->w - sp.srcw;
							else
								sp.srcx += step;
							break;
						case SDLK_t:
							if(sp.desth - step < 1)
								sp.desth = 1;
							else
								sp.desth -= step;
							break;
						case SDLK_g:
							if((sp.desth + step) * sp.scaley < screen->h)
								sp.desth += step;
							break;
						case SDLK_f:
							if(sp.destw - step < 1)
								sp.destw = 1;
							else
								sp.destw -= step;
							break;
						case SDLK_h:
							if((sp.destw + step) * sp.scalex < screen->w)
								sp.destw += step;
							break;
						case SDLK_i:
							if(sp.srch - step < 1)
								sp.srch = 1;
							else
								sp.srch -= step;
							break;
						case SDLK_k:
							if(sp.srch + step > image->h - sp.srcy)
								sp.srch = image->h - sp.srcy;
							else
								sp.srch += step;
							break;
						case SDLK_j:
							if(sp.srcw - step < 1)
								sp.srcw = 1;
							else
								sp.srcw -= step;
							break;
						case SDLK_l:
							if(sp.srcw + step > image->w - sp.srcx)
								sp.srcw = image->w - sp.srcx;
							else
								sp.srcw += step;
							break;
						case SDLK_UP:
							if(sp.scaley > 1)
								sp.scaley--;
							break;
						case SDLK_DOWN:
							if((sp.scaley + 1) * sp.desth < screen->h)
								sp.scaley++;
							break;
						case SDLK_LEFT:
							if(sp.scalex > 1)
								sp.scalex--;
							break;
						case SDLK_RIGHT:
							if((sp.scalex + 1) * sp.destw < screen->w)
								sp.scalex++;
							break;
						case SDLK_m:
							switch(sp.mode) {
								case COORD_MODE_CENTER:
									sp.mode = COORD_MODE_TOPLEFT;
									break;
								case COORD_MODE_TOPLEFT:
									sp.mode = COORD_MODE_CENTER;
									break;
							}
							break;
						case SDLK_p:
							printdims(stdout, &sp);
							break;
						default:
							break;
					}
					break;
				case SDL_VIDEORESIZE:
					if((screen = SDL_SetVideoMode(event.resize.w, event.resize.h, 32, SDL_SWSURFACE | SDL_RESIZABLE)) == NULL) {
						fprintf(stderr, "Failed to set video mode.\n");
						running = 0;
					}

					if(sp.scalex * sp.destw > screen->w) {
						if(screen->w / sp.destw > 0) {
							sp.scalex = screen->w / sp.destw;
						} else {
							sp.scalex = 1;
							sp.destw = screen->w;
						}
					}

					if(sp.scaley * sp.desth > screen->h) {
						if(screen->h / sp.desth > 0) {
							sp.scaley = screen->h / sp.desth;
						} else {
							sp.scaley = 1;
							sp.desth = screen->h;
						}
					}
					break;
			}
		}

		SDL_Delay(DELAYTIME);
	}

	SDL_FreeSurface(image);
	SDL_Quit();

	printdims(stdout, &sp);
	exit(EXIT_SUCCESS);

unload:
	SDL_FreeSurface(image);
uninit:
	SDL_Quit();
error:
	exit(EXIT_FAILURE);
}

void printdims(FILE *out, scaleparams *sp) {
	fprintf(out, "Crop rectangle: @ %d, %d for %d, %d\n", sp->srcx, sp->srcy, sp->srcw, sp->srch);
	fprintf(out, "Scale to: %d, %d\n", sp->destw, sp->desth);
}

int copyscaled(SDL_Surface *dest, SDL_Surface *src, scaleparams *sp) {
	int x, y, x2, y2;
	int destoff, destoff2;
	double xstep, ystep;
	int color;
	double startx, starty;

	xstep = (double)(sp->srcw) / (double)(sp->destw);
	ystep = (double)(sp->srch) / (double)(sp->desth);
	switch(sp->mode) {
		case COORD_MODE_TOPLEFT:
			startx = 0.0;
			starty = 0.0;
			break;
		case COORD_MODE_CENTER:
			startx = xstep / 2.0;
			starty = ystep / 2.0;
			break;
	}

	SDL_FillRect(dest, NULL, SDL_MapRGB(dest->format, 0, 0, 0));
	if(SDL_LockSurface(dest) != 0)
		return(-1);
	if(SDL_LockSurface(src) != 0)
		return(-1);

	if(sp->scalex == 1 && sp->scaley == 1) { // 1x1
		for(y = 0; y < sp->desth; y++) {
			destoff = dest->pitch * y;

			for(x = 0; x < sp->destw; x++) {
				*(int *)&(((char *)(dest->pixels))[destoff]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));

				destoff += dest->format->BytesPerPixel;
			}
		}
	} else if(sp->scalex == 2 && sp->scaley == 1) { // 2x1
		for(y = 0; y < sp->desth; y++) {
			destoff = dest->pitch * y;

			for(x = 0; x < sp->destw; x++) {
				*(int *)&(((char *)(dest->pixels))[destoff]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				*(int *)&(((char *)(dest->pixels))[destoff + dest->format->BytesPerPixel]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));

				destoff += dest->format->BytesPerPixel * 2;
			}
		}
	} else if(sp->scalex == 1 && sp->scaley == 2) { // 1x2
		for(y = 0; y < sp->desth; y++) {
			destoff = dest->pitch * y * 2;

			for(x = 0; x < sp->destw; x++) {
				*(int *)&(((char *)(dest->pixels))[destoff]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				*(int *)&(((char *)(dest->pixels))[destoff + dest->pitch]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));

				destoff += dest->format->BytesPerPixel;
			}
		}
	} else if(sp->scalex == 1 && sp->scaley == 2) { // 2x2
		for(y = 0; y < sp->desth; y++) {
			destoff = dest->pitch * y * 2;

			for(x = 0; x < sp->destw; x++) {
				*(int *)&(((char *)(dest->pixels))[destoff]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				*(int *)&(((char *)(dest->pixels))[destoff + dest->pitch]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				*(int *)&(((char *)(dest->pixels))[destoff + dest->format->BytesPerPixel]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				*(int *)&(((char *)(dest->pixels))[destoff + dest->pitch + dest->format->BytesPerPixel]) = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));

				destoff += dest->format->BytesPerPixel * 2;
			}
		} // TODO: More unrolled scalers
	} else { // slow fallback
		for(y = 0; y < sp->desth; y++) {
			destoff = dest->pitch * y * sp->scaley;

			for(x = 0; x < sp->destw; x++) {
				color = *SURFACEPTR(src, sp->srcx + (int)(xstep * (double)x + startx), sp->srcy + (int)(ystep * (double)y + starty));
				for(y2 = 0; y2 < sp->scaley; y2++) {
					destoff2 = destoff + (dest->pitch * y2);
					for(x2 = 0; x2 < sp->scalex; x2++) {
						*(int *)&(((char *)(dest->pixels))[destoff2]) = color;
						destoff2 += dest->format->BytesPerPixel;
					}
				}

				destoff += dest->format->BytesPerPixel * sp->scalex;
			}
		}
	}

	SDL_UnlockSurface(src);
	SDL_UnlockSurface(dest);

	return(0);
}
