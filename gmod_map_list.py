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

@dataclass
class FileHash():
    size : int
    digest : bytes

    def __eq__(self, other):
        return self.size == other.size and self.digest == other.digest

type FileList_T = dict[str, FileHash]
type DepotFileList_T = dict[str, FileList_T]

SHA1_T = type(hashlib.sha1())

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

class ValveFile:
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

        try:
            retbuf = retbuf.decode('utf-8')
        except UnicodeDecodeError as e:
            print(retbuf)
            raise e

        return retbuf

    def tell(self) -> int:
        if self.file is None:
            return 0

        return self.file.tell() - self.filled

    def seek(self, target, whence=0):
        if whence == os.SEEK_CUR:
            target -= self.filled
        # could be more efficient and reuse potential existing buffer but it doesn't matter much
        self.filled = 0
        self.file.seek(target, whence)

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def stat(self):
        return os.stat(self.file.fileno())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if self.file is not None:
            self.file.close()
        return False

    def __init__(self, path : pathlib.PurePath, compressed : bool=False):
        if compressed:
            self.file = lzma.LZMAFile(path)
        else:
            self.file = pathlib.Path(path).open('rb')

        self.buffer = array.array('B', itertools.repeat(0, self.READ_BUFFER_SIZE))
        self.filled = 0

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
        self.maps = []

        self.workshop_id = int(path.parent.name)
        stat = self.stat()
        self.size = stat.st_size

        magic, version, steamid, timestamp = self.GMA_HDR.unpack(self.read(self.GMA_HDR.size))
        if magic != self.GMA_MAGIC:
            raise ValueError("Bad GMA file magic")

        self.version = version
        self.steamid = steamid
        self.timestamp = timestamp

        self.filetime = stat.st_ctime

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

        self.filenum = 0
        self.filepos = -1

    def read_file_data(self, maxread=-1):
        if self.filepos < 0:
            if self.filenum == len(self.files):
                return None
            self.filepos = 0
            return self.files[self.filenum].name

        to_read = self.files[self.filenum].size - self.filepos
        if maxread >= 0 and maxread < to_read:
            to_read = maxread

        ret = self.read(to_read)
        self.filepos += len(ret)
        if self.filepos == self.files[self.filenum].size:
            self.filenum += 1
            self.filepos = -1

        return ret

    def read_all_data(self, new_file_cb, data_cb, end_file_cb, priv):
        # open an initial file
        data = self.read_file_data(READ_SIZE)
        if not new_file_cb(priv, data):
            return

        while True:
            data = self.read_file_data(READ_SIZE)
            if data is None:
                end_file_cb(priv)
                break
            elif isinstance(data, str):
                if not end_file_cb(priv):
                    break
                if not new_file_cb(priv, data):
                    break
            else:
                if not data_cb(priv, data):
                    break

    def mapnames(self):
        maps = ""
        for gmap in self.maps:
            maps += f" {gmap.name}\n"
        return maps

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
        maps = self.mapnames()
        return f"Workshop ID: {self.workshop_id}\n" \
               f"URL: {self.get_url()}\n" \
               f"Size: {human_readable_size(self.size)}\n" \
               f"Last Updated Time: {time.asctime(time.localtime(self.filetime))}\n" \
               f"Version: {self.version}\nSteam ID?: {self.steamid}\n" \
               f"Timestamp: {timestamp}\nName: {self.name}\n" \
               f"Author: {self.author}\nType: {self.type}\n" \
               f"Tags: {tags}\nDescription: {self.description}\n" \
               f"Addon Version (unused?): {self.addon_ver}\n" \
               f"Files:\n{files}\nMaps:\n{maps}"

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

    def read_all_data(self, new_file_cb, data_cb, end_file_cb, priv):
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
            print(path)
        else:
            workshop_id = int(path.parent.name)
            if len(do_only) == 0 or workshop_id in do_only:
                gmas.append((workshop_id, path))

    return gmas

@dataclass
class DumpFileState():
    path : pathlib.Path
    file : io.BufferedWriter | None

    def __init__(self, path : pathlib.PurePath):
        self.path = path
        self.file = None

