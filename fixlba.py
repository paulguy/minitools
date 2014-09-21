#!/usr/bin/python3

import sys
import os
import struct


def bswap(val):
  if sys.byteorder == "little":
    return ((val & 0x000000ff) << 24) | \
           ((val & 0x0000ff00) <<  8) | \
           ((val & 0x00ff0000) >>  8) | \
           ((val & 0xff000000) >> 24)
  else: #this might be required, don't have a bigendian platform to test on
    return ((val & 0x000000ff) >> 24) | \
           ((val & 0x0000ff00) >>  8) | \
           ((val & 0x00ff0000) <<  8) | \
           ((val & 0xff000000) << 24)


def readByte(infile):
  return struct.unpack("B", infile.read(1))[0]


def readIntLE(infile):
  return struct.unpack("<I", infile.read(4))[0]


def readIntBE(infile):
  return struct.unpack(">I", infile.read(4))[0]


def writeByte(outfile, val):
  outfile.write(struct.pack("B", val))


def writeIntLE(outfile, val):
  outfile.write(struct.pack("<I", val))


def writeIntBE(outfile, val):
  outfile.write(struct.pack(">I", val))                


def addValInFileLE(outfile, loc, val):
  outfile.seek(loc)
  temp = readIntLE(outfile) + val
  outfile.seek(loc)
  writeIntLE(outfile, temp)

  return temp


def addValInFileBE(outfile, loc, val):
  outfile.seek(loc)
  temp = readIntBE(outfile) + val
  outfile.seek(loc)
  writeIntBE(outfile, temp)

  return temp


def fixPathTableLE(file, loc, count, lba):
  file.seek(loc)
  for i in range(count):
    pathent = list(struct.unpack("<BBIH", file.read(8)))
    if pathent[0] == 0:
      continue
    pathent[2] += lba
    file.seek(-8, os.SEEK_CUR)
    file.write(struct.pack("<BBIH", pathent[0], pathent[1], pathent[2], pathent[3]))
    file.seek(pathent[0] + (pathent[0] % 2)) # pad out to even size


def fixPathTableBE(file, loc, count, lba):
  file.seek(loc)
  for i in range(count):
    pathent = list(struct.unpack(">BBIH", file.read(8)))
    if pathent[0] == 0:
      continue
    pathent[2] += lba
    file.seek(-8, os.SEEK_CUR)
    file.write(struct.pack(">BBIH", pathent[0], pathent[1], pathent[2], pathent[3]))
    file.seek(pathent[0] + (pathent[0] % 2)) # pad out to even size


def fixDirectories(file, loc, lba): #this function should be recursive
  curloc = loc
  while True:
    file.seek(curloc)
    dirent = list(struct.unpack("=BBIIIIBBBBBBBBBBHHB", file.read(33)))
    print(str(dirent))

    if dirent[0] == 0:
      if curloc % 2048 == 0: #we're at the start of a blank sector, so this
                             #should indicate the end of the directory list...
        break;
      curloc = ((curloc // 2048) + 1) * 2048 #next sector
      continue

    print(hex(dirent[2]), hex(dirent[3]))

    #swap architecture oppposite values so we can work with them
    if sys.byteorder == "big":
      dirent[2] = bswap(dirent[2])
    else:
      dirent[3] = bswap(dirent[3])

    print(hex(dirent[2]), hex(dirent[3]))    

    if dirent[2] == 0:
      newloc = dirent[3]
    else:
      newloc = dirent[2]

    if dirent[2] < lba:
      if dirent[2] > 0:
        print("WARNING: New LBA would be negative, skipping!")
    else:
      dirent[2] += lba

    if dirent[3] < lba:
      if dirent[3] > 0:
        print("WARNING: New LBA would be negative, skipping!")
    else:
      dirent[3] += lba

    print(hex(dirent[2]), hex(dirent[3]))    

    #swap them back
    if sys.byteorder == "big":
      dirent[2] = bswap(dirent[2])
    else:
      dirent[3] = bswap(dirent[3])

    print(hex(dirent[2]), hex(dirent[3]))    

    file.seek(curloc + 2)

    print(str(dirent))
    file.write(struct.pack("=II", dirent[2], dirent[3]))

    if dirent[13] & 0x2 != 0: #check for directory flag
      if dirent[0] > 34: #don't recurse over blank entries (., ..)
        fixDirectories(file, newloc, lba) #recurse over tree (ugly but should work)

    curloc += dirent[0]
    

def verifyISO(infile):
  infile.seek(32768)
  voldesc = infile.read(7)
  if voldesc[1:] != b"CD001\x01":
    print("ERROR: Not a valid ISO volume descriptor!")
    return False
  if voldesc[0] != 1:
    print("ERROR: Not supported reading other volume descriptor types as first volume descriptor!  TODO")
    return False

  return True


def fixLBA(outfile, lba):
  print("Header...")
  outfile.seek(32768 + 132)
  pathtblsize = readIntLE(outfile)
  lpathtbl = addValInFileLE(outfile, 32768 + 140, lba) * 2048 #little endian path table
  bpathtbl = addValInFileBE(outfile, 32768 + 148, lba) * 2048 #big endian path table
  rootdir = addValInFileLE(outfile, 32768 + 156 + 2, lba) * 2048 #little endian root dir extent
  addValInFileBE(outfile, 32768 + 156 + 6, lba) #big endian root dir extent
  
  print("Path Tables (LE)...")
  fixPathTableLE(outfile, lpathtbl, pathtblsize, lba)

  print("Path Tables (BE)...")
  fixPathTableBE(outfile, bpathtbl, pathtblsize, lba)

  print("Directories...")
  fixDirectories(outfile, rootdir, lba)

  return True


if len(sys.argv) < 3:
  print("USAGE: " + sys.argv[0] + " <filename> <LBA change>")
  exit()

lbachg = int(sys.argv[2])

inf = open(sys.argv[1], "rb+")
if verifyISO(inf) == False:
  print("ERROR: " + sys.argv[1] + " doesn't appear to be a valid ISO file!")
  inf.close()
  exit()

fixLBA(inf, lbachg)
inf.close()
