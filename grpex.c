#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define BLOCKSIZE (32768)

typedef struct {
    char name[13];
    unsigned int size;
} Entry;

const char magic[] = "KenSilverman";

int main(int argc, char **argv) {
    char buffer[BLOCKSIZE];
    char entry[16];
    int nEntries;
    Entry *entries;
    FILE *in, *out;
    int i;
    unsigned int j;
    unsigned int dataRead;
    unsigned int remainder;

    if(argc < 2) {
        fprintf(stderr, "%s <GRP file>\n", argv[0]);
        goto error0;
    }

    in = fopen(argv[1], "rb");
    if(in == NULL) {
        fprintf(stderr, "Failed to open %s for reading.\n", argv[1]);
        goto error0;
    }

    if(fread(entry, 1, sizeof(entry), in) < sizeof(entry)) {
        fprintf(stderr, "Failed to read entry.\n");
        goto error1;
    }

    if(memcmp(entry, magic, 12) != 0) {
        fprintf(stderr, "Bad magic.\n");
        goto error1;
    }

    nEntries = ((int *)entry)[3];
    entries = malloc(sizeof(Entry) * nEntries);
    if(entries == NULL) {
        fprintf(stderr, "Failed to allocate memory");
        goto error1;
    }

    for(i = 0; i < nEntries; i++) {
        if(fread(entry, 1, sizeof(entry), in) < sizeof(entry)) {
            fprintf(stderr, "Failed to read entry.\n");
            goto error2;
        }

        memcpy(entries[i].name, entry, 12);
        entries[i].name[12] = '\0';
        entries[i].size = ((unsigned int *)entry)[3];
    }

    for(i = 0; i < nEntries; i++) {
        fprintf(stderr, "%s (%u)... ", entries[i].name, entries[i].size);

        out = fopen(entries[i].name, "wb");
        if(out == NULL) {
            fprintf(stderr, "Failed to open %s for writing.\n", entries[i].name);
            goto error2;
        }

        for(j = 0; BLOCKSIZE < entries[i].size - j; j += BLOCKSIZE) {
            dataRead = fread(buffer, 1, BLOCKSIZE, in);
            if(dataRead < BLOCKSIZE) {
                fprintf(stderr, "Failed to read block.\n");
                goto error3;
            }

            if(fwrite(buffer, 1, dataRead, out) < dataRead) {
                fprintf(stderr, "Failed to write block.\n");
                goto error3;
            }
        }
        remainder = entries[i].size % BLOCKSIZE;
        if(remainder > 0) {
            dataRead = fread(buffer, 1, remainder, in);
            if(dataRead < remainder) {
                fprintf(stderr, "Failed to read block.\n");
                goto error3;
            }

            if(fwrite(buffer, 1, dataRead, out) < dataRead) {
                fprintf(stderr, "Failed to write block.\n");
                goto error3;
            }
        }            

        fclose(out);
        fprintf(stderr, "\n");
    }

    free(entries);
    fclose(in);
    exit(EXIT_SUCCESS);

error3:
    fclose(out);
error2:
    free(entries);
error1:
    fclose(in);
error0:
    exit(EXIT_FAILURE);
}