def dump_new_file_cb(priv, name):
    extract_path = pathlib.Path(priv.path.parent.name, pathlib.Path(name))
    extract_path.parent.mkdir(parents=True, exist_ok=True)
    priv.file = extract_path.open('wb')

    return True

def dump_data_cb(priv, data):
    priv.file.write(data)

    return True

def dump_end_file_cb(priv):
    priv.file.close()

    return True

def get_gma_infos(path, do_list=False, do_dump=False, do_only=[], sort_list=[]):
    # ugh big ugly do everything function

    gma_paths = _get_gma_infos(path, do_only)
    gmas = []

    for path in gma_paths:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        gma = GMAFile(path[1], compressed)

        if do_dump:
            priv = DumpFileState(path[1])
            gma.read_all_data(dump_new_file_cb, dump_data_cb, dump_end_file_cb, priv)

        gma.close()

        gmas.append(gma)

    for sort in sort_list:
        gmas = sorted(gmas, key=sort[1])

    for gma in gmas:
        if do_list:
            print(f"{gma.workshop_id} {gma.name} {human_readable_size(gma.size)}")
            maps = gma.mapnames()
            if len(maps) > 0:
                print(f"Maps:\n{maps}")
        else:
            print(gma)

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
            depotdata = parse_acf_file(acfpath)
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

def write_cache(steampath : pathlib.PurePath, depot : SteamDepot):
    path, outname = get_cache_path(steampath, depot)

    #print(f"Writing cache for {path} to {outname}.")
    with open(outname, 'w') as cachefile:
        for file in depot.files.keys():
            hexstr = ""
            for b in depot.files[file].digest:
                hexstr += f"{b:02X}"
            cachefile.write(f"{depot.files[file].size} {hexstr} {file}\n")

def read_cache(steampath : pathlib.PurePath, depot : SteamDepot):
    filelist : FileList_T = {}

    path, outname = get_cache_path(steampath, depot)

    try:
        with open(outname, 'r') as cachefile:
            #print(f"Reading cache for {path} from {outname}.")
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
    naked_files = read_cache(steampath, depot)
    if naked_files is None:
        naked_files = gather_files(depot.path)
        depot.set_files(naked_files)
        write_cache(steampath, depot)
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
    depot_files = read_cache(steampath, depot)
    if depot_files is None:
        priv = HashFileState()
        depot.source.read_all_data(hash_new_file_cb, hash_data_cb, hash_end_file_cb, priv)
        depot.source.close()
        depot.set_files(priv.hashes)
        write_cache(steampath, depot)
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
    print(f"Hashed {depot.path}", end='')
    if cached:
        print(" (cached)")
    else:
        print()
    sem.release()

def collisions_scan(steampath : pathlib.PurePath, do_only=[], num_threads=1):
    print("Gathering mounted files...")
    depots = get_depots(steampath)

    print("Gathering addon files...")
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

    print("Hashing files...")
    sem = threading.Semaphore(num_threads)
    threads = []
    for depot in depots:
        sem.acquire()
        threads.append(threading.Thread(target=hash_depot, args=(sem, steampath, depot)))
        threads[-1].start()
    # wait for the rest to finish
    for i in range(num_threads):
        sem.acquire()

    print("Finding collisions...")
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
          f"       {app} [--steampath[=]<path to steam> | --collisions-scan]")
    print("\nSort criterias:\n")
    for sort in GMAFile.SORTS.keys():
        print(f"{sort} : {GMAFile.SORTS[sort][0]}")

if __name__ == '__main__':
    argv = sys.argv[1:]
    do_usage = False
    do_collisions = False
    do_list = False
    do_dump = False
    do_only = []
    sort_list = []
    path = pathlib.Path.home().joinpath(DEFAULT_STEAM_PATH)
    threads = 1

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
            elif arg.startswith('steampath='):
                path = pathlib.PurePath(arg[10:])
            elif len(argv) > 1 and arg == 'steampath':
                path = pathlib.PurePath(argv[1])
                argv = argv[1:]
            elif arg.startswith('threads='):
                threads = int(arg[8:])
            elif len(argv) > 1 and arg == 'threads':
                threads = int(argv[1])
                argv = argv[1:]
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
        get_gma_infos(path, do_list, do_dump, do_only, sort_list)
