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
import hashlib
import threading
import math
from typing import Callable

try:
    from PIL import Image, UnidentifiedImageError
except ModuleNotFoundError:
    Image = None

THUMB_WIDTH = 64

# relative to home
DEFAULT_STEAM_PATH = pathlib.PurePath(".local", "share", "Steam")

GARRYSMOD_GAMEID = 4000
STEAM_WORKSHOP_PATH = pathlib.PurePath("steamapps", "workshop", "content", str(GARRYSMOD_GAMEID))

STEAM_APP_PATH = pathlib.PurePath("steamapps", "common")

GARRYSMOD_PATH = pathlib.PurePath(STEAM_APP_PATH, "GarrysMod")

DEPOTS_PATH = pathlib.PurePath("garrysmod", "cfg", "mountdepots.txt")

STEAM_DEPOTS = {
    "hl2": (220,"Half-Life 2"),
    "cstrike": (240,"Counter-Strike"),
    "dod": (300,"Day of Defeat"),
    "tf": (440,"Team Fortress 2"),
    "ep2": (420,"Half-Life 2: Episode 2"),
    "episodic": (380,"Half-Life 2: Episode 1"),
    "hl2mp": (320,"Half-Life 2: Deathmatch"),
    "lostcoast": (340,"Half-Life 2: Lost Coast"),
    "hl1": (280,"Half-Life: Source"),
    "hl1mp": (360,"Half-life Deathmatch: Source"),
    "zeno_clash": (22208,"Zeno Clash"),
    "portal": (400,"Portal"),
    "diprip": (17530,"D.I.P.R.I.P."),
    "zps": (17500,"Zombie Panic! Source"),
    "pvkii": (17570,"Pirates, Vikings and Knights II"),
    "dystopia": (17580,"Dystopia"),
    "insurgency": (17700,"Insurgency"),
    "ageofchivalry": (17510,"Age of Chivalry"),
    "left4dead2": (550,"Left 4 Dead 2"),
    "left4dead": (500,"Left 4 Dead"),
    "portal2": (620,"Portal 2"),
    "swarm": (630,"Alien Swarm"),
    "nucleardawn": (17710,"Nuclear Dawn"),
    "dinodday": (70000,"Dino D-Day"),
    "csgo": (730,"CS:Global Offensive")
}

# this is probably wrong
UNPACKED_FILE_DIRS = {"maps", "materials", "modals", "particles", "shaders", "sound"}

