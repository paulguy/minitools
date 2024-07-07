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

# TODO: handle lzma-compressed _legacy.bin files

# relative to home
DEFAULT_STEAM_PATH = pathlib.PurePath(".local", "share", "Steam")

GAMEID = 4000
STEAM_WORKSHOP_PATH = pathlib.PurePath("steamapps", "workshop", "content", str(GAMEID))

READ_STRING_START_BUF = 256

# possibly wrap read and read_string to allow buffering when reading LZMA
def read_string(file : io.BufferedReader):
    retbuf = b''
    bufread = READ_STRING_START_BUF
    totalsize = 0
    pos = file.tell()

    while True:
        buf = file.read(bufread)
        try:
            null = buf.index(b'\0')
            totalsize += null
            retbuf += buf[:null]
            break
        except ValueError:
            pass
        retbuf += buf
        totalsize += bufread
        bufread *= 2 # maybe a bit aggressive?

    file.seek(pos+totalsize+1, os.SEEK_SET)
    return retbuf.decode('utf-8')

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
        return f"Name: {self.name}  self: {human_readable_size(self.size)}"

class GMA:
    # much from <https://github.com/Facepunch/gmad>

    GMA_MAGIC = ord('G') | (ord('M') << 8) | (ord('A') << 16) | (ord('D') << 24)

    GMA_HDR = struct.Struct("<IBQQ")
    GMA_ADDON_VER = struct.Struct("<I")
    # seems to be an incrementing file number, but it isn't used this way
    GMA_FAKE_NUM = struct.Struct("<I")
    GMA_FILE_ENT = struct.Struct("<qI")

    def __init__(self, file : io.BufferedReader, workshop_id : int):
        self.file = file
        self.workshop_id = workshop_id
        self.size = os.fstat(self.file.fileno()).st_size

        magic, version, steamid, timestamp = self.GMA_HDR.unpack(self.file.read(self.GMA_HDR.size))
        if magic != self.GMA_MAGIC:
            raise ValueError("Bad GMA file magic")

        self.version = version
        self.steamid = steamid
        self.timestamp = timestamp

        if self.version > 1:
            # apparently just, a string that needs to be read past
            _ = read_string(self.file)

        self.name = read_string(self.file)
        desc = read_string(self.file)
        self.author = read_string(self.file)
        self.addon_ver, = self.GMA_ADDON_VER.unpack(self.file.read(self.GMA_ADDON_VER.size)) # unused, i guess

        self.files = []
        self.maps = []
        filenum = 1
        filepos = 0
        while True:
            fakenum, = self.GMA_FAKE_NUM.unpack(self.file.read(self.GMA_FAKE_NUM.size))
            if fakenum == 0:
                break
            name = read_string(self.file)
            size, crc = self.GMA_FILE_ENT.unpack(self.file.read(self.GMA_FILE_ENT.size))
            entry = GMAEntry(filenum, name, filepos, size, crc)
            self.files.append(entry)
            if entry.is_map():
                self.maps.append(entry)
            filenum += 1
            filepos += size

        self.fileblock = self.file.tell()

        desc_json = json.loads(desc)
        self.description = ""
        try:
            self.description = desc_json['description']
        except KeyError:
            pass
        self.type = ""
        try:
            self.type = desc_json['type']
        except KeyError:
            pass
        self.tags = ""
        try:
            self.tags = desc_json['tags']
        except KeyError:
            pass
 
    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

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
               f"Files:\n{files}\nMaps:\n{maps}"

def get_gma_paths(steampath : str):
    modspath = pathlib.Path(steampath, STEAM_WORKSHOP_PATH)
    paths = []

    for item in modspath.iterdir():
        if not (item.is_dir() and item.name.isdecimal()):
            paths.append(("{item.name} is probably not a mod directory (non-numeric name).", 0))
            continue

        gmas = list(item.glob("*.gma", case_sensitive=False))
        if len(gmas) == 0:
            paths.append(("No GMA files.", int(item.name)))
            continue

        if len(gmas) > 1:
            paths.append(("Multiple GMA files.", int(item.name)))
            continue

        paths.append((gmas[0], int(item.name)))

    return paths

def main(path, do_list, do_only):
    paths = get_gma_paths(path)

    for path in paths:
        if len(do_only) == 0 or path[1] in do_only:
            if isinstance(path[0], str):
                print(f"{path[1]} {path[0]}")
            else:
                gma = GMA(path[0].open('rb'), path[1])
                gma.close()
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
