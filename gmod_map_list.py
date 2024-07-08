#!/usr/bin/env python

import pathlib
import sys
import struct
import os
import io
import time
import json
from dataclasses import dataclass
import re
import array
import itertools
import lzma

# TODO: handle lzma-compressed _legacy.bin files

# relative to home
DEFAULT_STEAM_PATH = pathlib.PurePath(".local", "share", "Steam")

GAMEID = 4000
STEAM_WORKSHOP_PATH = pathlib.PurePath("steamapps", "workshop", "content", str(GAMEID))

# probably don't need to go further
SIZE_UNITS = ('b', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB')

def human_readable_size(size : int):
    thousands = 0
    thousandths = 0

    while size >= 1024 and thousands < len(SIZE_UNITS) - 1:
        # probably a better way to do this with number formats but meh
        thousandths = int(size / 1024 * 10 % 10)
        size //= 1024
        thousands += 1

    if thousands == 0:
        return f"{size}{SIZE_UNITS[thousands]}"
    else:
        return f"{size}.{thousandths}{SIZE_UNITS[thousands]}"

@dataclass
class GMAEntry:
    num : int
    name : str
    pos : int
    size : int
    crc : int

    map_re = re.compile(".+\\.bsp$")

    def is_map(self):
        return self.map_re.match(self.name)

    def __str__(self):
        return f"Name: {self.name}  Size: {human_readable_size(self.size)}"

class GMAFile:
    # much from <https://github.com/Facepunch/gmad>

    GMA_MAGIC = ord('G') | (ord('M') << 8) | (ord('A') << 16) | (ord('D') << 24)

    GMA_HDR = struct.Struct("<IBQQ")
    GMA_ADDON_VER = struct.Struct("<I")
    # seems to be an incrementing file number, but it isn't used this way
    GMA_FAKE_NUM = struct.Struct("<I")
    GMA_FILE_ENT = struct.Struct("<qI")

    # stuff for avoiding seeking for the LZMA decompressor
    READ_BUFFER_SIZE = 32768

    def read(self, count : int) -> bytes:
        if self.file is None:
            return b''

        retbuf = b''

        # try to empty what's in the buffer first
        if self.filled > 0:
            if count < self.filled:
                retbuf = self.buffer[:count].tobytes()
                # would be faster to do a ring buffer but mehhhhhhh
                self.buffer[:self.filled-count] = self.buffer[count:self.filled]
                self.filled -= count
            else:
                retbuf = self.buffer[:self.filled].tobytes()
                self.filled = 0

        # then read the rest from the file
        if len(retbuf) < count:
            buf = self.file.read(count - len(retbuf))
            retbuf += buf

        return retbuf

    def read_string(self) -> str:
        if self.file is None:
            return ''

        retbuf = b''
        have_read = 0
        found = False

        while True:
            try:
                # find the null in the buffer this time around
                null = self.buffer[:self.filled].index(0)
                retbuf += self.buffer[:null].tobytes()
                # move the unread buffer contents to the beginning
                self.buffer[:self.filled-(null+1)] = self.buffer[null+1:self.filled]
                self.filled -= null + 1
                found = True
            except ValueError:
                # none found, just empty it
                retbuf += self.buffer[:self.filled].tobytes()
                self.filled = 0

            if found:
                break

            # refill the buffer
            buf = self.file.read(len(self.buffer))
            if len(buf) == 0:
                return retbuf

            self.buffer[:len(buf)] = array.array('B', buf)
            self.filled = len(buf)

        return retbuf.decode('utf-8')

    def tell(self) -> int:
        if self.file is None:
            return 0

        return self.file.tell() - self.filled

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.file.close()
        return False

    # TODO: Functions for reading out files from gma?

    def __init__(self, path : pathlib.PurePath, compressed : bool=False):
        if compressed:
            self.file = lzma.LZMAFile(path)
        else:
            self.file = pathlib.Path(path).open('rb')

        self.buffer = array.array('B', itertools.repeat(0, self.READ_BUFFER_SIZE))
        self.filled = 0

        self.files = []
        self.maps = []

        self.workshop_id = int(path.parent.name)
        self.size = os.fstat(self.file.fileno()).st_size

        magic, version, steamid, timestamp = self.GMA_HDR.unpack(self.read(self.GMA_HDR.size))
        if magic != self.GMA_MAGIC:
            raise ValueError("Bad GMA file magic")

        self.version = version
        self.steamid = steamid
        self.timestamp = timestamp

        if self.version > 1:
            # apparently just, a string that needs to be read past
            _ = self.read_string()

        self.name = self.read_string()
        desc = self.read_string()
        self.author = self.read_string()
        self.addon_ver, = self.GMA_ADDON_VER.unpack(self.read(self.GMA_ADDON_VER.size)) # unused, i guess

        self.description = ""
        self.type = ""
        self.tags = ""
        try:
            desc_json = json.loads(desc)
            try:
                self.description = desc_json['description']
            except KeyError:
                pass
            try:
                self.type = desc_json['type']
            except KeyError:
                pass
            try:
                self.tags = desc_json['tags']
            except KeyError:
                pass
        except json.decoder.JSONDecodeError:
            # very old maps seem not to have JSON
            self.description = desc

        filenum = 1
        filepos = 0
        while True:
            fakenum, = self.GMA_FAKE_NUM.unpack(self.read(self.GMA_FAKE_NUM.size))
            if fakenum == 0:
                break
            name = self.read_string()
            size, crc = self.GMA_FILE_ENT.unpack(self.read(self.GMA_FILE_ENT.size))
            entry = GMAEntry(filenum, name, filepos, size, crc)
            self.files.append(entry)
            if entry.is_map():
                self.maps.append(entry)
            filenum += 1
            filepos += size

        self.fileblock = self.file.tell()

    def mapnames(self):
        maps = ""
        for gmap in self.maps:
            maps += f" {gmap.name}\n"
        return maps

    def get_url(self):
        return f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.workshop_id}"

    def __str__(self):
        timestamp = time.asctime(time.gmtime(self.timestamp))
        tags = ""
        for tag in self.tags:
            if len(tags) == 0:
                tags += tag
            else:
                tags += f" {tag}"
        files = ""
        for file in self.files:
            files += f" {file}\n"
        maps = self.mapnames()
        return f"Workshop ID: {self.workshop_id}\n" \
               f"URL: {self.get_url()}\n" \
               f"Size: {human_readable_size(self.size)}\nVersion: {self.version}\n" \
               f"Steam ID?: {self.steamid}\nTimestamp: {timestamp}\n" \
               f"Name: {self.name}\nAuthor: {self.author}\nType: {self.type}\n" \
               f"Tags: {tags}\nDescription: {self.description}\n" \
               f"Addon Version (unused?): {self.addon_ver}\n" \
               f"Files:\n{files}\nMaps:\n{maps}"

