#!/usr/bin/env python3

import sys
import io
import struct
import pathlib
import array
import itertools
from dataclasses import dataclass
from typing import Optional

MAGIC_SUM_VALUE = 0xB1B0AFBA

TABLE_HDR = struct.Struct(">IHHHH")
TABLE_ENTRY = struct.Struct(">4sIII")
NAME_HDR = struct.Struct(">HHH")
NAME_RECORD = struct.Struct(">HHHHHH")
HEAD_HDR = struct.Struct(">IIIIHHQQHHHHHHhhh")

def calc_checksum(data : array.array):
    data_array = array.array('I', data.tobytes())
    data_array.byteswap()
    checksum = sum(data_array)
    checksum %= 2 ** 32
    return checksum

def unpack_file(infile : io.BufferedReader,
                structure : struct.Struct) -> tuple:
    return structure.unpack(infile.read(structure.size))

def unpack_buf(data : array.array,
               start : int,
               structure : struct.Struct) -> tuple:
    return structure.unpack(data.tobytes()[start:start + structure.size])

def pad(data : array.array):
    # pad to 4 bytes
    if len(data) % 4 > 0:
        data.extend(array.array('B', itertools.repeat(0, 4 - (len(data) % 4))))

def print_hex2(data : bytes):
    for byte in data:
        print(f"{byte:02X} ", end='')
    print()

def print_hex8(data : bytes):
    for byte in data:
        print(f"{byte:08X} ", end='')
    print()

@dataclass
class TableEntry:
    tag : bytes
    checksum : int
    offset : int
    length : int
    data : Optional[array.array] = None

    def update_checksum(self):
        self.checksum = calc_checksum(self.data)

    def get_entry(self):
        return TABLE_ENTRY.pack(self.tag, self.checksum, self.offset, self.length)

@dataclass
class TTFFile:
    scaler_type : int
    search : int
    entry : int
    shift : int
    tables : list[TableEntry]

    def find_table(self, tag : bytes) -> Optional[TableEntry]:
        for item in self.tables:
            if item.tag == tag:
                return item

        return None

    def remove_table(self, tag : bytes):
        to_remove = self.find_table(tag)
        self.tables.remove(to_remove)

    def get_header(self):
        return TABLE_HDR.pack(self.scaler_type, len(self.tables), self.search, self.entry, self.shift)

    def get_table_order(self) -> list[TableEntry]:
        return sorted(self.tables, key=lambda x: x.offset)

    def write_file(self, destfile : pathlib.Path):
        # make sure the head checksum is up to date in case it's been changed
        head_table = self.find_table(b'head')
        version, fontVersion, orig_checksum, magic, flags, unitsPerEm, \
            created, modified, xmin, ymin, xmax, ymax, macstyle, \
            lowestRecPPEM, directionHint, indexToLocFormat, \
            glyphDataFormat = unpack_buf(head_table.data, 0, HEAD_HDR)
        #print(f"{version:08x} {fontVersion:08x} {orig_checksum:08x} {magic:08x} {flags:04x} {unitsPerEm} "
        #      f"{created} {modified} {xmin} {ymin} {xmax} {ymax} {macstyle} "
        #      f"{lowestRecPPEM} {directionHint} {indexToLocFormat} "
        #      f"{glyphDataFormat}")
        head_table.data[:HEAD_HDR.size] = array.array('B', HEAD_HDR.pack(version, fontVersion, 0, \
            magic, flags, unitsPerEm, created, modified, xmin, ymin, xmax, ymax, \
            macstyle, lowestRecPPEM, directionHint, indexToLocFormat, \
            glyphDataFormat))
        head_table.update_checksum()
 
        # set new values in case things have changed
        for i in range(1, 14):
            if i == 13:
                # dunno just set the max value?  probably won't happen
                self.entry = 12
                self.search = 65535
                self.shift = len(self.tables) * 16 - self.search
            else:
                entry = 2 ** i
                if entry > len(self.tables) - entry:
                    self.search = entry * 16
                    self.entry = i
                    self.shift = len(self.tables) * 16 - self.search
                    break

        with destfile.open('wb+') as outfile:
            outfile.write(self.get_header())

            for table in self.tables:
                outfile.write(table.get_entry())

            sorted_tables = self.get_table_order()
            for table in sorted_tables:
                outfile.write(table.data)

            outfile.seek(0)
            data = array.array('I', outfile.read())
            data.byteswap()
            checksum = sum(data)
            checksum %= 2 ** 32
            checksum = MAGIC_SUM_VALUE - checksum
            if checksum < 0:
                checksum += 2 ** 32
            outfile.seek(head_table.offset + 8)
            outfile.write(struct.pack(">I", checksum))

