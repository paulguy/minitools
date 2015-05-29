import BLSFile
import sys

bls = BLSFile.BLSFile(sys.argv[1])

def fix(brick):
  brick.x -= 0.5

def fix2(brick):
  brick.x += 0.5

print("normal bricks 1x")
for brick in bls.bricks:
  if (brick.name[:2] == "1x" and brick.name[2].isdigit() and brick.r % 2 == 0) or \
     brick.name[:3] == "1x1":
    fix(brick)
    print(".", end='')
print()

print("normal bricks 3x")
for brick in bls.bricks:
  if brick.name[1:3] == "x3" and brick.name[0].isdigit() and brick.r % 2 == 1:
    fix(brick)
    print(".", end='')
print()

print("specials")
for brick in bls.bricks:
  if (brick.name == "Castle Wall" and brick.r % 2 == 1) or \
     brick.name == "Pumpkin" or \
     brick.name == "Skull" or \
     brick.name == "Music Brick" or \
     brick.name == "Spawn Point" or \
     brick.name == "Checkpoint":
    fix(brick)
    print(".", end='')
print()

print("ramps")
for brick in bls.bricks:
  if ((brick.name == "25° Ramp 2x" or brick.name == "25° Ramp 4x" or \
       brick.name == "-25° Ramp 2x") and brick.r % 2 == 1) or \
       brick.name == "25° Ramp 1x" or brick.name == "-25° Ramp 1x" or \
       brick.name == "25° Ramp Corner" or brick.name == "-25° Ramp Corner" or \
     ((brick.name == "25° Crest 1x" or brick.name == "25° Crest End" or \
       brick.name == "45° Crest 1x" or brick.name == "45° Crest End") and \
       brick.r % 2 == 0) or \
     ((brick.name == "45° Ramp 1x" or brick.name == "-45° Ramp 1x" or \
       brick.name == "72° Ramp 1x" or brick.name == "-72° Ramp 1x" or \
       brick.name == "80° Ramp 1x" or brick.name == "-80° Ramp 1x") and \
       brick.r % 2 == 0):
    fix(brick)
    print(".", end='')
print()

print("oddities")
for brick in bls.bricks:
  if ((brick.name[:4] == "1x10" or brick.name[:4] == "1x12" or \
       brick.name[:4] == "1x16") and brick.r % 2 == 1) or \
      (brick.name == "1x4x5 Window" and brick.r % 2 == 0) or \
      (brick.name == "1x2F Print" and brick.r % 2 == 0):
    fix2(brick)
    print(".", end='')
  if (brick.name == "1x4x5 Window" and brick.r % 2 == 1) or \
     (brick.name == "1x2F Print" and brick.r % 2 == 1):
    fix(brick)
    print(".", end='')
print()

if sys.argv[1][-4:] == ".bls":
  outname = sys.argv[1][:-4] + "_fixed.bls"
else:
  outname = sys.argv[1] + "_fixed.bls"

with open(outname, "w", encoding=BLSFile.BLSFile.defencoding) as out:
  out.write(str(bls))
