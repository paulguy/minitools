#!/usr/bin/env python3.6

import struct


class BadPaletteException(Exception):
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
            palette.append((linearTable[r], linearTable[g], linearTable[b]))

    if len(palette) != 256:
        raise BadPaletteException("Couldn't read enough colors.")
    return palette


def getLUTs(filename):
    LUTs = {}

    with open(filename, 'rb') as LUTFile:
        count = struct.unpack('<B', LUTFile.read(1))[0]
        for i in range(count):
            index = struct.unpack('<B', LUTFile.read(1))[0]
            LUT = [x[0] for x in struct.iter_unpack('<B', LUTFile.read(256))]
            LUTs[index] = LUT

    return LUTs


def getAltPalettes(filename):
    altPalettes = []

    with open(filename, 'rb') as LUTFile:
        count = struct.unpack('<B', LUTFile.read(1))[0]
        LUTFile.seek(count * 257, 1)
        while True:
            palData = LUTFile.read(768)
            if len(palData) < 768:
                break
            palette = []
            for r, g, b in struct.iter_unpack('<BBB', palData):
                if r > 63 or g > 63 or b > 63:
                    raise BadPaletteException("Color value out of range 0 - 63.")
                palette.append((linearTable[r], linearTable[g], linearTable[b]))
            altPalettes.append(palette)

    return altPalettes


def applyPalette(palette, LUT):
    LUTPalette = []

    for color in LUT:
        LUTPalette.append(palette[color])

    return LUTPalette


def writePalette(filename, palette):
    with open(filename, 'w') as palFile:
        palFile.write("{:d}\n".format(len(palette)))
        for color in palette:
            palFile.write("{:d},{:d},{:d}\n".format(color[0], color[1], color[2]))


if __name__ == '__main__':
    palette = getPalette("PALETTE.DAT")
    LUTs = getLUTs("LOOKUP.DAT")
    altPalettes = getAltPalettes("LOOKUP.DAT")
    LUTPalettes = {}

    for key in LUTs.keys():
        LUTPalettes[key] = applyPalette(palette, LUTs[key])

    print("LUTs: {:d}, Alternate Palettes: {:d}".format(len(LUTPalettes), len(altPalettes)))

    writePalette("pal_default.txt", palette)

    for pal in enumerate(altPalettes):
        writePalette("pal_alternate{:d}.txt".format(pal[0]), pal[1])

    for key in LUTPalettes.keys():
        writePalette("pal_lookup{:d}.txt".format(key), LUTPalettes[key])
