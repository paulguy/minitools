import PaletteCore


class GPLColor(PaletteCore.Color):
  defaultColorName = "Untitled"

  def fromColor(color):
    gplc = GPLColor()
    gplc.r = color.r
    gplc.g = color.g
    gplc.b = color.b
    return gplc

  def __init__(self, line = None):
    if line == None:
      super().__init__()
      self.name = GPLColor.defaultColorName
    else:
      nums = line.split()
      if len(nums) != 4:
        raise Exception("Malformed Palette Entry")
      super().__init__(int(nums[0]), int(nums[1]), int(nums[2]))
      self.name = nums[3]

  def __str__(self):
    return "{:d} {:d} {:d} {:s}".format(self.r, self.g, self.b, self.name)
    
    
class GPLPalette(PaletteCore.Palette):
  header = "GIMP Palette"
  nameKey = "Name: "
  columnsKey = "Columns: "
  defaultName = "Untitled"
  defaultColumns = 16

  def __init__(self, name = defaultName, columns = defaultColumns):
    super().__init__()
    self.name = name
    self.columns = columns
    self.i = 0
    self.curcomment = 0
    self.comments = list()
    self.lines = 0

  def add_entry(self, color):
    if type(color) is not GPLColor:
      raise TypeError
    super().add_entry(color)

  def add_comment(self, line, comment):
    if type(line) is not int and type(comment) is not str:
      raise TypeError
    self.comments.append((line, comment))

  def add_line(self, line):
    if len(line) > 0 and line[-1] == '\n': #remove newlines if present
      line = line[:-1]
    #print("\"{:s}\"".format(line))

    if self.lines == 0:
      if line == GPLPalette.header:
        self.lines = 1
        return
      else:
        raise Exception("Header Missing")

    if len(line) == 0: #ignore blank lines
      pass
    elif line[0] == '#': #comment
      self.add_comment(len(self.palette), line[1:])
    elif line[:len(GPLPalette.nameKey)] == GPLPalette.nameKey:
      self.name = line[len(GPLPalette.nameKey):]
    elif line[:len(GPLPalette.columnsKey)] == GPLPalette.columnsKey:
      self.columns = int(line[len(GPLPalette.columnsKey):])
    else:
      self.add_entry(GPLColor(line))

    self.lines += 1

  def __iter__(self):
    self.i = -1  #probably not correct, but if iteration is interrupted, reset
    self.curcomment = 0
    return self

  def __next__(self):
    if self.i == -1:
      self.i = 0
      return GPLPalette.header + '\n' + \
             GPLPalette.nameKey + self.name + '\n' + \
             GPLPalette.columnsKey + str(self.columns)
    if self.i == len(self.palette):
      if self.curcomment < len(self.comments):  #output the last comments
        tc = self.curcomment
        self.curcomment += 1
        return "#{:s}".format(self.comments[tc][1])
      self.i = -1
      self.curcomment = 0
      raise StopIteration
    if self.curcomment < len(self.comments) and self.comments[self.curcomment][0] == self.i:
      tc = self.curcomment
      self.curcomment += 1
      return "#{:s}".format(self.comments[tc][1])
    ti = self.i
    self.i += 1
    return str(self.palette[ti])
