#!/usr/bin/env python

import subprocess
import time
import array
import itertools
import copy

symbols='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

orig_graphline = array.array('u', itertools.repeat(' ', 100))
graphfree = array.array('u', itertools.repeat('/', 100))

def scale(num):
  mul = 1 

  while num * mul < 50:
    mul *= 2

  return mul

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

  maxcpu = len(cores)
  totalpercent /= maxcpu
  for item in cores:
      cores[item] /= maxcpu

  order = sorted(cores, key=lambda x: cores[x])

  graphline = copy.copy(orig_graphline)
  diff = 0
  for item in range(max(order)):
    mul = scale(totalpercent)
    diff += int(cores[order[item]] * mul)
    graphline[diff] = symbols[order[item]]

  print(graphline[:diff+1].tounicode(), end='')
  print("{}| {percent}%".format(graphfree[:100-(diff + 1)].tounicode(), percent=100/mul));

  time.sleep(1 - (time.clock_gettime(time.CLOCK_MONOTONIC_RAW) - start))