# probably don't need to go further
SIZE_UNITS = ('b', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB')

# 1MB seems good
READ_SIZE = 1024*1024

CHARS4 = array.array('w', ' 𜺨𜴀▘𜴉𜴊🯦𜴍𜺣𜴶𜴹𜴺▖𜵅𜵈▌𜺫🮂𜴁𜴂𜴋𜴌𜴎𜴏𜴷𜴸𜴻𜴼𜵆𜵇𜵉𜵊𜴃𜴄𜴆𜴇𜴐𜴑𜴔𜴕𜴽𜴾𜵁𜵂𜵋𜵌𜵎𜵏▝𜴅𜴈▀𜴒𜴓𜴖𜴗𜴿𜵀𜵃𜵄▞𜵍𜵐▛'
                          '𜴘𜴙𜴜𜴝𜴧𜴨𜴫𜴬𜵑𜵒𜵕𜵖𜵡𜵢𜵥𜵦𜴚𜴛𜴞𜴟𜴩𜴪𜴭𜴮𜵓𜵔𜵗𜵘𜵣𜵤𜵧𜵨🯧𜴠𜴣𜴤𜴯𜴰𜴳𜴴𜵙𜵚𜵝𜵞𜵩𜵪𜵭𜵮𜴡𜴢𜴥𜴦𜴱𜴲𜴵🮅𜵛𜵜𜵟𜵠𜵫𜵬𜵯𜵰'
                          '𜺠𜵱𜵴𜵵𜶀𜶁𜶄𜶅▂𜶬𜶯𜶰𜶻𜶼𜶿𜷀𜵲𜵳𜵶𜵷𜶂𜶃𜶆𜶇𜶭𜶮𜶱𜶲𜶽𜶾𜷁𜷂𜵸𜵹𜵼𜵽𜶈𜶉𜶌𜶍𜶳𜶴𜶷𜶸𜷃𜷄𜷇𜷈𜵺𜵻𜵾𜵿𜶊𜶋𜶎𜶏𜶵𜶶𜶹𜶺𜷅𜷆𜷉𜷊'
                          '▗𜶐𜶓▚𜶜𜶝𜶠𜶡𜷋𜷌𜷏𜷐▄𜷛𜷞▙𜶑𜶒𜶔𜶕𜶞𜶟𜶢𜶣𜷍𜷎𜷑𜷒𜷜𜷝𜷟𜷠𜶖𜶗𜶙𜶚𜶤𜶥𜶨𜶩𜷓𜷔𜷗𜷘𜷡𜷢▆𜷤▐𜶘𜶛▜𜶦𜶧𜶪𜶫𜷕𜷖𜷙𜷚▟𜷣𜷥█')

@dataclass
class FileHash():
    size : int
    digest : bytes

    def __eq__(self, other):
        return self.size == other.size and self.digest == other.digest

type FileList_T = dict[str, FileHash]
type DepotFileList_T = dict[str, FileList_T]

SHA1_T = type(hashlib.sha1())

def log_print(string : str = '', end : str = '\n'):
    sys.stderr.write(string)
    sys.stderr.write(end)

def human_readable_size(size : int):
    thousands = 0
    thousandths = 0

    while size >= 1024 and thousands < len(SIZE_UNITS) - 1:
        # probably a better way to do this with number formats but meh
        size //= 1024
        thousands += 1

    if thousands == 0:
        return f"{size}{SIZE_UNITS[thousands]}"
    else:
        return f"{size}.{thousandths}{SIZE_UNITS[thousands]}"

class ValveFile:
    # stuff for avoiding seeking for the LZMA decompressor
    READ_BUFFER_SIZE = 32768

    def consume_buffer(self, count : int, dispose : bool = False) -> bytes:
        count = min(count, self.filled)

        if not dispose:
            retbuf = self.buffer[:count].tobytes()

        if self.filled - count > 0:
            # would be faster to do a ring buffer but mehhhhhhh
            self.buffer[:self.filled-count] = self.buffer[count:self.filled]
        self.filled -= count

        if not dispose:
            return retbuf

        return b''
 
    def read(self, count : int) -> bytes:
        if self.file is None:
            return b''

        # try to empty what's in the buffer first
        retbuf = self.consume_buffer(count)

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

        try:
            retbuf = retbuf.decode('utf-8')
        except UnicodeDecodeError as e:
            raise e

        return retbuf

    def tell(self) -> int:
        if self.file is None:
            return 0

        return self.file.tell() - self.filled

    def seek(self, target, whence=0) -> int:
        if whence == os.SEEK_CUR:
            if target < 0:
                # if seeking backwards, dump buffer
                # keep the real file pointer in sync
                target -= self.filled
                self.filled = 0
            else:
                diff : int = self.filled - target
                if diff < 0:
                    # if seeking forwards would consume the entire buffer, just dump it
                    self.filled = 0
                    # keep the real file pointer in sync
                    target = -diff
                else:
                    # if seeking forwards only consumes part of the buffer, avoid the seek
                    self.consume_buffer(target, dispose=True)
        else:
            # otherwise, dump the whole buffer on absolute seeks
            self.filled = 0

        if self.filled == 0:
            return self.file.seek(target, whence)
        
        return self.tell()

    def close(self):
        if self.file is not None:
            self.lastpos = self.file.tell()
            self.file.close()
            self.file = None

    def do_open(self):
        if self.compressed:
            self.file = lzma.LZMAFile(self.path)
        else:
            self.file = self.path.open('rb')

    def reopen(self):
        self.do_open()
        self.file.seek(self.lastpos)

    def stat(self):
        return os.stat(self.file.fileno())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.file is not None:
            self.file.close()
        return False

    def __init__(self, path : pathlib.PurePath, compressed : bool=False):
        self.path = pathlib.Path(path)
        self.compressed = compressed

        self.do_open()

        stat = self.stat()
        self.size = stat.st_size
        self.filetime = stat.st_ctime

        self.buffer = array.array('B', itertools.repeat(0, self.READ_BUFFER_SIZE))
        self.filled = 0
        self.lastpos = 0

@dataclass
class GMAEntry:
    num : int
    name : str
    pos : int
    size : int
    crc : int

    def as_mappath(name : str) -> pathlib.PurPath | None:
        path : pathlib.PurePath = pathlib.PurePath(name.lower())
        # for some reason path.parent needs to be cast to a str for comparison
        if str(path.parent) == 'maps' and path.suffix == '.bsp':
            return path
        return None

    def as_thumbpath(name : str) -> pathlib.PurPath | None:
        path : pathlib.PurePath = pathlib.PurePath(name.lower())
        # for some reason path.parent needs to be cast to a str for comparison
        if str(path.parent) == 'maps/thumb':
            return path
        return None

    def __str__(self):
        return f"Name: {self.name}  Size: {human_readable_size(self.size)}"

class GMAFile(ValveFile):
    # much from <https://github.com/Facepunch/gmad>

    GMA_MAGIC = ord('G') | (ord('M') << 8) | (ord('A') << 16) | (ord('D') << 24)

    GMA_HDR = struct.Struct("<IBQQ")
    GMA_ADDON_VER = struct.Struct("<I")
    # seems to be an incrementing file number, but it isn't used this way
    GMA_FAKE_NUM = struct.Struct("<I")
    GMA_FILE_ENT = struct.Struct("<qI")

    SORTS = {
        "id": ("ID", lambda x: x.workshop_id),
        "size": ("Size", lambda x: x.size),
        "updated": ("Last Updated Time", lambda x: x.filetime),
        "published": ("Published Time", lambda x: x.timestamp),
        "name": ("Name", lambda x: x.name),
        "author": ("Author", lambda x: x.author),
        "files": ("File Count", lambda x: len(x.files)),
        "maps": ("Map Count", lambda x: len(x.maps))
    }

    def __init__(self, path : pathlib.PurePath, compressed : bool=False):
        super().__init__(path, compressed)

        self.path = path

        self.files = []
        self.maps = {}
        self.thumbs = []

        self.workshop_id = int(path.parent.name)

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
            mappath : pathlib.PurePath | None = GMAEntry.as_mappath(entry.name)
            if mappath is not None:
                self.maps[mappath] = None
            thumbpath : pathlib.PurePath | None = GMAEntry.as_thumbpath(entry.name)
            if thumbpath is not None:
                self.thumbs.append(thumbpath)
            filenum += 1
            filepos += size

        self.filenum = 0
        self.filepos = -1

        self.close()

    def read_file_data(self, maxread=-1, reading : bool = True):
        if self.filepos < 0:
            if self.filenum == len(self.files):
                return None
            self.filepos = 0
            return self.files[self.filenum].name

        to_read = self.files[self.filenum].size - self.filepos
        if maxread >= 0 and maxread < to_read:
            to_read = maxread

        have_read : int = to_read
        if reading:
            ret = self.read(to_read)
            have_read = len(ret)
        else:
            # if not reading, just skip over
            self.seek(to_read, os.SEEK_CUR)
            ret = b''

        self.filepos += have_read
        if self.filepos == self.files[self.filenum].size:
            self.filenum += 1
            self.filepos = -1

        return ret

    def read_all_data(self, dumpstate : DumpGMAFileState):
        self.reopen()

        # open an initial file
        data = self.read_file_data(READ_SIZE)
        if not dumpstate.new_file_cb(data):
            return

        while True:
            data = self.read_file_data(READ_SIZE)
            if data is None:
                dumpstate.end_file_cb()
                break
            elif isinstance(data, str):
                if not dumpstate.end_file_cb():
                    break
                if not dumpstate.new_file_cb(data):
                    break
            else:
                if not dumpstate.data_cb(data):
                    break

    def read_file_set(self, file_set : list[pathlib.PurePath], dumpstate : DumpGMAFileState):
        self.reopen()

        reading : bool = False

        # open an initial file
        data = self.read_file_data(READ_SIZE)
        if pathlib.PurePath(data) in file_set:
            reading = True
            if not dumpstate.new_file_cb(data):
                return

        while True:
            data = self.read_file_data(READ_SIZE, reading)
            if data is None:
                if reading:
                    dumpstate.end_file_cb()
                break
            elif isinstance(data, str):
                if reading:
                    if not dumpstate.end_file_cb():
                        break
                if pathlib.PurePath(data) in file_set:
                    reading = True
                    if not dumpstate.new_file_cb(data):
                        break
                else:
                    reading = False
            else:
                if reading:
                    if not dumpstate.data_cb(data):
                        break

    def get_url(self):
        return f"https://steamcommunity.com/sharedfiles/filedetails/?id={self.workshop_id}"

    def get_file_set(self):
        return {file.name for file in self.files}

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
        return f"Workshop ID: {self.workshop_id}\n" \
               f"URL: {self.get_url()}\n" \
               f"Size: {human_readable_size(self.size)}\n" \
               f"Last Updated Time: {time.asctime(time.localtime(self.filetime))}\n" \
               f"Version: {self.version}\nSteam ID?: {self.steamid}\n" \
               f"Timestamp: {timestamp}\nName: {self.name}\n" \
               f"Author: {self.author}\nType: {self.type}\n" \
               f"Tags: {tags}\nDescription: {self.description}\n" \
               f"Addon Version (unused?): {self.addon_ver}\n" \
               f"Files:\n{files}"

    def get_dict(self):
        return {'workshop_id': self.workshop_id,
                'url': self.get_url(),
                'size': self.size,
                'updated_time': self.filetime,
                'version': self.version,
                'steamid': self.steamid,
                'timestamp': self.timestamp,
                'name': self.name,
                'author': self.author,
                'type': self.type,
                'tags': self.tags,
                'description': self.description,
                'addon_ver': self.addon_ver,
                'files': [{'name': file.name, 'size': file.size} for file in self.files]}

@dataclass
class VPKEntry():
    archive : int # if 0x7FFF, the archive is the directory and archive_offset is relative to end of the tree
    preload_pos : int
    preload_bytes : int
    archive_offset : int
    archive_bytes : int

class VPKFile(ValveFile):
    # much from <https://developer.valvesoftware.com/wiki/VPK_(file_format)>

    # this'll be super basic and only read the directory tree

    DIRECTORY_SUFFIX = "_dir.vpk"
    THIS_ARCHIVE = 0x7FFF

    VPK_MAGIC = 0x34 | (0x12 << 8) | (0xAA << 16) | (0x55 << 24)

    VPK_MAGIC_HDR = struct.Struct("<II")
    VPK_1_HDR = struct.Struct("<I")
    VPK_2_HDR = struct.Struct("<IIIII")
    VPK_ENTRY = struct.Struct("<IHHIIH")

    def __init__(self, path : pathlib.PurePath):
        # no compression here but the in-place string reading from a binary file is still useful
        super().__init__(path)

        self.parent = path.parent
        self.name = path.name[:-len(VPKFile.DIRECTORY_SUFFIX)]

        self.files = {}

        magic, version = self.VPK_MAGIC_HDR.unpack(self.read(self.VPK_MAGIC_HDR.size))

        if magic != self.VPK_MAGIC:
            # probably a data file, not a directory
            self.files = None
            return

        if version == 1:
            self.treesize = self.VPK_1_HDR.unpack(self.read(self.VPK_1_HDR.size))
        elif version == 2:
            # don't care about the signatures
            self.treesize, _, _, _, _ = self.VPK_2_HDR.unpack(self.read(self.VPK_2_HDR.size))
        else:
            # unrecognized version, but a data file could in theory start with
            # the header bytes so just act like nothing happened
            self.files = None
            return

        while True:
            extension = self.read_string()
            if extension == "":
                break
            elif extension == " ":
                extension = ""
            else:
                extension = f".{extension}"
            while True:
                path = self.read_string()
                if path == "":
                    break
                elif path == " ":
                    path = ""
                else:
                    path = f"{path}/"
                while True:
                    filename = self.read_string()
                    if filename == "":
                        break
                    _, preloadBytes, archiveIndex, entryOffset, entryLength, _ = self.VPK_ENTRY.unpack(self.read(self.VPK_ENTRY.size))
                    self.files[f"{path}{filename}{extension}"] = VPKEntry(archiveIndex, self.tell(), preloadBytes, entryOffset, entryLength)
                    if preloadBytes > 0:
                        self.seek(preloadBytes, os.SEEK_CUR)

        self.close()

    def read_all_data(self, new_file_cb, data_cb, end_file_cb, priv):
        self.reopen()

        for name in self.files.keys():
            file = self.files[name]
            new_file_cb(priv, name)
            if file.preload_bytes > 0:
                self.seek(file.preload_pos)
                remaining = file.preload_bytes
                while remaining > 0:
                    to_read = remaining
                    if to_read > READ_SIZE:
                        to_read = READ_SIZE
                    data = self.read(to_read)
                    data_cb(priv, data)
                    remaining -= len(data)
            if file.archive_bytes > 0:
                infile = self
                if file.archive == VPKFile.THIS_ARCHIVE:
                    self.seek(self.treesize + file.archive_offset)
                else:
                    infile = pathlib.Path(self.parent, f"{self.name}_{file.archive:03d}.vpk").open('rb')
                    infile.seek(file.archive_offset)
                remaining = file.archive_bytes
                while remaining > 0:
                    to_read = remaining
                    if to_read > READ_SIZE:
                        to_read = READ_SIZE
                    data = infile.read(to_read)
                    data_cb(priv, data)
                    remaining -= len(data)
                if infile is not self:
                    infile.close()
            end_file_cb(priv)

def parse_acf_file(path : pathlib.PurePath):
    root = {}

    with pathlib.Path(path).open('r') as infile:
        ln = 0

        key = None
        current = [root]
        while True:
            line = infile.readline()
            if line == "":
                break
            line = line.strip()
            ln += 1

            while len(line) > 0:
                if key == None:
                    if line.startswith("\""):
                        quote = line[1:].index("\"")
                        key = line[1:quote+1]
                        line = line[quote+2:].lstrip()
                    elif line.startswith("}"):
                        current = current[:-1]
                        line = line[1:].lstrip()
                    else:
                        raise ValueError(f"Expected key in parsing ACF file ({ln}).")
                else:
                    if line.startswith("\""):
                        quote = line[1:].index("\"")
                        current[-1][key] = line[1:quote+1]
                        line = line[quote+2:].lstrip()
                    elif line.startswith("{"):
                        # create a dict in the current dict
                        current[-1][key] = {}
                        # make the same new dict the current dict
                        current.append(current[-1][key])
                        line = line[1:].lstrip()
                    else:
                        raise ValueError(f"Expected value in parsing ACF file ({ln}).")
                    key = None

    return root

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

def _get_gma_infos(path, do_only=[]):
    paths = get_gma_paths(path)
    gmas = []

    for path in paths:
        if isinstance(path, str):
            # print errors
            log_print(path)
        else:
            workshop_id = int(path.parent.name)
            if len(do_only) == 0 or workshop_id in do_only:
                gmas.append((workshop_id, path))

    return gmas

@dataclass
class DumpGMAFileState():
    path : pathlib.Path
    file : io.BufferedWriter | None
    do_dump : bool
    maps : dict[pathlib.PurePath, str | None] | None
    thumbs : dict[pathlib.PurePath, pathlib.PurePath] | None
    current_name : pathlib.PurePath | None
    current_data : bytes

    def __init__(self, path : pathlib.PurePath,
                       do_dump : bool,
                       maps : dict[pathlib.PurePath, str | None] | None,
                       thumbs : list[pathlib.PurePath] | None):
        self.path = path
        self.file = None
        self.do_dump = do_dump
        self.thumbs = None
        if maps is not None and thumbs is not None:
            self.maps = maps
            self.thumbs = {}
            for mappath in self.maps.keys():
                for thumb in thumbs:
                    if mappath.stem == thumb.stem:
                        self.thumbs[thumb] = mappath
        self.current_name = None
        self.current_data = b''

    def new_file_cb(self, name):
        if do_dump:
            extract_path = pathlib.Path(self.path.parent.name, pathlib.Path(name))
            extract_path.parent.mkdir(parents=True, exist_ok=True)
            self.file = extract_path.open('wb')

        if self.thumbs is not None and len(self.thumbs) > 0:
            path : pathlib.PurePath | None = GMAEntry.as_thumbpath(name)
            if path is not None and path in self.thumbs:
                self.current_name = path

        return True

    def data_cb(self, data):
        if do_dump:
            self.file.write(data)

        if self.current_name is not None:
            self.current_data += data

        return True

    def end_file_cb(self):
        if do_dump:
            self.file.close()

        if self.current_name is not None:
            self.maps[self.thumbs[self.current_name]] = self.current_data
            if not do_dump:
                # if not dumping and all thumbnails are extracted, stop extracting.
                all_none = True
                for gmap in self.maps.keys():
                    if self.maps[gmap] is None:
                        all_none = False
                        break
                if all_none:
                    return False
            self.current_name = None
            self.current_data = b''

        return True

def image_to_octants(data : bytes, thumb_width : int) -> str | None:
    error_r : float = 0.0
    error_g : float = 0.0
    error_b : float = 0.0
    try:
        image : Image = Image.open(io.BytesIO(data))
    except UnidentifiedImageError:
        log_print(f"WARNING: Couldn't load image in thumbnails {self.current_name}.")

        return None

    width : int = math.ceil(thumb_width / 2) * 2
    height : int = math.ceil(image.height / image.width * width / 4) * 4
    image = image.resize((width, height))
    imgdata = image.get_flattened_data()
    thumbdata = ""
    for y in range(0, height, 4):
        for x in range(0, width, 2):
            cell_img = image.crop((x, y, x + 2, y + 4)).quantize(2)
            pal = cell_img.getpalette()
            data = cell_img.get_flattened_data()
            r0 = pal[0]
            g0 = pal[1]
            b0 = pal[2]
            if len(pal) < 6:
                r1 = pal[0]
                g1 = pal[1]
                b1 = pal[2]
                thumbdata += f"\x1b[48;2;{r0};{g0};{b0}m█"
            else:
                r1 = pal[3]
                g1 = pal[4]
                b1 = pal[5]
                cell_idx : int = (data[1] * 16) + \
                                  data[0] + \
                                 (data[3] * 32) + \
                                 (data[2] * 2) + \
                                 (data[5] * 64) + \
                                 (data[4] * 4) + \
                                 (data[7] * 128) + \
                                 (data[6] * 8)
                thumbdata += f"\x1b[48;2;{r0};{g0};{b0}m\x1b[38;2;{r1};{g1};{b1}m"
                thumbdata += CHARS4[cell_idx]
            # calculate error for each border pixel and diffuse it in to neighboring cells
            if x + 2 < width:
                pixel = imgdata[width * y + x + 1]
                error_r = (pal[data[1] * 3] / 255.0) - (pixel[0] / 255.0)
                error_g = (pal[data[1] * 3 + 1] / 255.0) - (pixel[1] / 255.0)
                error_b = (pal[data[1] * 3 + 2] / 255.0) - (pixel[2] / 255.0)
                pixel = imgdata[width * y + x + 2]
                image.putpixel((x+2, y), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 3.0 * 2.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 3.0 * 2.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 3.0 * 2.0)))) * 255.0)))
                pixel = imgdata[width * (y + 1) + x + 2]
                image.putpixel((x+2, y+1), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 3.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 3.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 3.0)))) * 255.0)))

                pixel = imgdata[width * (y + 1) + x + 1]
                error_r = (pal[data[3] * 3] / 255.0) - (pixel[0] / 255.0)
                error_g = (pal[data[3] * 3 + 1] / 255.0) - (pixel[1] / 255.0)
                error_b = (pal[data[3] * 3 + 2] / 255.0) - (pixel[2] / 255.0)
                pixel = imgdata[width * y + x + 2]
                image.putpixel((x+2, y), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))
                pixel = imgdata[width * (y + 1) + x + 2]
                image.putpixel((x+2, y+1), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 2.0)))) * 255.0)))
                pixel = imgdata[width * (y + 2) + x + 2]
                image.putpixel((x+2, y+2), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))

                pixel = imgdata[width * (y + 2) + x + 1]
                error_r = (pal[data[5] * 3] / 255.0) - (pixel[0] / 255.0)
                error_g = (pal[data[5] * 3 + 1] / 255.0) - (pixel[1] / 255.0)
                error_b = (pal[data[5] * 3 + 2] / 255.0) - (pixel[2] / 255.0)
                pixel = imgdata[width * (y + 1) + x + 2]
                image.putpixel((x+2, y+1), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))
                pixel = imgdata[width * (y + 2) + x + 2]
                image.putpixel((x+2, y+2), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 2.0)))) * 255.0)))
                pixel = imgdata[width * (y + 3) + x + 2]
                image.putpixel((x+2, y+3), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))

            pixel = imgdata[width * (y + 3) + x]
            error_r = (pal[data[6] * 3] / 255.0) - (pixel[0] / 255.0)
            error_g = (pal[data[6] * 3 + 1] / 255.0) - (pixel[1] / 255.0)
            error_b = (pal[data[6] * 3 + 2] / 255.0) - (pixel[2] / 255.0)
            if x + 2 < width:
                pixel = imgdata[width * (y + 2) + x + 2]
                image.putpixel((x+2, y+2), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 7.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 7.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 7.0)))) * 255.0)))
                pixel = imgdata[width * (y + 3) + x + 2]
                image.putpixel((x+2, y+3), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 7.0 * 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 7.0 * 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 7.0 * 2.0)))) * 255.0)))
            if y + 4 < height:
                pixel = imgdata[width * (y + 4) + x]
                image.putpixel((x, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 7.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 7.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 7.0)))) * 255.0)))
                pixel = imgdata[width * (y + 4) + x + 1]
                image.putpixel((x+1, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 7.0 * 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 7.0 * 2.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 7.0 * 2.0)))) * 255.0)))
            if x + 2 < width and y + 4 < height:
                pixel = imgdata[width * (y + 4) + x + 2]
                image.putpixel((x+2, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 7.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 7.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 7.0)))) * 255.0)))
 
            if y + 4 < height:
                pixel = imgdata[width * (y + 3) + x + 1]
                error_r = (pal[data[7] * 3] / 255.0) - (pixel[0] / 255.0)
                error_g = (pal[data[7] * 3 + 1] / 255.0) - (pixel[1] / 255.0)
                error_b = (pal[data[7] * 3 + 2] / 255.0) - (pixel[2] / 255.0)
                if x > 0:
                    pixel = imgdata[width * (y + 4) + x - 1]
                    image.putpixel((x-1, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                                int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                                int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))
                pixel = imgdata[width * (y + 4) + x]
                image.putpixel((x, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 2.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 2.0)))) * 255.0),
                                          int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 2.0)))) * 255.0)))
                pixel = imgdata[width * (y + 4) + x + 1]
                image.putpixel((x+1, y+4), (int(max(0.0, min(1.0, ((pixel[0] / 255.0) + (error_r / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[1] / 255.0) + (error_g / 4.0)))) * 255.0),
                                            int(max(0.0, min(1.0, ((pixel[2] / 255.0) + (error_b / 4.0)))) * 255.0)))

        thumbdata += "\x1b[m\n"
    
    return thumbdata

