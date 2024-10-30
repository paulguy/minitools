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

class VPKFile(ValveFile):
    # much from <https://developer.valvesoftware.com/wiki/VPK_(file_format)>

    # this'll be super basic and only read the directory tree

    VPK_MAGIC = 0x34 | (0x12 << 8) | (0xAA << 16) | (0x55 << 24)

    VPK_MAGIC_HDR = struct.Struct("<II")
    VPK_1_HDR = struct.Struct("<I")
    VPK_2_HDR = struct.Struct("<IIIII")
    VPK_ENTRY = struct.Struct("<IHHIIH")

    def __init__(self, path : pathlib.PurePath):
        # no compression here but the in-place string reading from a binary file is still useful
        super().__init__(path)

        self.files = set()

        magic, version = self.VPK_MAGIC_HDR.unpack(self.read(self.VPK_MAGIC_HDR.size))

        if magic != self.VPK_MAGIC:
            # probably a data file, not a directory
            self.files = None
            return

        if version == 1:
            treesize = self.VPK_1_HDR.unpack(self.read(self.VPK_1_HDR.size))
        elif version == 2:
            # don't care about the signatures
            treesize, _, _, _, _ = self.VPK_2_HDR.unpack(self.read(self.VPK_2_HDR.size))
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
                    # just ignoring everything
                    _, preloadBytes, archiveIndex, _, _, _ = self.VPK_ENTRY.unpack(self.read(self.VPK_ENTRY.size))
                    # not clear on the docs here
                    if preloadBytes > 0:
                        self.seek(preloadBytes, os.SEEK_CUR)
                    self.files.add(f"{path}{filename}{extension}")

    def get_files_list(self):
        return self.files

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

def get_gma_infos(path, do_list=False, do_dump=False, do_only=[], sort_list=[]):
    gma_paths = _get_gma_infos(path, do_only)
    gmas = []

    for path in gma_paths:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        gma = GMAFile(path[1], compressed)

        if do_dump:
            curfile = None
            while True:
                data = gma.read_file_data(READ_SIZE)
                if data is None:
                    if curfile is not None:
                        curfile.close()
                    break
                elif isinstance(data, str):
                    if curfile is not None:
                        curfile.close()
                    extract_path = pathlib.Path(path[1].parent.name, pathlib.Path(data))
                    extract_path.parent.mkdir(parents=True, exist_ok=True)
                    curfile = extract_path.open('wb')
                else:
                    curfile.write(data)

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
                 mounted : bool,
                 path : pathlib.PurePath):
        self.depot_name = depot_name
        self.game_id = game_id
        self.game_name = game_name
        self.mounted = mounted
        # not 100% sure on this one
        self.path = path
        self.files = []

    def __hash__(self):
        return hash(self.path)

    def __str__(self):
        return f"Depot: {self.depot_name}  ID: {self.game_id}  Name: {self.game_name}  Path: {self.path}  Files: {len(self.files)}"

    def set_files(self, files : list[str] | set[str]):
        self.files = set(files)

    def get_files(self) -> set[str]:
        return self.files

def get_mounted_depots(steampath : pathlib.PurePath):
    depotspath = pathlib.PurePath(steampath, GARRYSMOD_PATH, DEPOTS_PATH)

    depotdata = parse_acf_file(depotspath)

    # garry's mod is probably always mounted?
    depots = [SteamDepot("garrysmod",
                         GARRYSMOD_GAMEID,
                         "Garry's Mod",
                         True,
                         pathlib.PurePath(steampath, GARRYSMOD_PATH, "garrysmod"))]

    depotdict = depotdata["gamedepotsystem"]
    for depot in depotdict.keys():
        if int(depotdict[depot]) != 0:
            depotinfo = STEAM_DEPOTS[depot]
            acfpath = pathlib.Path(steampath, "steamapps", f"appmanifest_{depotinfo[0]}.acf")
            depotdata = parse_acf_file(acfpath)
            depots.append(SteamDepot(depot,
                                     depotinfo[0],
                                     depotinfo[1],
                                     True,
                                     pathlib.PurePath(steampath, STEAM_APP_PATH, depotdata["AppState"]["installdir"], depot)))

    return depots

def gather_files(path : pathlib.PurePath):
    filelist = set()

    for dirname in UNPACKED_FILE_DIRS:
        for root, dirs, files in pathlib.Path(path, dirname).walk():
            for file in files:
                # get the relative path and join its directory parts back together
                # in the same way as other gmod paths are
                filelist.add('/'.join(pathlib.PurePath(root, file).relative_to(path).parts))

    return filelist

def list_depot(steampath : pathlib.PurePath, depot : SteamDepot):
    depot.set_files(gather_files(depot.path))

    newdepots = [depot]

    for item in pathlib.Path(depot.path).glob("*.vpk", case_sensitive=False):
        vpk = VPKFile(item)
        files = vpk.get_files_list()
        if files is None:
            continue
        newdepot = SteamDepot(depot.depot_name,
                              depot.game_id,
                              depot.game_name,
                              True,
                              pathlib.PurePath(depot.path, item))
        newdepot.set_files(files)
        newdepots.append(newdepot)

    return newdepots

def get_depots(steampath : pathlib.PurePath):
    # main garrysmod VPKs
    #filelists.update(_read_vpks("Garry's Mod", pathlib.Path(path, GARRYSMOD_PATH, "garrysmod")))

    depots = get_mounted_depots(steampath)
    newdepots = []
    for depot in depots:
        newdepots.extend(list_depot(steampath, depot))

    return newdepots

def collisions_scan(path, do_only=[]):
    print("Gathering mounted files...")
    depots = get_depots(path)

    print("Gathering addon files...")
    gmas = _get_gma_infos(path, do_only)

    for path in gmas:
        compressed = False
        if path[1].name.endswith("_legacy.bin"):
            compressed = True

        with GMAFile(path[1], compressed) as gma:
            # no dumping, so just close it right away
            gma.close()

            newdepot = SteamDepot(f"addon_{gma.workshop_id}",
                                  gma.workshop_id,
                                  gma.name,
                                  False,
                                  gma.path)
            newdepot.set_files(gma.get_file_set())
            depots.append(newdepot)

    print("Finding collisions...")
    collisions = {}
    for num, depot1 in enumerate(depots):
        for depot2 in depots[num+1:]:
            intersection = depot1.files.intersection(depot2.files)
            for item in intersection:
                if item in collisions:
                    collisions[item].add(depot1)
                    collisions[item].add(depot2)
                else:
                    collisions[item] = {depot1, depot2}

    for collision in collisions.keys():
        addon = False
        for depot in collisions[collision]:
            if not depot.mounted:
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

    # ultra simple args parsing
    while len(argv) > 0:
        if argv[0].startswith('--'):
            arg = argv[0][2:]
            if arg == 'list':
                do_list = True
            elif arg == 'sort=':
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
        collisions_scan(path, do_only)
    else:
        get_gma_infos(path, do_list, do_dump, do_only, sort_list)
