import subprocess
import time

letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ'

while True:
  start = time.clock_gettime(time.CLOCK_MONOTONIC_RAW)
  psproc = subprocess.run(("ps", "--no-headers", "-A", "-L", "-o", "psr,pcpu"),
                          stdout=subprocess.PIPE)
  lines = psproc.stdout.splitlines()

  cores = dict()

  totalpercent = 0.0
  for line in lines:
    items = line.split(b' ')

    core = -1
    percent = -1.0
    for item in items:
      if item != b'':
        if core < 0:
          core = int(item)
        else:
          percent = float(item)
          totalpercent += percent
          break

    if core not in cores:
      cores[core] = 0.0
    cores[core] += percent

  order = sorted(cores, key=lambda x: cores[x])
  for item in range(max(order) + 1):
    diff = 0
    if item in order:
      if totalpercent <= 1.0:
        diff = round(cores[order[item]] * 100)
      elif totalpercent <= 10.0:
        diff = round(cores[order[item]] * 10)
      else:
        diff = round(cores[order[item]])

    if order[item] < 10:
      print("{core:>{space}}".format(core=order[item], space=diff), end='')
    else:
      print("{core:>{space}}".format(core=letters[order[item] - 10], space=diff), end='')

  if totalpercent <= 1.0:
    print("{ends:>{space}}".format(ends='| 1%', space=round(1.0 - totalpercent)));
  elif totalpercent <= 10.0:
    print("{ends:>{space}}".format(ends='| 10%', space=round(10.0 - totalpercent)));
  else:
    print("{ends:>{space}}".format(ends='| 100%', space=round(100.0 - totalpercent)));

  time.sleep(1 - (time.clock_gettime(time.CLOCK_MONOTONIC_RAW) - start))