def print_maps(gma : GMAFile, thumb_width : int):
    if len(gma.maps) > 0:
        print(f"Maps:")
        for i, gmap in enumerate(gma.maps.keys()):
            if thumb_width > 0:
                if gma.maps[gmap] is not None:
                    if i > 0:
                        print()
                    print(image_to_octants(gma.maps[gmap], thumb_width), end='')
            print(f" {gmap.stem}")

class RangeIterator:
    def parse_number(num : str, last : int) -> int:
        try:
            val = int(num)
        except ValueError:
            raise ValueError(f"Item {num} must be an integer.")
        if val < 0:
            # make negative values start from the last value
            val += last
        if val < 0 or val >= last:
            raise IndexError(f"Index {num} out of range.")

        return val

    def __init__(self, ranges : str | None, last : int):
        self.blocks = []
        self.num = -1

        if ranges is None:
            if last == 1:
                self.blocks.append(0)
            else:
                self.blocks.append((0, last - 1))
        else:
            blocks = ranges.split(',')
            for block in blocks:
                colon = -1
                try:
                    colon = block.index(':')
                except ValueError:
                    pass
                if colon < 0:
                    self.blocks.append(RangeIterator.parse_number(block, last))
                else:
                    first = 0
                    if colon > 0:
                        first = RangeIterator.parse_number(block[:colon], last)
                    second = last - 1
                    if colon < len(block) - 1:
                        second = RangeIterator.parse_number(block[colon+1:], last)
                    if first == second:
                        self.blocks.append(first)
                    else:
                        if first > second:
                            raise ValueError("Second value in a range must be later in succession than the first.")
                        self.blocks.append((first, second))

    def __iter__(self):
        return self

    def __next__(self):
        if len(self.blocks) == 0:
            raise StopIteration

        if isinstance(self.blocks[0], int):
            # if item is an integer, remove it and return it
            val = self.blocks[0]
            self.blocks = self.blocks[1:]
            return val

        if self.num < 0:
            # if item is a tuple, and number is negative, set it to the first value in this range
            self.num = self.blocks[0][0]
            return self.num
        elif self.num == self.blocks[0][1] - 1:
            # if the number is one less than the last value, remove the item, save the last value, mark num as unset and return the last value
            self.blocks = self.blocks[1:]
            val = self.num + 1
            self.num = -1
            return val

        # otherwise, increment the number and return it
        self.num += 1

        return self.num