def read_tables(infile : io.BufferedReader,
                count : int) -> list[TableEntry]:
    tables = []
    for i in range(count):
        tag, checksum, offset, length = unpack_file(infile, TABLE_ENTRY)
        tables.append(TableEntry(tag, checksum, offset, length))

    # read data in, including any padding
    sorted_tables = sorted(tables, key=lambda x: x.offset)
    for i, table in enumerate(sorted_tables[:-1]):
        infile.seek(table.offset)
        table.data = array.array('B', infile.read(sorted_tables[i+1].offset - table.offset))
    # and the rest of the file
    infile.seek(sorted_tables[-1].offset)
    sorted_tables[-1].data = array.array('B', infile.read())
       
    return tables

def read_file(srcname : pathlib.Path) -> TTFFile:
    with srcname.open('rb') as infile:
        scaler_type, table_count, search, entry, shift = unpack_file(infile, TABLE_HDR)
        tables = read_tables(infile, table_count)

    return TTFFile(scaler_type, search, entry, shift, tables)

def get_name_str(name : int):
    match name:
        case 0:
            return "Copyright"
        case 1:
            return "Font Family"
        case 2:
            return "Font Subfamily"
        case 3:
            return "Unique Subfamily Identification"
        case 4:
            return "Full Name"
        case 5:
            return "Version"
        case 6:
            return "PostScript Name"
        case 7:
            return "Trademark"
        case 8:
            return "Manufacturer"
        case 9:
            return "Designer"
        case 10:
            return "Description"
        case 11:
            return "URL"
        case 12:
            return "Designer URL"
        case 13:
            return "License"
        case 14:
            return "License URL"
        case 16:
            return "Preferred Family"
        case 17:
            return "Preferred Subfamily"
        case 18:
            return "Compatible Full"
        case 19:
            return "Sample Text"
        case 25:
            return "Variations PostScript Name Prefix"

    return "Unknown"

# i dunno which of these are needed
CHANGE_VALUES = {
    "Font Family",
    "Full Name",
    "PostScript Name"
}

def fix_name_table(name_table : TableEntry,
                   new_name : Optional[str] = None,
                   new_subfamily : Optional[str] = None):
    new_header = array.array('B')
    new_strings = array.array('B')

    name_format, name_count, string_offset = unpack_buf(name_table.data, 0, NAME_HDR)
    new_header.extend(NAME_HDR.pack(name_format, name_count, string_offset))

    for i in range(name_count):
        platform, platform_specific, language, name, length, offset = \
            unpack_buf(name_table.data,
                       NAME_HDR.size + (NAME_RECORD.size * i),
                       NAME_RECORD)
        #print(f"{platform} {platform_specific} {language} {name} {length} {offset}")

        # this is awful but probably fine for modern...
        platform_str = "Unknown"
        encoding = 'utf_16_be'
        if platform == 0:
            platform_str = "Unicode"
        elif platform == 1:
            platform_str = "Macintosh"
            encoding = "mac_roman"
        elif platform == 3:
            platform_str = "Microsoft"
            encoding = 'utf_16_be'
        name_str = get_name_str(name)
        value = name_table.data[string_offset+offset:string_offset+offset+length]
        if new_name is None:
            print(f"{name_str} ({platform_str}): {value.tobytes().decode(encoding)}")
        elif new_subfamily is not None and name_str == "Font Subfamily":
            new_subfamily_bytes = new_subfamily.encode(encoding)
            new_header.extend(NAME_RECORD.pack(platform, platform_specific, language, name, len(new_subfamily_bytes), len(new_strings)))
            new_strings.extend(new_subfamily_bytes)
        #elif new_subfamily is not None and name_str == "Full Name":
        #    new_fullname_bytes = f"{new_name} {new_subfamily}".encode(encoding)
        #    new_header.extend(NAME_RECORD.pack(platform, platform_specific, language, name, len(new_fullname_bytes), len(new_strings)))
        #    new_strings.extend(new_fullname_bytes)
        elif new_name is not None and name_str in CHANGE_VALUES:
            new_name_bytes = new_name.encode(encoding)
            new_header.extend(NAME_RECORD.pack(platform, platform_specific, language, name, len(new_name_bytes), len(new_strings)))
            new_strings.extend(new_name_bytes)
        else:
            new_header.extend(NAME_RECORD.pack(platform, platform_specific, language, name, length, len(new_strings)))
            new_strings.extend(value)

    if new_name is not None:
        new_header.extend(new_strings)
        pad(new_header)
        name_table.data = new_header
        name_table.update_checksum()

def main():
    srcname = pathlib.Path(sys.argv[1])
    destname = srcname.with_name(f"{srcname.stem}_renamed{srcname.suffix}")

    ttf = read_file(srcname)

    # remove digital signature
    #ttf.remove_table(b'DSIG')
 
    name_table = ttf.find_table(b'name')
    if len(sys.argv) == 3:
        fix_name_table(name_table, sys.argv[2])
    elif len(sys.argv) > 3:
        fix_name_table(name_table, sys.argv[2], sys.argv[3])
    else:
        fix_name_table(name_table)

    #ttf.fix_head_checksum()

    if len(sys.argv) > 2:
        ttf.write_file(destname)

if __name__ == '__main__':
    main()
