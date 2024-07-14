#!/usr/bin/env python

import struct
import sys
import array
import itertools
import pathlib
import os
import json

from PIL import Image

HDR = struct.Struct("<BBB")

COLORS = (0x00000000, 0x00AA0000, 0x0000AA00, 0x00AAAA00,
          0x000000AA, 0x00AA00AA, 0x000055AA, 0x00AAAAAA,
          0x00555555, 0x00FF5555, 0x0055FF55, 0x00FFFF55,
          0x005555FF, 0x00FF55FF, 0x0055FFFF, 0x00FFFFFF)

# build palette for Image.putpalette()
PALETTE = [0, 0, 0, 0]
for c in COLORS:
    PALETTE.append(c & 0x000000FF)
    PALETTE.append((c & 0x0000FF00) >> 8)
    PALETTE.append((c & 0x00FF0000) >> 16)
    PALETTE.append(0xFF)

# not sure if this is correct?
PAD_SIZE = 64

class DN1:
    def load_fullscreen_dn1(self, infile):
        self.fullscreen = True
        self.width = 320
        self.height = 200
        self.count = 1
        self.data = array.array('B', itertools.repeat(0, self.width*self.height))

        infile.seek(0, os.SEEK_SET)

        # low bit 0
        plane = infile.read(len(self.data)//8)
        pos = 0
        for byte in plane:
            self.data[pos] = (byte & 0x80) >> 7
            self.data[pos+1] = (byte & 0x40) >> 6
            self.data[pos+2] = (byte & 0x20) >> 5
            self.data[pos+3] = (byte & 0x10) >> 4
            self.data[pos+4] = (byte & 0x08) >> 3
            self.data[pos+5] = (byte & 0x04) >> 2
            self.data[pos+6] = (byte & 0x02) >> 1
            self.data[pos+7] = (byte & 0x01)
            pos += 8
        # bit 1
        plane = infile.read(len(self.data)//8)
        pos = 0
        for byte in plane:
            self.data[pos] |= (byte & 0x80) >> 6
            self.data[pos+1] |= (byte & 0x40) >> 5
            self.data[pos+2] |= (byte & 0x20) >> 4
            self.data[pos+3] |= (byte & 0x10) >> 3
            self.data[pos+4] |= (byte & 0x08) >> 2
            self.data[pos+5] |= (byte & 0x04) >> 1
            self.data[pos+6] |= (byte & 0x02)
            self.data[pos+7] |= (byte & 0x01) << 1
            pos += 8
        # bit 2
        plane = infile.read(len(self.data)//8)
        pos = 0
        for byte in plane:
            self.data[pos] |= (byte & 0x80) >> 5
            self.data[pos+1] |= (byte & 0x40) >> 4
            self.data[pos+2] |= (byte & 0x20) >> 3
            self.data[pos+3] |= (byte & 0x10) >> 2
            self.data[pos+4] |= (byte & 0x08) >> 1
            self.data[pos+5] |= (byte & 0x04)
            self.data[pos+6] |= (byte & 0x02) << 1
            self.data[pos+7] |= (byte & 0x01) << 2
            pos += 8
        # bit 3
        plane = infile.read(len(self.data)//8)
        pos = 0
        for byte in plane:
            self.data[pos] |= (byte & 0x80) >> 4
            self.data[pos+1] |= (byte & 0x40) >> 3
            self.data[pos+2] |= (byte & 0x20) >> 2
            self.data[pos+3] |= (byte & 0x10) >> 1
            self.data[pos+4] |= (byte & 0x08)
            self.data[pos+5] |= (byte & 0x04) << 1
            self.data[pos+6] |= (byte & 0x02) << 2
            self.data[pos+7] |= (byte & 0x01) << 3
            pos += 8

    def load_background_dn1(self, infile):
        self.background = True
        self.width = 208
        self.height = 160
        self.count = 1
        self.data = array.array('B', itertools.repeat(0, self.width*self.height))

        width_tiles = self.width // 16 # tile width

        # no need to seek?

        # similar to below, but ignore alpha
        colors = array.array('B', itertools.repeat(0, 16))
        pos = 0
        for i in range(self.height // 16):
            # read for width tiles, for whole tile height and each tile row is 10 bytes
            rowdata = infile.read(width_tiles * 16 * 10)
            for j in range(16): # tile height
                for k in range(width_tiles):
                    offset = (k * 16 * 10) + (j * 10)
                    # tile left byte
                    # first byte ignored
                    # low bit 0
                    colors[0] = (rowdata[offset + 1] & 0x80) >> 7
                    colors[1] = (rowdata[offset + 1] & 0x40) >> 6
                    colors[2] = (rowdata[offset + 1] & 0x20) >> 5
                    colors[3] = (rowdata[offset + 1] & 0x10) >> 4
                    colors[4] = (rowdata[offset + 1] & 0x08) >> 3
                    colors[5] = (rowdata[offset + 1] & 0x04) >> 2
                    colors[6] = (rowdata[offset + 1] & 0x02) >> 1
                    colors[7] = (rowdata[offset + 1] & 0x01)
                    # bit 1
                    colors[0] |= (rowdata[offset + 2] & 0x80) >> 6
                    colors[1] |= (rowdata[offset + 2] & 0x40) >> 5
                    colors[2] |= (rowdata[offset + 2] & 0x20) >> 4
                    colors[3] |= (rowdata[offset + 2] & 0x10) >> 3
                    colors[4] |= (rowdata[offset + 2] & 0x08) >> 2
                    colors[5] |= (rowdata[offset + 2] & 0x04) >> 1
                    colors[6] |= (rowdata[offset + 2] & 0x02)
                    colors[7] |= (rowdata[offset + 2] & 0x01) << 1
                    # bit 2
                    colors[0] |= (rowdata[offset + 3] & 0x80) >> 5
                    colors[1] |= (rowdata[offset + 3] & 0x40) >> 4
                    colors[2] |= (rowdata[offset + 3] & 0x20) >> 3
                    colors[3] |= (rowdata[offset + 3] & 0x10) >> 2
                    colors[4] |= (rowdata[offset + 3] & 0x08) >> 1
                    colors[5] |= (rowdata[offset + 3] & 0x04)
                    colors[6] |= (rowdata[offset + 3] & 0x02) << 1
                    colors[7] |= (rowdata[offset + 3] & 0x01) << 2
                    # bit 3
                    colors[0] |= (rowdata[offset + 4] & 0x80) >> 4
                    colors[1] |= (rowdata[offset + 4] & 0x40) >> 3
                    colors[2] |= (rowdata[offset + 4] & 0x20) >> 2
                    colors[3] |= (rowdata[offset + 4] & 0x10) >> 1
                    colors[4] |= (rowdata[offset + 4] & 0x08)
                    colors[5] |= (rowdata[offset + 4] & 0x04) << 1
                    colors[6] |= (rowdata[offset + 4] & 0x02) << 2
                    colors[7] |= (rowdata[offset + 4] & 0x01) << 3
                    # tile right byte
                    # first byte ignored
                    # low bit 0
                    colors[8] = (rowdata[offset + 6] & 0x80) >> 7
                    colors[9] = (rowdata[offset + 6] & 0x40) >> 6
                    colors[10] = (rowdata[offset + 6] & 0x20) >> 5
                    colors[11] = (rowdata[offset + 6] & 0x10) >> 4
                    colors[12] = (rowdata[offset + 6] & 0x08) >> 3
                    colors[13] = (rowdata[offset + 6] & 0x04) >> 2
                    colors[14] = (rowdata[offset + 6] & 0x02) >> 1
                    colors[15] = (rowdata[offset + 6] & 0x01)
                    # bit 1
                    colors[8] |= (rowdata[offset + 7] & 0x80) >> 6
                    colors[9] |= (rowdata[offset + 7] & 0x40) >> 5
                    colors[10] |= (rowdata[offset + 7] & 0x20) >> 4
                    colors[11] |= (rowdata[offset + 7] & 0x10) >> 3
                    colors[12] |= (rowdata[offset + 7] & 0x08) >> 2
                    colors[13] |= (rowdata[offset + 7] & 0x04) >> 1
                    colors[14] |= (rowdata[offset + 7] & 0x02)
                    colors[15] |= (rowdata[offset + 7] & 0x01) << 1
                    # bit 2
                    colors[8] |= (rowdata[offset + 8] & 0x80) >> 5
                    colors[9] |= (rowdata[offset + 8] & 0x40) >> 4
                    colors[10] |= (rowdata[offset + 8] & 0x20) >> 3
                    colors[11] |= (rowdata[offset + 8] & 0x10) >> 2
                    colors[12] |= (rowdata[offset + 8] & 0x08) >> 1
                    colors[13] |= (rowdata[offset + 8] & 0x04)
                    colors[14] |= (rowdata[offset + 8] & 0x02) << 1
                    colors[15] |= (rowdata[offset + 8] & 0x01) << 2
                    # bit 3
                    colors[8] |= (rowdata[offset + 9] & 0x80) >> 4
                    colors[9] |= (rowdata[offset + 9] & 0x40) >> 3
                    colors[10] |= (rowdata[offset + 9] & 0x20) >> 2
                    colors[11] |= (rowdata[offset + 9] & 0x10) >> 1
                    colors[12] |= (rowdata[offset + 9] & 0x08)
                    colors[13] |= (rowdata[offset + 9] & 0x04) << 1
                    colors[14] |= (rowdata[offset + 9] & 0x02) << 2
                    colors[15] |= (rowdata[offset + 9] & 0x01) << 3
                    self.data[pos:pos+16] = colors[:]
                    pos += 16 # 2 bytes per tile

    def load_from_dn1(self, path):
        with open(path, 'rb') as infile:
            infile.seek(0, os.SEEK_END)
            filesize = infile.tell()
            infile.seek(0, os.SEEK_SET)

            self.count, width_bytes, self.height = HDR.unpack(infile.read(HDR.size))
            if self.count == 0 or width_bytes == 0 or self.height == 0 or self.count * width_bytes * self.height > filesize:
                if filesize == 20803:
                    print("Maybe background graphic?")
                    self.load_background_dn1(infile)
                    return
                elif filesize == 32000:
                    print("Maybe fullscreen graphic?")
                    self.load_fullscreen_dn1(infile)
                    return
                raise ValueError("File header indicates an invalid size, maybe you tried to load the wrong kind of file?")

            self.width = width_bytes * 8

            self.data = array.array('B', itertools.repeat(0, self.width * self.height * self.count))

            colors = array.array('B', itertools.repeat(0, 8))
            alphas = array.array('B', itertools.repeat(0, 8))

            # oof this is going to be slow, but the image data is tiny...
            pos = 0
            for i in range(self.count):
                for j in range(self.height):
                    rowdata = infile.read(width_bytes * 5)
                    for k in range(width_bytes):
                        # get alphas
                        alphas[0] = (rowdata[k * 5] & 0x80) >> 7
                        alphas[1] = (rowdata[k * 5] & 0x40) >> 6
                        alphas[2] = (rowdata[k * 5] & 0x20) >> 5
                        alphas[3] = (rowdata[k * 5] & 0x10) >> 4
                        alphas[4] = (rowdata[k * 5] & 0x08) >> 3
                        alphas[5] = (rowdata[k * 5] & 0x04) >> 2
                        alphas[6] = (rowdata[k * 5] & 0x02) >> 1
                        alphas[7] = (rowdata[k * 5] & 0x01)
                        # low bit 0
                        colors[0] = (rowdata[k * 5 + 1] & 0x80) >> 7
                        colors[1] = (rowdata[k * 5 + 1] & 0x40) >> 6
                        colors[2] = (rowdata[k * 5 + 1] & 0x20) >> 5
                        colors[3] = (rowdata[k * 5 + 1] & 0x10) >> 4
                        colors[4] = (rowdata[k * 5 + 1] & 0x08) >> 3
                        colors[5] = (rowdata[k * 5 + 1] & 0x04) >> 2
                        colors[6] = (rowdata[k * 5 + 1] & 0x02) >> 1
                        colors[7] = (rowdata[k * 5 + 1] & 0x01)
                        # bit 1
                        colors[0] |= (rowdata[k * 5 + 2] & 0x80) >> 6
                        colors[1] |= (rowdata[k * 5 + 2] & 0x40) >> 5
                        colors[2] |= (rowdata[k * 5 + 2] & 0x20) >> 4
                        colors[3] |= (rowdata[k * 5 + 2] & 0x10) >> 3
                        colors[4] |= (rowdata[k * 5 + 2] & 0x08) >> 2
                        colors[5] |= (rowdata[k * 5 + 2] & 0x04) >> 1
                        colors[6] |= (rowdata[k * 5 + 2] & 0x02)
                        colors[7] |= (rowdata[k * 5 + 2] & 0x01) << 1
                        # bit 2
                        colors[0] |= (rowdata[k * 5 + 3] & 0x80) >> 5
                        colors[1] |= (rowdata[k * 5 + 3] & 0x40) >> 4
                        colors[2] |= (rowdata[k * 5 + 3] & 0x20) >> 3
                        colors[3] |= (rowdata[k * 5 + 3] & 0x10) >> 2
                        colors[4] |= (rowdata[k * 5 + 3] & 0x08) >> 1
                        colors[5] |= (rowdata[k * 5 + 3] & 0x04)
                        colors[6] |= (rowdata[k * 5 + 3] & 0x02) << 1
                        colors[7] |= (rowdata[k * 5 + 3] & 0x01) << 2
                        # bit 3
                        colors[0] |= (rowdata[k * 5 + 4] & 0x80) >> 4
                        colors[1] |= (rowdata[k * 5 + 4] & 0x40) >> 3
                        colors[2] |= (rowdata[k * 5 + 4] & 0x20) >> 2
                        colors[3] |= (rowdata[k * 5 + 4] & 0x10) >> 1
                        colors[4] |= (rowdata[k * 5 + 4] & 0x08)
                        colors[5] |= (rowdata[k * 5 + 4] & 0x04) << 1
                        colors[6] |= (rowdata[k * 5 + 4] & 0x02) << 2
                        colors[7] |= (rowdata[k * 5 + 4] & 0x01) << 3
                        # palette index 0 for transparent
                        colors[0] *= alphas[0]
                        colors[1] *= alphas[1]
                        colors[2] *= alphas[2]
                        colors[3] *= alphas[3]
                        colors[4] *= alphas[4]
                        colors[5] *= alphas[5]
                        colors[6] *= alphas[6]
                        colors[7] *= alphas[7]
                        # other indices 1-16
                        colors[0] += alphas[0]
                        colors[1] += alphas[1]
                        colors[2] += alphas[2]
                        colors[3] += alphas[3]
                        colors[4] += alphas[4]
                        colors[5] += alphas[5]
                        colors[6] += alphas[6]
                        colors[7] += alphas[7]
                        self.data[pos:pos+8] = colors[:]
                        pos += 8 # 1 byte per 8 pixels

    def load_image(self, filename : str):
        image = Image.open(filename)
        if image.width % 8 != 0:
            raise ValueError("File width is not a multiple of 8!")
        if image.width != self.width or image.height != self.height * self.count:
            raise ValueError("JSON and file dimensions don't match!")
        # pillow seems to return the highest color index as the last entry
        if image.mode != 'P' or image.getcolors()[-1][1] > len(PALETTE) // 4:
            raise ValueError("Image isn't indexed or has more colors than can be used!")

        self.data = array.array('B', image.tobytes())
 
    def __init__(self, path : pathlib.Path):
        self.dn1 = False
        self.fullscreen = False
        self.background = False

        if path.suffix.lower() == '.dn1':
            self.dn1 = True
            self.load_from_dn1(path)
        elif path.suffix.lower() == '.json':
            dn1json = None
            with open(path, 'r') as infile:
                dn1json = json.loads(infile.read())
            self.count = dn1json['count']
            self.width = dn1json['width']
            self.height = dn1json['height']
            self.fullscreen = dn1json['fullscreen']
            self.background = dn1json['background']
            self.load_image(dn1json['filename'])
        else:
            raise ValueError("Couldn't determine what type of file is being loaded, file must be .json or .dn1")

    def save_png(self, path : pathlib.Path):
        outpng = f"{path}.png"
        outjson = f"{path}.json"

        image = Image.frombytes('P', (self.width, self.height * self.count), self.data.tobytes())
        if self.fullscreen or self.background:
            image.putpalette(PALETTE[4:], 'RGBA')
        else:
            image.putpalette(PALETTE, 'RGBA')
        image.save(outpng, 'PNG')

        dn1json = json.dumps({'filename': outpng,
                              'count': self.count,
                              'width': self.width,
                              'height': self.height,
                              'fullscreen': self.fullscreen,
                              'background': self.background})
        with open(outjson, 'w') as outfile:
            outfile.write(dn1json)

    def save_fullscreen_dn1(self, path : pathlib.Path):
        plane = array.array('B', itertools.repeat(0, 320*200//8))

        with open(path, 'wb') as outfile:
            # low bit 0
            for i in range(len(plane)):
                plane[i] = (self.data[i*8] & 0x01) << 7
                plane[i] |= (self.data[i*8+1] & 0x01) << 6
                plane[i] |= (self.data[i*8+2] & 0x01) << 5
                plane[i] |= (self.data[i*8+3] & 0x01) << 4
                plane[i] |= (self.data[i*8+4] & 0x01) << 3
                plane[i] |= (self.data[i*8+5] & 0x01) << 2
                plane[i] |= (self.data[i*8+6] & 0x01) << 1
                plane[i] |= (self.data[i*8+7] & 0x01)
            plane.tofile(outfile)
            # bit 1
            for i in range(len(plane)):
                plane[i] = (self.data[i*8] & 0x02) << 6
                plane[i] |= (self.data[i*8+1] & 0x02) << 5
                plane[i] |= (self.data[i*8+2] & 0x02) << 4
                plane[i] |= (self.data[i*8+3] & 0x02) << 3
                plane[i] |= (self.data[i*8+4] & 0x02) << 2
                plane[i] |= (self.data[i*8+5] & 0x02) << 1
                plane[i] |= (self.data[i*8+6] & 0x02)
                plane[i] |= (self.data[i*8+7] & 0x02) >> 1
            plane.tofile(outfile)
            # bit 2
            for i in range(len(plane)):
                plane[i] = (self.data[i*8] & 0x04) << 5
                plane[i] |= (self.data[i*8+1] & 0x04) << 4
                plane[i] |= (self.data[i*8+2] & 0x04) << 3
                plane[i] |= (self.data[i*8+3] & 0x04) << 2
                plane[i] |= (self.data[i*8+4] & 0x04) << 1
                plane[i] |= (self.data[i*8+5] & 0x04)
                plane[i] |= (self.data[i*8+6] & 0x04) >> 1
                plane[i] |= (self.data[i*8+7] & 0x04) >> 2
            plane.tofile(outfile)
            # bit 3
            for i in range(len(plane)):
                plane[i] = (self.data[i*8] & 0x08) << 4
                plane[i] |= (self.data[i*8+1] & 0x08) << 3
                plane[i] |= (self.data[i*8+2] & 0x08) << 2
                plane[i] |= (self.data[i*8+3] & 0x08) << 1
                plane[i] |= (self.data[i*8+4] & 0x08)
                plane[i] |= (self.data[i*8+5] & 0x08) >> 1
                plane[i] |= (self.data[i*8+6] & 0x08) >> 2
                plane[i] |= (self.data[i*8+7] & 0x08) >> 3
            plane.tofile(outfile)

            # fixed size, no padding needed

    def save_background_dn1(self, path : pathlib.Path):
        tilerow = array.array('B', itertools.repeat(0xFF, 10))

        width_tiles = self.width // 16 # tile width
        height_tiles = self.height // 16

        with open(path, 'wb') as outfile:
            outfile.write(b'\0\0\0') # starts with an empty 3 zeroes header

            for i in range(height_tiles):
                for j in range(width_tiles):
                    for k in range(16):
                        pos = (i * (self.width * 16)) + (j * 16) + (k * self.width)
                        # 0 and 5 should stay 0xFF
                        # low bit 0
                        tilerow[1] = (self.data[pos] & 0x01) << 7
                        tilerow[1] |= (self.data[pos+1] & 0x01) << 6
                        tilerow[1] |= (self.data[pos+2] & 0x01) << 5
                        tilerow[1] |= (self.data[pos+3] & 0x01) << 4
                        tilerow[1] |= (self.data[pos+4] & 0x01) << 3
                        tilerow[1] |= (self.data[pos+5] & 0x01) << 2
                        tilerow[1] |= (self.data[pos+6] & 0x01) << 1
                        tilerow[1] |= (self.data[pos+7] & 0x01)
                        tilerow[6] = (self.data[pos+8] & 0x01) << 7
                        tilerow[6] |= (self.data[pos+9] & 0x01) << 6
                        tilerow[6] |= (self.data[pos+10] & 0x01) << 5
                        tilerow[6] |= (self.data[pos+11] & 0x01) << 4
                        tilerow[6] |= (self.data[pos+12] & 0x01) << 3
                        tilerow[6] |= (self.data[pos+13] & 0x01) << 2
                        tilerow[6] |= (self.data[pos+14] & 0x01) << 1
                        tilerow[6] |= (self.data[pos+15] & 0x01)
                        # bit 1
                        tilerow[2] = (self.data[pos] & 0x02) << 6
                        tilerow[2] |= (self.data[pos+1] & 0x02) << 5
                        tilerow[2] |= (self.data[pos+2] & 0x02) << 4
                        tilerow[2] |= (self.data[pos+3] & 0x02) << 3
                        tilerow[2] |= (self.data[pos+4] & 0x02) << 2
                        tilerow[2] |= (self.data[pos+5] & 0x02) << 1
                        tilerow[2] |= (self.data[pos+6] & 0x02)
                        tilerow[2] |= (self.data[pos+7] & 0x02) >> 1
                        tilerow[7] = (self.data[pos+8] & 0x02) << 6
                        tilerow[7] |= (self.data[pos+9] & 0x02) << 5
                        tilerow[7] |= (self.data[pos+10] & 0x02) << 4
                        tilerow[7] |= (self.data[pos+11] & 0x02) << 3
                        tilerow[7] |= (self.data[pos+12] & 0x02) << 2
                        tilerow[7] |= (self.data[pos+13] & 0x02) << 1
                        tilerow[7] |= (self.data[pos+14] & 0x02)
                        tilerow[7] |= (self.data[pos+15] & 0x02) >> 1
                        # bit 2
                        tilerow[3] = (self.data[pos] & 0x04) << 5
                        tilerow[3] |= (self.data[pos+1] & 0x04) << 4
                        tilerow[3] |= (self.data[pos+2] & 0x04) << 3
                        tilerow[3] |= (self.data[pos+3] & 0x04) << 2
                        tilerow[3] |= (self.data[pos+4] & 0x04) << 1
                        tilerow[3] |= (self.data[pos+5] & 0x04)
                        tilerow[3] |= (self.data[pos+6] & 0x04) >> 1
                        tilerow[3] |= (self.data[pos+7] & 0x04) >> 2
                        tilerow[8] = (self.data[pos+8] & 0x04) << 5
                        tilerow[8] |= (self.data[pos+9] & 0x04) << 4
                        tilerow[8] |= (self.data[pos+10] & 0x04) << 3
                        tilerow[8] |= (self.data[pos+11] & 0x04) << 2
                        tilerow[8] |= (self.data[pos+12] & 0x04) << 1
                        tilerow[8] |= (self.data[pos+13] & 0x04)
                        tilerow[8] |= (self.data[pos+14] & 0x04) >> 1
                        tilerow[8] |= (self.data[pos+15] & 0x04) >> 2
                        # bit 3
                        tilerow[4] = (self.data[pos] & 0x08) << 4
                        tilerow[4] |= (self.data[pos+1] & 0x08) << 3
                        tilerow[4] |= (self.data[pos+2] & 0x08) << 2
                        tilerow[4] |= (self.data[pos+3] & 0x08) << 1
                        tilerow[4] |= (self.data[pos+4] & 0x08)
                        tilerow[4] |= (self.data[pos+5] & 0x08) >> 1
                        tilerow[4] |= (self.data[pos+6] & 0x08) >> 2
                        tilerow[4] |= (self.data[pos+7] & 0x08) >> 3
                        tilerow[9] = (self.data[pos+8] & 0x08) << 4
                        tilerow[9] |= (self.data[pos+9] & 0x08) << 3
                        tilerow[9] |= (self.data[pos+10] & 0x08) << 2
                        tilerow[9] |= (self.data[pos+11] & 0x08) << 1
                        tilerow[9] |= (self.data[pos+12] & 0x08)
                        tilerow[9] |= (self.data[pos+13] & 0x08) >> 1
                        tilerow[9] |= (self.data[pos+14] & 0x08) >> 2
                        tilerow[9] |= (self.data[pos+15] & 0x08) >> 3
                        tilerow.tofile(outfile)
 
    def save_dn1(self, path : pathlib.Path):
        outdn1 = pathlib.Path(f"{path}.DN1") # all caps because it's how it was
        if self.fullscreen:
            self.save_fullscreen_dn1(outdn1)
            return
        elif self.background:
            self.save_background_dn1(outdn1)
            return
        width_bytes = self.width // 8

        with open(outdn1, 'wb') as outfile:
            outfile.write(HDR.pack(self.count, width_bytes, self.height))

            pos = 0
            colors = array.array('B', itertools.repeat(0, 8))
            alphas = array.array('B', itertools.repeat(0, 8))

            outbuf = array.array('B', itertools.repeat(0, width_bytes * 5))
            for i in range(self.count):
                for j in range(self.height):
                    for k in range(width_bytes):
                        # at this point, alpha and color index values have been validated

                        # copy colors in to buffer for operations
                        colors[:] = self.data[pos:pos+8]
                        # 0 - transparent, 1 - opaque
                        alphas[0] = min(1, colors[0])
                        alphas[1] = min(1, colors[1])
                        alphas[2] = min(1, colors[2])
                        alphas[3] = min(1, colors[3])
                        alphas[4] = min(1, colors[4])
                        alphas[5] = min(1, colors[5])
                        alphas[6] = min(1, colors[6])
                        alphas[7] = min(1, colors[7])
                        # set the alpha bit
                        outbuf[k * 5] = alphas[0] << 7
                        outbuf[k * 5] |= alphas[1] << 6
                        outbuf[k * 5] |= alphas[2] << 5
                        outbuf[k * 5] |= alphas[3] << 4
                        outbuf[k * 5] |= alphas[4] << 3
                        outbuf[k * 5] |= alphas[5] << 2
                        outbuf[k * 5] |= alphas[6] << 1
                        outbuf[k * 5] |= alphas[7]
                        # convert back to EGA values
                        colors[0] -= alphas[0]
                        colors[1] -= alphas[1]
                        colors[2] -= alphas[2]
                        colors[3] -= alphas[3]
                        colors[4] -= alphas[4]
                        colors[5] -= alphas[5]
                        colors[6] -= alphas[6]
                        colors[7] -= alphas[7]
                        # low bit 0
                        outbuf[k * 5 + 1] = (colors[0] & 0x01) << 7
                        outbuf[k * 5 + 1] |= (colors[1] & 0x01) << 6
                        outbuf[k * 5 + 1] |= (colors[2] & 0x01) << 5
                        outbuf[k * 5 + 1] |= (colors[3] & 0x01) << 4
                        outbuf[k * 5 + 1] |= (colors[4] & 0x01) << 3
                        outbuf[k * 5 + 1] |= (colors[5] & 0x01) << 2
                        outbuf[k * 5 + 1] |= (colors[6] & 0x01) << 1
                        outbuf[k * 5 + 1] |= (colors[7] & 0x01)
                        # bit 1
                        outbuf[k * 5 + 2] = (colors[0] & 0x02) << 6
                        outbuf[k * 5 + 2] |= (colors[1] & 0x02) << 5
                        outbuf[k * 5 + 2] |= (colors[2] & 0x02) << 4
                        outbuf[k * 5 + 2] |= (colors[3] & 0x02) << 3
                        outbuf[k * 5 + 2] |= (colors[4] & 0x02) << 2
                        outbuf[k * 5 + 2] |= (colors[5] & 0x02) << 1
                        outbuf[k * 5 + 2] |= (colors[6] & 0x02)
                        outbuf[k * 5 + 2] |= (colors[7] & 0x02) >> 1
                        # bit 2
                        outbuf[k * 5 + 3] = (colors[0] & 0x04) << 5
                        outbuf[k * 5 + 3] |= (colors[1] & 0x04) << 4
                        outbuf[k * 5 + 3] |= (colors[2] & 0x04) << 3
                        outbuf[k * 5 + 3] |= (colors[3] & 0x04) << 2
                        outbuf[k * 5 + 3] |= (colors[4] & 0x04) << 1
                        outbuf[k * 5 + 3] |= (colors[5] & 0x04)
                        outbuf[k * 5 + 3] |= (colors[6] & 0x04) >> 1
                        outbuf[k * 5 + 3] |= (colors[7] & 0x04) >> 2
                        # bit 3
                        outbuf[k * 5 + 4] = (colors[0] & 0x08) << 4
                        outbuf[k * 5 + 4] |= (colors[1] & 0x08) << 3
                        outbuf[k * 5 + 4] |= (colors[2] & 0x08) << 2
                        outbuf[k * 5 + 4] |= (colors[3] & 0x08) << 1
                        outbuf[k * 5 + 4] |= (colors[4] & 0x08)
                        outbuf[k * 5 + 4] |= (colors[5] & 0x08) >> 1
                        outbuf[k * 5 + 4] |= (colors[6] & 0x08) >> 2
                        outbuf[k * 5 + 4] |= (colors[7] & 0x08) >> 3
                        pos += 8
                    outbuf.tofile(outfile)

            remain = (self.count * width_bytes * self.height + 3) % PAD_SIZE
            if remain > 0:
                padding = array.array('B', itertools.repeat(0, PAD_SIZE - remain))
                padding.tofile(outfile)
 
if __name__ == '__main__':
    path = pathlib.Path(sys.argv[1])

    image = DN1(path)
    if image.dn1:
        image.save_png(path.stem)
    else:
        image.save_dn1(path.stem)