def get_gma_paths(steampath : str):
    modspath = pathlib.Path(steampath, STEAM_WORKSHOP_PATH)
    paths = []

    for item in modspath.iterdir():
        if not (item.is_dir() and item.name.isdecimal()):
            paths.append(f"{item.name} is probably not a mod directory (non-numeric name).")
            continue

        gmas = list(item.glob("*.gma", case_sensitive=False))
        gmas.extend(item.glob("*_legacy.bin", case_sensitive=False))

        if len(gmas) == 0:
            try:
                _ = item.iterdir().__next__()
                paths.append(f"No GMA files in {item.name}.")
            except StopIteration:
                paths.append(f"Empty direcotry in {item.name}.")
            continue

        if len(gmas) > 1:
            paths.append(f"Multiple GMA files in {item.name}.")
            continue

        paths.append(gmas[0])

    return paths

def main(path, do_list=False, do_only=[]):
    paths = get_gma_paths(path)
    gmas = []

    for path in paths:
        if isinstance(path, str):
            print(path)
        else:
            workshop_id = int(path.parent.name)
            if len(do_only) == 0 or workshop_id in do_only:
                gmas.append((workshop_id, path))

    gmas = sorted(gmas, key=lambda path: path[0])

    for path in gmas:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        with GMAFile(path[1], compressed) as gma:
            if do_list:
                print(f"{gma.workshop_id} {gma.name} {human_readable_size(gma.size)}")
                maps = gma.mapnames()
                if len(maps) > 0:
                    print(f"Maps:\n{maps}")
            else:
                print(gma)

def usage(app):
    print(f"USAGE: {app} [--list | --steampath[=]<path to steam> | <workshop ID>]...")

if __name__ == '__main__':
    argv = sys.argv[1:]
    do_usage = False
    do_list = False
    do_only = []
    path = pathlib.Path.home().joinpath(DEFAULT_STEAM_PATH)

    # ultra simple args parsing
    while len(argv) > 0:
        if argv[0].startswith('--'):
            arg = argv[0][2:]
            if arg == 'list':
                do_list = True
                argv = argv[1:]
            elif arg.startswith('steampath='):
                path = pathlib.PurePath(arg[10:])
                argv = argv[1:]
            elif len(argv) > 1 and arg == 'steampath':
                path = pathlib.PurePath(argv[1])
                argv = argv[2:]
            else:
                do_usage = True
                break
        else:
            try:
                do_only.append(int(argv[0]))
            except ValueError:
                do_usage = True
                break
            argv = argv[1:]

    if do_usage:
        usage(sys.argv[0])
    else:
        main(path, do_list, do_only)
