import PaletteCore

class BLColor(PaletteCore.Color):
  def fromColor(color):
    blc = BLColor()
    blc.r = color.r
    blc.g = color.g
    blc.b = color.b
    blc.a = color.a
    return blc

  def __init__(self, line = None):
    if line == None:
      super().__init__()
    else:
      nums = line.split()
      if len(nums) != 4:
        raise Exception("Malformed Palette Entry")
      super().__init__(int(nums[0]), int(nums[1]), int(nums[2]), int(nums[3]))

  def __str__(self):
    return "{:d} {:d} {:d} {:d}".format(self.r, self.g, self.b, self.a)


class BLPalette(PaletteCore.Palette):
  maxpal = 64
  
  def __init__(self):
    super().__init__()
    self.i = 0
    self.curdiv = 0
    self.divs = list()
    
  def add_entry(self, color):
    if type(color) is not BLColor:
      raise TypeError
    if len(self.palette) == BLPalette.maxpal:
      raise Exception("Too Many Colors")
    super().add_entry(color)
    
  def add_div(self, line, name):
    if type(line) is not int or type(name) is not str:
      raise TypeError
    self.divs.append((line, name))
        
  def add_line(self, line):
    if len(line) > 0 and line[-1] == '\n': #remove newlines if present
      line = line[:-1]
    #print("\"{:s}\"".format(line))
    if len(line) == 0: #ignore blank lines
      return
    if line[:4] == 'DIV:':
      self.add_div(len(self.palette), line[4:])
    else:
      self.add_entry(BLColor(line))
      
  def __iter__(self):
    self.i = 0  #probably not correct, but if iteration is interrupted, reset
    self.curdiv = 0
    return self

  def __next__(self):
    if self.i == len(self.palette):
      if self.curdiv < len(self.divs) and self.divs[self.curdiv][0] == self.i:
        tdiv = self.curdiv
        self.curdiv += 1
        return "DIV:{:s}\n".format(self.divs[tdiv][1])
      self.i = 0
      self.curdiv = 0
      raise StopIteration
    if self.curdiv < len(self.divs) and self.divs[self.curdiv][0] == self.i:
      tdiv = self.curdiv
      self.curdiv += 1
      return "DIV:{:s}\n".format(self.divs[tdiv][1])
    ti = self.i
    self.i += 1
    return str(self.palette[ti])
