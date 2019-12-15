#!/usr/bin/env python3.6

import struct
import re
import glob
from pathlib import Path


class BadPaletteException(Exception):
    pass


class BadArtFileException(Exception):
    pass


linearTable = (
      0,   4,   8,  12,  16,  20,  24,  28,
     32,  36,  40,  44,  48,  52,  56,  60,
     65,  69,  73,  77,  81,  85,  89,  93,
     97, 101, 105, 109, 113, 117, 121, 125,
    130, 134, 138, 142, 146, 150, 154, 158,
    162, 166, 170, 174, 178, 182, 186, 190,
    195, 199, 203, 207, 211, 215, 219, 223,
    227, 231, 235, 239, 243, 247, 251, 255
)


def getPalette(filename):
    palette = []

    with open(filename, 'rb') as palFile:
        for r, g, b in struct.iter_unpack('<BBB', palFile.read(768)):
            if r > 63 or g > 63 or b > 63:
                raise BadPaletteException("Color value out of range 0 - 63.")
            palette.append((linearTable[b], linearTable[g], linearTable[r]))

    if len(palette) != 256:
        raise BadPaletteException("Couldn't read enough colors.")
    return palette


def getNames(filename):
    names = {}
    defineRE = re.compile("^#define\s+(?P<name>[^\s]+)\s+\(?(?P<num>[0-9]+)", re.IGNORECASE)

    with open(filename, 'r') as namesh:
        for line in namesh:
            result = defineRE.match(line)
            if result:
                names[int(result.group('num'))] = result.group('name')

    return names


def getArtFileRange(filename):
    start = 0
    end = 0

    with open(filename, 'rb') as artFile:
        magic, num, start, end = struct.unpack("<IIII", artFile.read(16))
        if magic != 1:
            raise BadArtFileException("Bad magic.")
        if end < start:
            raise BadArtFileException("End after start.")

    return start, end


def getFiles(path):
    files = []

    for name in glob.iglob(str(Path(path) / "*.ART")):
        try:
            start, end = getArtFileRange(name)
        except BadArtFileException as e:
            print("Bad ART file {:s}: {:s}.".format(name, str(e)))
            continue
        for file in files:
            if start >= file[1] and start <= file[2]:
                print("WARNING: {:s} and {:s} overlap.".format(name, file[0]))
        files.append((name, start, end))

    files = sorted(files, key=lambda val: val[1])

    return files


def writeBMP(name, width, height, palette, data):
    pad = b"\0\0\0"
    stride = int(width / 4) * 4
    if stride < width:
        stride = stride + 4
    widthDiff = stride - width
    with open("{:s}.bmp".format(name), 'wb') as bmpFile:
        bmpFile.write(struct.pack("<ccIHHI IIIHHIIIIII", b'B', b'M',
            54 + 1024 + (stride * height), 0, 0, 54 + 1024,
            40, width, height, 1, 8, 0, 0, 1000, 1000, 256, 256))
        for color in palette:
            bmpFile.write(struct.pack("<BBBx", color[0], color[1], color[2]))
        for i in range(height):
            bmpFile.write(data[i*width:(i+1)*width])
            bmpFile.write(pad[0:widthDiff])


def rearrangeData(data, width, height):
    newData = []

    for y in range(height - 1, -1, -1):
        for x in range(0, height * width, height):
            newData.append(data[y+x])

    return bytes(newData)


def extractFile(filename, start, end, palette, names):
    dims = []

    with open(filename, 'rb') as artFile:
        artFile.seek(16)

        count = end - start + 1
        widths = [x[0] for x in struct.iter_unpack('<H', artFile.read(count * 2))]
        if len(widths) < count:
            raise BadArtFileException("Couldn't read enough widths.")
        heights = [x[0] for x in struct.iter_unpack('<H', artFile.read(count * 2))]
        if len(heights) < count:
            raise BadArtFileException("Couldn't read enough heights.")
        dims = zip(widths, heights)

        #don't need the rest of this
        artFile.seek(count * 4, 1)

        for dim in enumerate(dims):
            width, height = dim[1]
            if width == 0 or height == 0:
                continue
            data = artFile.read(width * height)
            if len(data) < width * height:
                raise BadArtFileException("Not enough data.")
            data = rearrangeData(data, width, height)

            name = ""
            try:
                name = "{:04d}_{:s}".format(start + dim[0],
                                            names[start + dim[0]])
            except KeyError:
                name = "{:04d}".format(start + dim[0])

            print(" -> Writing out {:s}...".format(name))
            writeBMP(name, width, height, palette, data)


def extractFiles(artFiles, palette, names):
    for filename, start, end in artFiles:
        print("Extracting from {:s}...".format(filename))
        extractFile(filename, start, end, palette, names)


if __name__ == '__main__':
    palette = []
    names = {}
    artFiles = []

    palette = getPalette("PALETTE.DAT")
    names = getNames("NAMES.H")
    artFiles = getFiles(".")

    extractFiles(artFiles, palette, names)