def get_gma_infos(path : pathlib.Path,
                  do_list : bool,
                  do_dump : bool,
                  do_json : bool,
                  thumb_width : int,
                  do_only : list[int],
                  sort_list : list[tuple[str, Callable[GMAFile]]],
                  ranges : str):
    # ugh big ugly do everything function
    do_thumbs = thumb_width > 0

    gma_paths = _get_gma_infos(path, do_only)
    gmas = []

    for path in gma_paths:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        gma = GMAFile(path[1], compressed)

        if do_dump or do_thumbs:
            maps = None
            thumbs = None
            # TODO: move thumbnail extraction until the end so only the needed ones get extracted
            if do_thumbs:
                maps = gma.maps
                thumbs = gma.thumbs
            dumpstate = DumpGMAFileState(path[1], do_dump, maps, thumbs)

            if do_dump:
                gma.read_all_data(dumpstate)
            else:
                gma.read_file_set(thumbs, dumpstate)

        gma.close()

        gmas.append(gma)

    for sort in sort_list:
        gmas = sorted(gmas, key=sort[1])

    if do_json:
        gmadicts = [gma.get_dict() for gma in gmas]
        print(json.dumps(gmadicts))
    else:
        r = RangeIterator(':', len(gmas))
        try:
            r = RangeIterator(ranges, len(gmas))
        except Exception as e:
            log_print(f"WARNING: Bad range: {ranges} : {e}, ignoring...")
        for i in RangeIterator(ranges, len(gmas)):
            gma = gmas[i]
            print(i, end=' ')
            if do_list:
                print(f"{gma.workshop_id} {gma.name} {human_readable_size(gma.size)}")
                print_maps(gma, thumb_width)
            else:
                print(gma)
                print_maps(gma, thumb_width)
            print()

