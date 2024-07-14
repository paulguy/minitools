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
    def load_from_dn1(self, path):
        with open(path, 'rb') as infile:
            infile.seek(0, os.SEEK_END)
            filesize = infile.tell()
            infile.seek(0, os.SEEK_SET)

            self.count, width_bytes, self.height = HDR.unpack(infile.read(HDR.size))
            if self.count == 0 or width_bytes == 0 or self.height == 0 or self.count * width_bytes * self.height > filesize:
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
            self.load_image(dn1json['filename'])
        else:
            raise ValueError("Couldn't determine what type of file is being loaded, file must be .json or .dn1")

    def save_png(self, path : pathlib.Path):
        outpng = f"{path}.png"
        outjson = f"{path}.json"

        image = Image.frombytes('P', (self.width, self.height * self.count), self.data.tobytes())
        image.putpalette(PALETTE, 'RGBA')
        image.save(outpng, 'PNG')

        dn1json = json.dumps({'filename': outpng, 'count': self.count, 'width': self.width, 'height': self.height})
        with open(outjson, 'w') as outfile:
            outfile.write(dn1json)

    def save_dn1(self, path : pathlib.Path):
        outdn1 = f"{path}.DN1" # all caps because it's how it was
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
