#!/usr/bin/env python

import struct
import sys
import array
import itertools
import pathlib
import os

from PIL import Image

HDR = struct.Struct("<BBB")

COLORS = (0x00000000, 0x00AA0000, 0x0000AA00, 0x00AAAA00,
          0x000000AA, 0x00AA00AA, 0x0000AAAA, 0x00AAAAAA,
          0x00555555, 0x00FF5555, 0x0055FF55, 0x00FFFF55,
          0x005555FF, 0x00FF55FF, 0x0055FFFF, 0x00FFFFFF)

class DN1:
    def __init__(self, path : pathlib.Path):
        with open(inpath, 'rb') as infile:
            infile.seek(0, os.SEEK_END)
            filesize = infile.tell()
            infile.seek(0, os.SEEK_SET)

            self.count, width_bytes, self.height = HDR.unpack(infile.read(HDR.size))
            if self.count == 0 or width_bytes == 0 or self.height == 0 or self.count * width_bytes * self.height > filesize:
                raise ValueError("File header indicates an invalid size, maybe you tried to load the wrong kind of file?")

            self.width = width_bytes * 8

            self.data = array.array('I', itertools.repeat(0, self.width * self.height * self.count))

            bytecols = array.array('B', itertools.repeat(0, 8))
            colors = array.array('I', itertools.repeat(0, 8))

            # oof this is going to be slow, but the image data is tiny...
            pos = 0
            for i in range(self.count):
                for j in range(self.height):
                    rowdata = infile.read(width_bytes * 5)
                    for k in range(width_bytes):
                        # low bit 0
                        bytecols[0] = (rowdata[k * 5 + 1] & 0x80) >> 7
                        bytecols[1] = (rowdata[k * 5 + 1] & 0x40) >> 6
                        bytecols[2] = (rowdata[k * 5 + 1] & 0x20) >> 5
                        bytecols[3] = (rowdata[k * 5 + 1] & 0x10) >> 4
                        bytecols[4] = (rowdata[k * 5 + 1] & 0x08) >> 3
                        bytecols[5] = (rowdata[k * 5 + 1] & 0x04) >> 2
                        bytecols[6] = (rowdata[k * 5 + 1] & 0x02) >> 1
                        bytecols[7] = (rowdata[k * 5 + 1] & 0x01)
                        # bit 1
                        bytecols[0] |= (rowdata[k * 5 + 2] & 0x80) >> 6
                        bytecols[1] |= (rowdata[k * 5 + 2] & 0x40) >> 5
                        bytecols[2] |= (rowdata[k * 5 + 2] & 0x20) >> 4
                        bytecols[3] |= (rowdata[k * 5 + 2] & 0x10) >> 3
                        bytecols[4] |= (rowdata[k * 5 + 2] & 0x08) >> 2
                        bytecols[5] |= (rowdata[k * 5 + 2] & 0x04) >> 1
                        bytecols[6] |= (rowdata[k * 5 + 2] & 0x02)
                        bytecols[7] |= (rowdata[k * 5 + 2] & 0x01) << 1
                        # bit 2
                        bytecols[0] |= (rowdata[k * 5 + 3] & 0x80) >> 5
                        bytecols[1] |= (rowdata[k * 5 + 3] & 0x40) >> 4
                        bytecols[2] |= (rowdata[k * 5 + 3] & 0x20) >> 3
                        bytecols[3] |= (rowdata[k * 5 + 3] & 0x10) >> 2
                        bytecols[4] |= (rowdata[k * 5 + 3] & 0x08) >> 1
                        bytecols[5] |= (rowdata[k * 5 + 3] & 0x04)
                        bytecols[6] |= (rowdata[k * 5 + 3] & 0x02) << 1
                        bytecols[7] |= (rowdata[k * 5 + 3] & 0x01) << 2
                        # bit 3
                        bytecols[0] |= (rowdata[k * 5 + 4] & 0x80) >> 4
                        bytecols[1] |= (rowdata[k * 5 + 4] & 0x40) >> 3
                        bytecols[2] |= (rowdata[k * 5 + 4] & 0x20) >> 2
                        bytecols[3] |= (rowdata[k * 5 + 4] & 0x10) >> 1
                        bytecols[4] |= (rowdata[k * 5 + 4] & 0x08)
                        bytecols[5] |= (rowdata[k * 5 + 4] & 0x04) << 1
                        bytecols[6] |= (rowdata[k * 5 + 4] & 0x02) << 2
                        bytecols[7] |= (rowdata[k * 5 + 4] & 0x01) << 3
                        # convert to RGB and add alpha
                        colors[0] = COLORS[bytecols[0]] | (((rowdata[k * 5] & 0x80) >> 7) * 0xFF000000)
                        colors[1] = COLORS[bytecols[1]] | (((rowdata[k * 5] & 0x40) >> 6) * 0xFF000000)
                        colors[2] = COLORS[bytecols[2]] | (((rowdata[k * 5] & 0x20) >> 5) * 0xFF000000)
                        colors[3] = COLORS[bytecols[3]] | (((rowdata[k * 5] & 0x10) >> 4) * 0xFF000000)
                        colors[4] = COLORS[bytecols[4]] | (((rowdata[k * 5] & 0x08) >> 3) * 0xFF000000)
                        colors[5] = COLORS[bytecols[5]] | (((rowdata[k * 5] & 0x04) >> 2) * 0xFF000000)
                        colors[6] = COLORS[bytecols[6]] | (((rowdata[k * 5] & 0x02) >> 1) * 0xFF000000)
                        colors[7] = COLORS[bytecols[7]] | (((rowdata[k * 5] & 0x01)) * 0xFF000000)
                        self.data[pos:pos+8] = colors[:]
                        pos += 8 # 1 byte per 8 pixels

    def save(self, path : pathlib.Path):
        image = Image.frombytes('RGBA', (self.width, self.height * self.count), self.data.tobytes())
        image.save(path, 'PNG')

if __name__ == '__main__':
    inpath = pathlib.Path(sys.argv[1])
    outpath = pathlib.Path(f"{inpath.stem}.png")

    image = DN1(inpath)
    image.save(outpath)
