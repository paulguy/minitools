#!/usr/bin/env python

import sys

SUFFIXES = ('', 'KiB', 'MiB', 'GiB', 'TiB')

def do_decode(infile, human):
    for line in infile:
        line = line[:-1]
        newline = line.strip()
        lpad = line[:len(line)-len(newline)]
        num, rest = newline.split(maxsplit=1)
        start, end = num.split(sep='-')
        start = int(start, base=16)
        end = int(end, base=16)
        size = end - start + 1
        suffix = ''
        if human:
            for suffix in SUFFIXES:
                if size // 1024 > 0:
                    size //= 1024
                else:
                    break
        print("{}{} {}{} {}".format(lpad, hex(start), size, suffix, rest))

def decode(filename, human=False):
    if filename == '-':
        do_decode(sys.stdin, human)
    else:
        with open(filename, 'r') as infile:
            do_decode(infile, human)

if __name__ == '__main__':
    human = False

    if len(sys.argv) > 1:
        if len(sys.argv) > 2 and sys.argv[1] == '-h':
            human = True
            filename = sys.argv[2]
        else:
            filename = sys.argv[1]

        decode(filename, human)
    else:
        print("USAGE: {} [-h] <filename>".format(sys.argv[0]))
