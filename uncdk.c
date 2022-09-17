#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char MOOV[] = {'m', 'o', 'o', 'v'};

int seek_and_read(FILE *f, long pos, size_t len, char *buf) {
    size_t got;

    if(fseek(f, pos, SEEK_SET) < 0) {
        return(-1);
    }

    got = fread(buf, 1, len, f);

    return(got);
}

int seek_and_write(FILE *f, long pos, size_t len, char *buf) {
    size_t putted;

    if(fseek(f, pos, SEEK_SET) < 0) {
        return(-1);
    }

    putted = fwrite(buf, 1, len, f);

    return(putted);
}

void swap4(char *buf) {
    char t;

    t = buf[0];
    buf[0] = buf[3];
    buf[3] = t;
    t = buf[1];
    buf[1] = buf[2];
    buf[2] = t;
}

void xorBlock(char *buf, size_t len, unsigned char xorVal) {
    int i;

    for(i = 0; i < len; i++) {
        buf[i] ^= xorVal;
    }
}

int main(int argc, char **argv) {
    FILE *cdkFile;
    char moov[sizeof(MOOV)];
    unsigned int moovSize;
    char *atom;
    size_t got;
    unsigned char xorVal;

    if(argc < 2) {
        fprintf(stderr, "USAGE: %s <infile>\n", argv[0]);
        return(EXIT_FAILURE);
    }

    cdkFile = fopen(argv[1], "r+");
    if(cdkFile == NULL) {
        fprintf(stderr, "Failed to open %s for read/write.\n");
        return(EXIT_FAILURE);
    }

    if(seek_and_read(cdkFile, 4, sizeof(MOOV), moov) < sizeof(MOOV)) {
        fprintf(stderr, "Failed to read atom type.\n");
        goto cleanup_file;
    }

    if(memcmp(moov, MOOV, sizeof(MOOV)) != 0) {
        fprintf(stderr, "First atom wasn't a moov atom.\n");
        goto cleanup_file;
    }

    if(seek_and_read(cdkFile, 0, sizeof(moovSize), (char *)&moovSize) < sizeof(moovSize)) {
        fprintf(stderr, "Failed to read moov atom size.\n");
        goto cleanup_file;
    }

    swap4((char *)&moovSize);

    atom = malloc(moovSize);
    if(atom == NULL) {
        fprintf(stderr, "Couldn't allocate memory.\n");
        goto cleanup_file;
    }

    got = seek_and_read(cdkFile, 8, moovSize, atom);
    if(got < moovSize) {
        fprintf(stderr, "Failed to read atom, size %d, got %d.\n", moovSize, got);
        goto cleanup_mem;
    }

    /* Usually 0x7A but the first byte of a moov atom should be 0 so the
     * obfuscating XOR value will always be in the first byte, unless the moov
     * atom is exceptionally huge which isn't likely in this case. */
    xorVal = atom[0];
    xorBlock(atom, moovSize, xorVal);

    got = seek_and_write(cdkFile, 8, moovSize, atom);
    if(got < moovSize) {
        fprintf(stderr, "Failed to write atom, size %d, got %d.\n", moovSize, got);
        goto cleanup_mem;
    }

    fclose(cdkFile);

    return(EXIT_SUCCESS);

cleanup_mem:
    free(atom);
cleanup_file:
    fclose(cdkFile);

    return(EXIT_FAILURE);
}