class SteamDepot:
    def __init__(self,
                 depot_name : str,
                 game_id : int,
                 game_name : str,
                 path : pathlib.PurePath,
                 source : None | VPKFile | GMAFile):
        self.depot_name = depot_name
        self.game_id = game_id
        self.game_name = game_name
        self.path = path
        self.source = source
        self.files = []

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return f"Depot: {self.depot_name}  ID: {self.game_id}  Name: {self.game_name}  Path: {self.path}  Files: {len(self.files)}"

    def set_files(self, files : FileList_T):
        self.files = files

    def get_files(self) -> FileList_T:
        return self.files

def get_mounted_depots(steampath : pathlib.PurePath):
    depotspath = pathlib.PurePath(steampath, GARRYSMOD_PATH, DEPOTS_PATH)

    depotdata = parse_acf_file(depotspath)

    # garry's mod is probably always mounted?
    depots = [SteamDepot("garrysmod",
                         GARRYSMOD_GAMEID,
                         "Garry's Mod",
                         pathlib.PurePath(steampath, GARRYSMOD_PATH, "garrysmod"),
                         None)]

    depotdict = depotdata["gamedepotsystem"]
    for depot in depotdict.keys():
        if int(depotdict[depot]) != 0:
            depotinfo = STEAM_DEPOTS[depot]
            acfpath = pathlib.Path(steampath, "steamapps", f"appmanifest_{depotinfo[0]}.acf")
            try:
                depotdata = parse_acf_file(acfpath)
            except FileNotFoundError:
                log_print(f"WARNING: Could not load app manifest for {depotinfo[0]} ({depotinfo[1]})!")
                continue
            depots.append(SteamDepot(depot,
                                     depotinfo[0],
                                     depotinfo[1],
                                     pathlib.PurePath(steampath, STEAM_APP_PATH, depotdata["AppState"]["installdir"], depot),
                                     None))

    return depots

