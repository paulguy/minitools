#!/usr/bin/python3.4

import sys
import os
import shutil
from enum import Enum, unique


def outFileName(infilename, ext="iso"):
  try:
    dotindex = infilename.rindex(".")
    if dotindex == 0:
      outfilename = infilename + "." + ext
    else:
      outfilename = infilename[:dotindex] + "." + ext
  except ValueError:
    outfilename = infilename + "." + ext

  return outfilename


@unique
class GDITrackType(Enum):
  audio = 0
  data = 4


def readGDI(gdifile):
  tracks = list()
  tracksfound = list()

  thistrack = 1

  line = gdifile.readline()
  if len(line) == 0:
    return False
  ntracks = int(line[:-1])
  if ntracks < 1 or ntracks > 99:
    print("WARNING: GDI file claims track number is less than 1 or greater than 99!")

  while True:
    line = gdifile.readline()
    if len(line) == 0:
      break

    track = line[:-1].split()
    tracknum = int(track[0])
    if tracknum < 1 or tracknum > 99:
      print("WARNING: Track claims to be less than 1 or greater than 99!")
    if tracknum > ntracks:
      print("WARNING: Track claims to be a higher track number than specified by GDI file.")
    if tracknum < thistrack:
      print("WARNING: Track numbering isn't ascending!")
    if tracknum > thistrack:
      print("WARNING: Track numbering skips a track!")
    if tracknum in tracksfound:
      print("WARNING: Repeat track number!")

    tracks.append({'num': tracknum,
                   'blkpos': int(track[1]),
                   'type': GDITrackType(int(track[2])),
                   'blksize': int(track[3]),
                   'file': track[4],
                   'unknown': int(track[5])})

    thistrack = tracknum + 1

  if thistrack == 1: #we didn't find any tracks
    return False
  return tracks


def sortTracks(tracks):
  return sorted(tracks, key=lambda x: x['num'])


def monotonicTracks(tracks):
  curtrack = 1

  for track in tracks:
    if track['num'] != curtrack:
      return False
    curtrack += 1

  return True


def ascendingTrackBlocks(tracks):
  for track in enumerate(tracks[:-1]):
    if tracks[track[0]+1]['blkpos'] <= tracks[track[0]]['blkpos']:
      return False

  return True


def trimTracks(tracks, count, fixlba=True):
  if count > 0:
    newtracks = tracks[count:]
    startlba = tracks[count]['blkpos']
    for track in newtracks:
      track['num'] -= count
      if fixlba:
        track['blkpos'] -= startlba
    
    return newtracks
  if count < 0:
    return tracks[:-count]

  return tracks #if 0 do nothing


def getTrackSizes(tracks):
  tracksizes = list()
  ntracks = len(tracks)
  
  #we can't determine the size of this track based on the track table so
  #exclude it
  for track in enumerate(tracks[:-1]):
    tracksizes.append(0)
    tracksizes[track[0]]= (tracks[track[0]+1]['blkpos'] - track[1]['blkpos'])\
                          * 2048
    continue #try to treat all tracks equally
    
    if track[1]['type'] == GDITrackType.audio:
      tracksizes[track[0]]= (tracks[track[0]+1]['blkpos'] - track[1]['blkpos'])\
                            * 2352
      #pretty sure audio tracks have no subchannel data
    if track[1]['type'] == GDITrackType.data:
      tracksizes[track[0]]= (tracks[track[0]+1]['blkpos'] - track[1]['blkpos'])\
                            * 2048
      #also reasonably sure data tracks are almost always 2048 block sectors, at
      #least in this case

  tracksizes.append(-1)
  return tracksizes


def getTrackPositions(tracksize):
  trackpos = list()
  curtrackpos = 0

  for size in tracksize:
    trackpos.append(curtrackpos)
    curtrackpos += size

  return trackpos


def dcbin2iso(inf, outf):
  while True:
    seeked = inf.seek(16, os.SEEK_CUR)
    if seeked < 16:
      if seeked > 0:
        print("WARNING: Incomplete seek: Seeked " + seeked + " bytes.")
      break

    sector = inf.read(2048)
    if len(sector) < 2048:
      if len(sector) > 0:
        print("WARNING: Incomplete read: Read " + len(sector) + " bytes.")
      break

    seeked = inf.seek(288, os.SEEK_CUR)
    if seeked < 288:
      if seeked > 0:
        print("WARNING: Incomplete seek: Seeked " + seeked + " bytes.")
      break

    outf.write(sector)


if len(sys.argv) < 2:
  print("No file name given.")
  exit()

outname = outFileName(sys.argv[1])

inf = open(sys.argv[1], "r")
gditbl = readGDI(inf)
inf.close()
gditbl = sortTracks(gditbl)
if not monotonicTracks(gditbl):
  print("ERROR: Tracks must be ascending with none skipped.")
  exit()
if not ascendingTrackBlocks(gditbl):
  print("ERROR: Track offsets must be ascending.")
  exit()
startlba = gditbl[2]['blkpos']
gditbl = trimTracks(gditbl, 2)

tracksize = getTrackSizes(gditbl)
trackpos = getTrackPositions(tracksize)

outf = open(outname, "wb")

for track in gditbl:
  print(str(track['num']) + ": " + track['file'] + " " + str(track['blksize']) + " " + \
        str(track['blkpos']) + " " + track['type'].name + " " + \
        str(trackpos[track['num']-1]) + " " + str(tracksize[track['num']-1]) + \
        "... ")
  
  outf.seek(trackpos[track['num']-1])
  if track['type'] == GDITrackType.audio: # just copy the data straight over
    if track['num'] == 1: #first (third) track must be data
      print("ERROR: Initial data track not found!")
      break      
    continue #don't bother writing audio data, we don't need it
    inf = open(track['file'], "rb")
    shutil.copyfileobj(inf, outf, length=tracksize[track['num']-1])
    inf.close()
  if track['type'] == GDITrackType.data:
    if track['blksize'] == 2352: # need to strip subchannel
      inf = open(track['file'], "rb")
      dcbin2iso(inf, outf)
      inf.close()
    elif track['blksize'] == 2048: # just copy it
      inf = open(track['file'], "rb")
      shutil.copyfileobj(inf, outf, length=tracksize[track['num']-1])
      inf.close()
    else:
      print("ERROR: Unsupported block size.")
      exit()

print("Start LBA is: " + str(-startlba))
inf.close()
