class Color:
  @property
  def r(self):
    return self._r
  @r.setter
  def r(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 255:
      raise ValueError
    self._r = value

  @property
  def g(self):
    return self._g
  @g.setter
  def g(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 255:
      raise ValueError
    self._g = value

  @property
  def b(self):
    return self._b
  @b.setter
  def b(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 255:
      raise ValueError
    self._b = value

  @property
  def a(self):
    return self._a
  @a.setter
  def a(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 255:
      raise ValueError
    self._a = value
  
  def __init__(self, r=0, g=0, b=0, a=255):
    self.r = r
    self.b = b
    self.g = g
    self.a = a
    
  def __repr__(self):
    return {'r': self.r, 'g': self.g, 'b': self.b, 'a': self.a}


class Palette:
  def __init__(self):
    self.palette = list()

  def add_entry(self, color):
    if type(color).__mro__[-2] is not Color:
      raise TypeError
    self.palette.append(color)

  def del_index(self, idx):
    self.palette = self.palette[:idx] + self.palette[idx+1:]
    
  def del_value(self, color):
    self.palette.remove(color)