def gather_files(path : pathlib.PurePath):
    filelist = {}

    for dirname in UNPACKED_FILE_DIRS:
        for root, dirs, files in pathlib.Path(path, dirname).walk():
            for file in files:
                # get the relative path and join its directory parts back together
                # in the same way as other gmod paths are
                name = '/'.join(pathlib.PurePath(root, file).relative_to(path).parts)
                hashobj = hashlib.sha1(usedforsecurity=False)
                size = 0
                with pathlib.Path(root, file).open('rb') as infile:
                    while True:
                        data = infile.read(READ_SIZE)
                        if len(data) == 0:
                            break
                        size += len(data)
                        hashobj.update(data)
                filelist[name] = FileHash(size, hashobj.digest())

    return filelist

@dataclass
class HashFileState():
    hashes : FileList_T
    hashobj : SHA1_T | None
    curname : str | None
    size : int

    def __init__(self):
        self.hashes = {}
        self.hashobj = None
        self.curname = None
        self.size = 0

def hash_new_file_cb(priv, name):
    priv.hashobj = hashlib.sha1(usedforsecurity=False)
    priv.curname = name
    priv.size = 0

    return True

def hash_data_cb(priv, data):
    priv.size += len(data)
    priv.hashobj.update(data)

    return True

def hash_end_file_cb(priv):
    priv.hashes[priv.curname] = FileHash(priv.size, priv.hashobj.digest())

    return True

