#!/usr/bin/python

import os
import os.path
import sqlite3
import argparse

argparser = argparse.ArgumentParser(description='Extract OGG files from Blockland addons cache.')

argparser.add_argument(metavar='filename', dest='infile', default='cache.db', help='file to extract from (default: %(default)s)', nargs='?')
argparser.add_argument(dest='outdir', default='oggs', help='directory to write ogg files too, will be created if it does not exist (default: %(default)s)', nargs='?')
args = argparser.parse_args()

total = 0
new = 0
dircreated = 0

conn = sqlite3.connect(args.infile)
c = conn.cursor()

c.execute('SELECT hash, data FROM blobs WHERE data LIKE "OggS%"')

for row in c:
    total = total + 1
    if not dircreated:
        try:
            os.mkdir(args.outdir)
        except FileExistsError:
            pass
        dircreated = 1
    filename = os.path.join(args.outdir, '{}.ogg'.format(row[0][:40]))
    print('{0}: {1}... '.format(total, filename), end='')
    if not os.path.lexists(filename):
        new = new + 1
        outf = open(filename, 'wb')
        outf.write(bytes(row[1]))
        outf.close()
        print('Extracted')
    else:
        print('Exists')

conn.close()

print('Total found: {0}  Newly extracted: {1}'.format(total, new))