def get_cache_path(steampath : pathlib.PurePath, depot : SteamDepot):
    path = depot.path.relative_to(pathlib.Path(steampath, STEAM_APP_PATH))
    outname = str('_'.join(path.parts))
    if outname.endswith(VPKFile.DIRECTORY_SUFFIX):
        outname = outname[:-len(VPKFile.DIRECTORY_SUFFIX)]
    outname += ".vpkhashcache"

    return path, outname

def write_cache(steampath : pathlib.PurePath, depot : SteamDepot, time : float):
    path, outname = get_cache_path(steampath, depot)

    #print(f"Writing cache for {path} to {outname}.")
    with open(outname, 'w') as cachefile:
        cachefile.write(f"{time}\n")
        for file in depot.files.keys():
            hexstr = ""
            for b in depot.files[file].digest:
                hexstr += f"{b:02X}"
            cachefile.write(f"{depot.files[file].size} {hexstr} {file}\n")

def read_cache(steampath : pathlib.PurePath, depot : SteamDepot, time : float):
    filelist : FileList_T = {}

    path, outname = get_cache_path(steampath, depot)

    try:
        with open(outname, 'r') as cachefile:
            #print(f"Reading cache for {path} from {outname}.")
            cachetime = float(cachefile.readline())
            if cachetime < time:
                # if cache is older than the file time, the cache is invalid
                return None
            for line in cachefile.readlines():
                size, digest, name = line.split(maxsplit=2)
                digestarray = array.array('B', itertools.repeat(0, len(digest) // 2))
                for i in range(len(digestarray)):
                    digestarray[i] = int(digest[i*2:(i*2)+1], base=16)
                # remove the newline
                filelist[name[:-1]] = FileHash(size, digestarray.tobytes())
    except FileNotFoundError:
        return None

    return filelist

def list_depot(steampath : pathlib.PurePath, depot : SteamDepot):
    newdepots = [depot]

    for item in pathlib.Path(depot.path).glob(f"*{VPKFile.DIRECTORY_SUFFIX}", case_sensitive=False):
        newdepots.append(SteamDepot(depot.depot_name,
                                    depot.game_id,
                                    depot.game_name,
                                    item,
                                    VPKFile(pathlib.PurePath(depot.path, item))))

    return newdepots

def get_depots(steampath : pathlib.PurePath):
    depots = get_mounted_depots(steampath)
    newdepots = []
    for depot in depots:
        newdepots.extend(list_depot(steampath, depot))

    return newdepots

def hash_naked_files(steampath : pathlib.PurePath, depot : SteamDepot):
    stat = os.stat(depot.path)
    naked_files = read_cache(steampath, depot, stat.st_ctime)
    if naked_files is None:
        naked_files = gather_files(depot.path)
        depot.set_files(naked_files)
        write_cache(steampath, depot, stat.st_ctime)
        return False
    else:
        depot.set_files(naked_files)
    return True

def hash_gma_files(depot : SteamDepot):
    priv = HashFileState()
    depot.source.read_all_data(hash_new_file_cb, hash_data_cb, hash_end_file_cb, priv)
    depot.set_files(priv.hashes)
    depot.source.close()
    # never cached
    return False

def hash_vpk_files(steampath : pathlib.PurePath, depot : SteamDepot):
    depot_files = read_cache(steampath, depot, depot.source.filetime)
    if depot_files is None:
        priv = HashFileState()
        depot.source.read_all_data(hash_new_file_cb, hash_data_cb, hash_end_file_cb, priv)
        depot.source.close()
        depot.set_files(priv.hashes)
        write_cache(steampath, depot, depot.source.filetime)
        return False
    else:
        depot.set_files(depot_files)
        depot.source.close()
    return True

def hash_depot(sem : threading.Semaphore, steampath : pathlib.PurePath, depot : SteamDepot):
    cached = False
    if depot.source is None:
        cached = hash_naked_files(steampath, depot)
    elif isinstance(depot.source, VPKFile):
        cached = hash_vpk_files(steampath, depot)
    elif isinstance(depot.source, GMAFile):
        cached = hash_gma_files(depot)
    else:
        raise RuntimeError("Couldn't determine depot source (this is a bug!)")
    log_print(f"Hashed {depot.path}", end='')
    if cached:
        log_print(" (cached)")
    else:
        log_print()
    sem.release()

def depot_sort_key(depot : SteamDepot):
    if depot.source is None:
        return 1<<31 # put bare directories further up

    return depot.source.size

def collisions_scan(steampath : pathlib.PurePath, do_only=[], num_threads=1):
    log_print("Gathering mounted files...")
    depots = get_depots(steampath)

    log_print("Gathering addon files...")
    gmas = _get_gma_infos(steampath, do_only)

    for path in gmas:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        gma = GMAFile(path[1], compressed)
        depots.append(SteamDepot(f"addon_{gma.workshop_id}",
                                 gma.workshop_id,
                                 gma.name,
                                 path[1],
                                 gma))

    # get the larger files first to minimize time at the end potentially
    # waiting on fewer large tasks
    depots = sorted(depots, key=depot_sort_key, reverse=True)

    log_print(f"Hashing files... ({num_threads} thread(s))")
    sem = threading.Semaphore(num_threads)
    threads = []
    for depot in depots:
        sem.acquire()
        threads.append(threading.Thread(target=hash_depot, args=(sem, steampath, depot)))
        threads[-1].start()
    # wait for the rest to finish
    for i in range(num_threads):
        sem.acquire()

    log_print("Finding collisions...")
    depotsets = []
    for depot in depots:
        depotsets.append(set(depot.files.keys()))

    collisions = {}
    for num1, depot1 in enumerate(depotsets):
        for num2, depot2 in enumerate(depotsets[num1+1:]):
            intersection = depot1.intersection(depot2)
            for item in intersection:
                if depots[num1].files[item] != depots[num1+1+num2].files[item]:
                    # if size and hash differs, add it
                    if item in collisions:
                        collisions[item].add(depots[num1])
                        collisions[item].add(depots[num1+1+num2])
                    else:
                        collisions[item] = {depots[num1], depots[num1+1+num2]}

    for collision in collisions.keys():
        addon = False
        for depot in collisions[collision]:
            if isinstance(depot.source, GMAFile):
                addon = True
        if addon:
            print(f"File: {collision}")
            for depot in collisions[collision]:
                print(f" Source: {depot.game_name}  Path: {depot.path}")
            print()

def make_sort_list(sort_list_string):
    sort_list = []

    for criteria in sort_list_string.split(","):
        try:
            sort_list.append(GMAFile.SORTS[criteria.lower()])
        except KeyError:
            raise ValueError("Invalid sort criteria: {criteria}")

    return sort_list

def usage(app):
    print(f"USAGE: {app} [--list | --sort[=]<criteria[,criteria,...]> | --dump | --steampath[=]<path to steam> | <workshop ID>]...\n"
          "           --collisions-scan [--steampath[=]<path to steam> | --threads[=]<number of threads>]... | --thumbs[[=]<width>]\n"
          "           --ranges[=]<range[,range,...]")
    print("\nSort criterias:\n")
    for sort in GMAFile.SORTS.keys():
        print(f"{sort} : {GMAFile.SORTS[sort][0]}")

if __name__ == '__main__':
    argv = sys.argv[1:]
    do_usage = False
    do_collisions = False
    do_list = False
    do_dump = False
    do_json = False
    thumb_width = -1
    do_only = []
    sort_list = []
    path = pathlib.Path.home().joinpath(DEFAULT_STEAM_PATH)
    threads = 1
    ranges = None

    # ultra simple args parsing
    while len(argv) > 0:
        if argv[0].startswith('--'):
            arg = argv[0][2:]
            if arg == 'list':
                do_list = True
            elif arg.startswith('sort='):
                sort_list = make_sort_list(arg[5:])
            elif arg == 'sort':
                sort_list = make_sort_list(argv[1])
                argv = argv[1:]
            elif arg == 'dump':
                do_dump = True
            elif arg == 'collisions-scan':
                do_collisions = True
            elif arg == 'json':
                do_json = True
            elif arg.startswith('steampath='):
                path = pathlib.PurePath(arg[10:])
            elif len(argv) > 1 and arg == 'steampath':
                path = pathlib.PurePath(argv[1])
                argv = argv[1:]
            elif arg.startswith('threads='):
                threads = int(arg[8:])
                if threads < 1:
                    print("Threads must be greater than 0.")
                    do_usage = True
                    break
            elif len(argv) > 1 and arg == 'threads':
                threads = int(argv[1])
                if threads < 1:
                    print("Threads must be greater than 0.")
                    do_usage = True
                    break
                argv = argv[1:]
            elif arg == 'thumbs':
                if Image is None:
                    print("Thumbnails requested but pillow not installed.")
                    do_usage = True
                    break
                thumb_width = THUMB_WIDTH
                if len(argv) > 1:
                    try:
                        thumb_width = int(argv[1])
                        if thumb_width > 512:
                            # filter out values that are larger than the thumbnail size and larger than a reasonable size
                            # in case a workshop item is added.  Workshop IDs are global to the entirety of steam so i don't
                            # think gmod even has any IDs this low.  Would be curious to know though!
                            thumb_width = THUMB_WIDTH
                        else:
                            argv = argv[1:]
                    except ValueError:
                        pass
                if thumb_width < 1:
                    print("Thumbnails width must be greater than 0.")
                    do_usage = True
                    break
            elif arg.startswith('thumbs='):
                thumb_width = int(arg[7:])
                if thumb_width < 1:
                    print("Thumbnails width must be greater than 0.")
                    do_usage = True
                    break
            elif arg == 'ranges':
                ranges = argv[1]
                argv = argv[1:]
            elif arg.startswith('ranges='):
                ranges = arg[7:]
            else:
                do_usage = True
                break
            argv = argv[1:]
        else:
            try:
                do_only.append(int(argv[0]))
            except ValueError:
                do_usage = True
                break
            argv = argv[1:]

    if do_usage:
        usage(sys.argv[0])
    elif do_collisions:
        collisions_scan(path, do_only, threads)
    else:
        get_gma_infos(path, do_list, do_dump, do_json, thumb_width, do_only, sort_list, ranges)
