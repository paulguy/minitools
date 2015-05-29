from io import TextIOWrapper

class BLSColor:
  @property
  def r(self):
    return self._r
  @r.setter
  def r(self, value):
    fvalue = float(value)
    if fvalue < 0 or fvalue > 1:
      raise ValueError
    self._r = fvalue

  @property
  def g(self):
    return self._g
  @g.setter
  def g(self, value):
    fvalue = float(value)
    if fvalue < 0 or fvalue > 1:
      raise ValueError
    self._g = fvalue

  @property
  def b(self):
    return self._b
  @b.setter
  def b(self, value):
    fvalue = float(value)
    if fvalue < 0 or fvalue > 1:
      raise ValueError
    self._b = fvalue

  @property
  def a(self):
    return self._a
  @a.setter
  def a(self, value):
    fvalue = float(value)
    if fvalue < 0 or fvalue > 1:
      raise ValueError
    self._a = fvalue
  
  def setall(self, r, g, b, a):
    self.r = r
    self.g = g
    self.b = b
    self.a = a
  
  def __init__(self, r=1.0, g=0.0, b=1.0, a=0.0, palstr=None):
    if palstr == None:
      self.setall(r, g, b, a)
    else:
      vals = palstr.split()
      if len(vals) != 4:
        raise Exception("Malformed palette string: {:s}".format(palstr))

      self.setall(vals[0], vals[1], vals[2], vals[3])

  def __str__(self):
    return "{:f} {:f} {:f} {:f}".format(self.r, self.g, self.b, self.a)


class BLSEvent:
  @property
  def enabled(self):
    return self._enabled
  @enabled.setter
  def enabled(self, value):
    if type(value) is bool:
      if value == True:
        value = 1
      else:
        value = 0
    if type(value) is not int:
      return TypeError
    if value < 0 or value > 1:
      return ValueError
    self._enabled = value

  @property
  def inevent(self):
    return self._inevent
  @inevent.setter
  def inevent(self, value):
    if type(value) is not str:
      raise TypeError
    self._inevent = value

  @property
  def delay(self):
    return self._delay
  @delay.setter
  def delay(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0:
      raise ValueError
    self._delay = value

  @property
  def target(self):
    return self._target
  @target.setter
  def target(self, value):
    if value == -1:
      value = "-1"
    if type(value) is not str:
      raise TypeError
    if value == "<NAMED BRICK>":
      value == "-1"
    self._target = value

  @property
  def targetarg(self):
    return self._targetarg
  @targetarg.setter
  def targetarg(self, value):
    if value == None:
      self._targetarg = ""
      return
    if type(value) is not str:
      raise TypeError
    self._targetarg = value

  @property
  def outevent(self):
    return self._outevent
  @outevent.setter
  def outevent(self, value):
    if type(value) is not str:
      raise TypeError
    self._outevent = value

  @property
  def outarg1(self):
    return self._outarg1
  @outarg1.setter
  def outarg1(self, value):
    if value == None:
      self._outarg1 = ""
      return
    if type(value) is not str:
      raise TypeError
    self._outarg1 = value
  
  @property
  def outarg2(self):
    return self._outarg2
  @outarg2.setter
  def outarg2(self, value):
    if value == None:
      self._outarg2 = ""
      return
    if type(value) is not str:
      raise TypeError
    self._outarg2 = value

  @property
  def outarg3(self):
    return self._outarg3
  @outarg3.setter
  def outarg3(self, value):
    if value == None:
      self._outarg3 = ""
      return
    if type(value) is not str:
      raise TypeError
    self._outarg3 = value

  @property
  def outarg4(self):
    return self._outarg4
  @outarg4.setter
  def outarg4(self, value):
    if value == None:
      self._outarg4 = ""
      return
    if type(value) is not str:
      raise TypeError
    self._outarg4 = value

  def __init__(self, enabled, inevent, delay, target, outevent, targetarg=None,\
               outarg1=None, outarg2=None, outarg3=None, outarg4=None):
    self.enabled = enabled
    self.inevent = inevent
    self.delay = delay
    self.target = target
    self.targetarg = targetarg
    self.outevent = outevent
    self.outarg1 = outarg1
    self.outarg2 = outarg2
    self.outarg3 = outarg3
    self.outarg4 = outarg4

  def __str__(self):
    return "{:d}\t{:s}\t{:d}\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}\t{:s}"\
          .format(self.enabled, self.inevent, self.delay, self.target, \
                  self.targetarg, self.outevent, self.outarg1, self.outarg2, \
                  self.outarg3, self.outarg4)

  def fromLine(line):
    parts = line.split("\t")
    if len(parts) != 10:
      raise Exception("Event line malformed: \"{:s}\"".format(line))
    return BLSEvent(int(parts[0]), parts[1], int(parts[2]), parts[3], parts[5], \
                    parts[4], parts[6], parts[7], parts[8], parts[9])


class BLSEmitter:
  @property
  def name(self):
    return self._name
  @name.setter
  def name(self, value):
    if type(value) is not str:
      raise TypeError
    self._name = value

  @property
  def d(self):
    return self._d
  @d.setter
  def d(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 5:
      raise ValueError
    self._d = value

  def __init__(self, name, direction):
    self.name = name
    self.d = direction

  def __str__(self):
    return "{:s}\" {:d}".format(self.name, self.d)

  def fromLine(line):
    name = line.split("\"")
    if len(name) != 2:
      raise Exception("Emitter line malformed: \"{:s}\"".format(line))

    return BLSEmitter(name[0], int(name[1]))


class BLSItem:
  @property
  def name(self):
    return self._name
  @name.setter
  def name(self, value):
    if type(value) is not str:
      raise TypeError
    self._name = value

  @property
  def pos(self):
    return self._pos
  @pos.setter
  def pos(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 5:
      raise ValueError
    self._pos = value

  @property
  def d(self):
    return self._d
  @d.setter
  def d(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 5:
      raise ValueError
    self._d = value

  @property
  def restime(self):
    return self._restime
  @restime.setter
  def restime(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0:
      raise ValueError
    self._restime = value

  def __init__(self, name, pos, direction, respawntime):
    self.name = name
    self.pos = pos
    self.d = direction
    self.restime = respawntime

  def __str__(self):
    return "{:s}\" {:d} {:d} {:d}".format(self.name, self.pos, self.d, \
                                          self.restime)

  def fromLine(line):
    name = line.split("\"")
    if len(name) != 2:
      raise Exception("Item line malformed: \"{:s}\"".format(line))
    parts = name[1][1:].split(" ")
    if len(parts) != 3:
      raise Exception("Item line malformed: \"{:s}\"".format(line))
    return BLSItem(name[0], int(parts[0]), int(parts[1]), int(parts[2]))


class BLSVehicle:
  @property
  def name(self):
    return self._name
  @name.setter
  def name(self, value):
    if type(value) is not str:
      raise TypeError
    self._name = value

  @property
  def recolor(self):
    return self._recolor
  @recolor.setter
  def recolor(self, value):
    if type(value) is bool:
      if value == True:
        value = 1
      else:
        value = 0
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 1:
      raise ValueError
    self._recolor = value

  def __init__(self, name, recolor=False):
    self.name = name
    self.recolor = recolor

  def __str__(self):
    return "{:s}\" {:d}".format(self.name, self.recolor)

  def fromLine(line):
    name = line.split("\"")
    if len(name) != 2:
      raise Exception("Vehicle line malformed: \"{:s}\"".format(line))
    parts = name[1][1:].split(" ")
    if len(parts) != 1:
      raise Exception("Vehicle line malformed: \"{:s}\"".format(line))
    return BLSVehicle(name[0], int(parts[0]))


class BLSBrick:
  @property
  def name(self):
    return self._name
  @name.setter
  def name(self, value):
    if type(value) is not str:
      raise TypeError
    self._name = value

  @property
  def x(self):
    return self._x
  @x.setter
  def x(self, value):
    if type(value) is not float:
      raise TypeError
    self._x = value

  @property
  def y(self):
    return self._y
  @y.setter
  def y(self, value):
    if type(value) is not float:
      raise TypeError
    self._y = value

  @property
  def z(self):
    return self._z
  @z.setter
  def z(self, value):
    if type(value) is not float:
      raise TypeError
    self._z = value

  @property
  def r(self):
    return self._r
  @r.setter
  def r(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 3:
      raise ValueError
    self._r = value

  @property
  def unknown(self):
    return self._unknown
  @unknown.setter
  def unknown(self, value):
    if type(value) is not int:
      raise TypeError
    self._unknown = value

  @property
  def color(self):
    return self._color
  @color.setter
  def color(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 63:
      raise ValueError
    self._color = value

  @property
  def printname(self):
    return self._printname
  @printname.setter
  def printname(self, value):
    if value == None:
      value = ""
    if type(value) is not str:
      raise TypeError
    self._printname = value

  @property
  def fx(self):
    return self._fx
  @fx.setter
  def fx(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 8:
      raise ValueError
    self._fx = value

  @property
  def undulo(self):
    return self._undulo
  @undulo.setter
  def undulo(self, value):
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 2: # 2 is water
      raise ValueError
    self._undulo = value

  @property
  def raycast(self):
    return self._raycast
  @raycast.setter
  def raycast(self, value):
    if type(value) is bool:
      if value == True:
        value = 1
      else:
        value = 0
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 1:
      raise ValueError
    self._raycast = value

  @property
  def collision(self):
    return self._collision
  @collision.setter
  def collision(self, value):
    if type(value) is bool:
      if value == True:
        value = 1
      else:
        value = 0
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 1:
      raise ValueError
    self._collision = value

  @property
  def render(self):
    return self._render
  @render.setter
  def render(self, value):
    if type(value) is bool:
      if value == True:
        value = 1
      else:
        value = 0
    if type(value) is not int:
      raise TypeError
    if value < 0 or value > 1:
      raise ValueError
    self._render = value

  @property
  def owner(self):
    return self._owner
  @owner.setter
  def owner(self, value):
    if value == None:
      self._owner = 0
      return
    if type(value) is not int:
      raise TypeError
    if value < -1:
      raise ValueError
    self._owner = value

  @property
  def objname(self):
    return self._objname
  @objname.setter
  def objname(self, value):
    if value == None:
      self._objname = ""
      return
    if type(value) is not str:
      raise TypeError
    self._objname = value

  @property
  def events(self):
    return self._events

  @property
  def emitter(self):
    return self._emitter
  @emitter.setter
  def emitter(self, value):
    if value == None:
      self._emitter = None
      return
    if type(value) is not BLSEmitter:
      raise TypeError
    self._emitter = value

  @property
  def light(self):
    return self._light
  @light.setter
  def light(self, value):
    if value == None:
      self._light = ""
      return
    if type(value) is not str:
      raise TypeError
    self._light = value

  @property
  def item(self):
    return self._item
  @item.setter
  def item(self, value):
    if value == None:
      self._item = None
      return
    if type(value) is not BLSItem:
      raise TypeError
    self._item = value

  @property
  def vehicle(self):
    return self._vehicle
  @vehicle.setter
  def vehicle(self, value):
    if value == None:
      self._vehicle = None
      return
    if type(value) is not BLSVehicle:
      raise TypeError
    self._vehicle = value

  @property
  def music(self):
    return self._music
  @music.setter
  def music(self, value):
    if value == None:
      self._music = ""
      return
    if type(value) is not str:
      raise TypeError
    self._music = value

  def __init__(self, name, x=0, y=0, z=0, r=0, unknown=0, color=0, \
               printname=None, fx=0, undulo=0, raycast=False, collision=False, \
               render=False, owner=-1, objectname=None, emitter=None, \
               light=None, item=None, vehicle=None, music=None):
    self.name = name
    self.x = x
    self.y = y
    self.z = z
    self.r = r
    self.unknown = unknown
    self.color = color
    self.printname = printname
    self.fx = fx
    self.undulo = undulo
    self.raycast = raycast
    self.collision = collision
    self.render = render
    self.owner = owner
    self.objname = objectname
    self._events = list() #i won't try initializing this here, use utility functions
    self.emitter = emitter
    self.item = item
    self.light = light
    self.vehicle = vehicle
    self.music = music

  def add_event(self, event):
    if type(event) is not BLSEvent:
      raise TypeError
    self._events.append(event)

  def bricktostr(name, x, y, z, r, unknown, color, printname, fx, undulo, \
                 raycast, collision, render):
    if type(name) is not str or type(x) is not float or type(y) is not float \
       or type(z) is not float or type(r) is not int or type(unknown) is not int \
       or type(color) is not int or type(printname) is not str \
       or type(fx) is not int or type(raycast) is not int \
       or type(collision) is not int or type(render) is not int:
      raise TypeError
    return "{:s}\" {:g} {:g} {:g} {:d} {:d} {:d} {:s} {:d} {:d} {:d} {:d} {:d}" \
           .format(name, x, y, z, r, unknown, color, printname, fx, undulo, raycast, \
                   collision, render)

  def ownertostr(owner):
    if type(owner) is not int:
      raise TypeError
    return "+-OWNER {:d}".format(owner)

  def objnametostr(objname):
    if type(objname) is not str:
      raise TypeError
    return "+-NTOBJECTNAME _{:s}".format(objname)

  def eventtostr(event, num):
    if type(event) is not BLSEvent:
      raise TypeError
    if type(num) is not int:
      raise TypeError
    return "+-EVENT\t{:d}\t{:s}".format(num, str(event))

  def eventstostr(events):
    ret = ""
    for event in enumerate(events):
      ret += BLSBrick.eventtostr(event[1], event[0]) + "\n"

    return ret

  def emittertostr(emitter):
    if type(emitter) is not BLSEmitter:
      raise TypeError
    return "+-EMITTER {:s}".format(str(emitter))

  def lighttostr(light):
    if type(light) is not str:
      raise TypeError
    return "+-LIGHT {:s}\" ".format(light) #space is there on purpose

  def itemtostr(item):
    if type(item) is not BLSItem:
      raise TypeError
    return "+-ITEM {:s}".format(str(item))

  def vehicletostr(vehicle):
    if type(vehicle) is not BLSVehicle:
      raise TypeError
    return "+-VEHICLE {:s}".format(str(vehicle))

  def musictostr(music):
    if type(music) is not str:
      raise TypeError
    return "+-AUDIOEMITTER {:s}\" ".format(music)

  def __str__(self):
    ret = BLSBrick.bricktostr(self.name, self.x, self.y, self.z, self.r, \
                              self.unknown, self.color, self.printname, self.fx, \
                              self.undulo, self.raycast, self.collision, \
                              self.render) + "\n"
    if self.owner > -1:
      ret += BLSBrick.ownertostr(self.owner) + "\n"
    if self.objname != "":
      ret += BLSBrick.objnametostr(self.objname) + "\n"
    if len(self.events) > 0:
      ret += BLSBrick.eventstostr(self.events)
    if self.emitter != None:
      ret += BLSBrick.emittertostr(self.emitter) + "\n"
    if self.light != "":
      ret += BLSBrick.lighttostr(self.light) + "\n"
    if self.item != None:
      ret += BLSBrick.itemtostr(self.item) + "\n"
    if self.vehicle != None:
      ret += BLSBrick.vehicletostr(self.vehicle) + "\n"
    if self.music != "":
      ret += BLSBrick.musictostr(self.music) + "\n"

    return ret

  def fromLine(line):
    name = line.split("\"")
    #print(name)
    if len(name) != 2:
      raise Exception("Brick line malformed: \"{:s}\"".format(line))
    parts = name[1][1:].split(" ")
    if len(parts) != 12:
      raise Exception("Brick line malformed: \"{:s}\"".format(line))
    #print(parts)
    return BLSBrick(name[0], float(parts[0]), float(parts[1]), float(parts[2]), \
                    int(parts[3]), int(parts[4]), int(parts[5]), parts[6], \
                    int(parts[7]), int(parts[8]), int(parts[9]), int(parts[10]), \
                    int(parts[11]))

  def fromLines(lines):
    events = list()

    #print(lines[0])
    brick = BLSBrick.fromLine(lines[0])
    for line in enumerate(lines[1:]):
      if len(line[1]) == 0 and line[0] != len(linelist) - 1:
        raise Exception("Brick block malformed:\n\"{:s}\"\n".format(lines))
      if line[1][:2] != "+-":
        raise Exception("Brick line malformed: \"{:s}\"".format(line[1]))
      try: #hopefully events are the only one that use a tab, otherwise this'll suck
        cmdpos = line[1].index("\t")
      except:
        cmdpos = line[1].index(" ")
      cmd = line[1][2:cmdpos]
      args = line[1][cmdpos+1:]
      #print(repr(cmd))
      #print(repr(args))
      if cmd == 'OWNER':
        if brick.owner >= 0:
          print("WARNING: Multiple owners?\n")
        brick.owner = int(args)
      elif cmd == 'NTOBJECTNAME':
        if brick.objname != "":
          print("WARNING: Multiple names?\n")
        if args[0] != '_':
          print("WARNING: name doesn't start with \'_\'\n")
        brick.objname = args[1:]
      elif cmd == 'EVENT':
        evnumpos = args.index("\t")
        evnum = int(args[:evnumpos])
        nonum = args[evnumpos+1:]
        if len(events) == 0:
          events.append((evnum, nonum))
        else: #insert sort
          for event in enumerate(events):
            if event[1][0] == len(events) - 1: #if we've iterated to the end, just append
              events.append((evnum, nonum))
              break
            if evnum < event[1][0]:
              events.insert(event[0], (evnum, nonum))
              break
      elif cmd == 'EMITTER':
        if brick.emitter != None:
          print("WARNING: Multiple emitters?\n")
        brick.emitter = BLSEmitter.fromLine(args)
      elif cmd == 'LIGHT':
        if brick.light != "":
          print("WARNING: Multiple lights?\n")
        brick.light = args.split("\"")[0]
      elif cmd == 'ITEM':
        if brick.item != None:
          print("WARNING: Multiple items?\n")
        brick.item = BLSItem.fromLine(args)
      elif cmd == 'VEHICLE':
        if brick.vehicle != None:
          print("WARNING: Multiple vehicles?\n")
        brick.vehicle = BLSVehicle.fromLine(args)
      elif cmd == 'AUDIOEMITTER':
        if brick.music != "":
          print("WARNING: Multiple songs?\n")
        brick.music = args.split("\"")[0]
      else:
        raise Exception("Brick line malformed: \"{:s}\"".format(line[1]))
    for event in enumerate(events):
      #print(event)
      if event[0] != event[1][0]:
        print("WARNING: Event count mismatch: {:d} != {:d}  This will be ignored!\n"\
              .format(event[0], event[1][0]))
      brick.add_event(BLSEvent.fromLine(event[1][1]))

    return brick
      

class BLSFile:
  defheading = "This is a Blockland save file.  " + \
  "You probably shouldn't modify it cause you'll screw it up."
  maxpal = 64
  linecountstr = "Linecount"
  defencoding = "latin-1" #probably wrong but it should work

  @property
  def description(self):
    return self._description
  @description.setter
  def description(self, value):
    for item in value:
      if type(item) is not str:
        raise TypeError
    self._description = value

  @property
  def pal(self):
    return self._pal
  @pal.setter
  def pal(self, value):
    for item in value:
      if type(item) is not BLSColor:
        raise TypeError
    if len(value) > BLSFile.maxpal:
      raise TypeError("Too many colors: {:d} > {:d}".format(len(value), maxpal))
    self._pal = value

  @property
  def bricks(self):
    return self._bricks
  @bricks.setter
  def bricks(self, value):
    for item in value:
      if type(item) is not BLSBrick:
        raise TypeError
    self._bricks = value
  
  def add_desc_line(self, line):
    if type(line) is not str:
      raise TypeError
    self._description.append(line)

  def add_color(self, color):
    if type(color) is not BLSColor:
      raise TypeError
    if len(self._pal) >= BLSFile.maxpal:
      raise Exception("Colors is already {:d}!".format(maxpal))
    self._pal.append(color)

  def add_brick(self, brick):
    if type(brick) is not BLSBrick:
      raise TypeError
    self._bricks.append(brick)

  def fromFile(file, brick):
    if type(file) is not TextIOWrapper:
      raise TypeError
    heading = file.readline()[:-1]
    if heading != BLSFile.defheading:
      raise Exception("File signature did not match: \"{:s}\"".format(heading))
    desclines = int(file.readline()[:-1])
    for i in range(desclines):
      brick.add_desc_line(file.readline()[:-1])
    for i in range(BLSFile.maxpal):
      brick.add_color(BLSColor(palstr=file.readline()[:-1]))
    lc = file.readline()[:-1]
    lcp = lc.split(" ")
    if lcp[0] != BLSFile.linecountstr:
      raise Exception("Line count line is invalid: \"{:s}\"".format(lc))
    expectlines = int(lcp[1])
    nextline = file.readline()[:-1]
    totalbricks = 0
    while True:
      totalbricks += 1
      bricklines = list()
      while True:
        bricklines.append(nextline)
        nextline = file.readline()[:-1]
        if nextline[:2] != "+-":
          break
      #print(bricklines)
      brick.add_brick(BLSBrick.fromLines(bricklines))
      if len(nextline) == 0:
        break
    if totalbricks != expectlines:
      print("WARNING: Lines read in does not match line count in file! {} != {}\n", totalbricks, expectlines)

  def __init__(self, filename="", description=list(), pal=list(), bricks=list()):
    if filename != "":
      self.description = list()
      self.pal = list()
      self.bricks = list()

      with open(filename, "r", encoding=BLSFile.defencoding) as file:
        BLSFile.fromFile(file, self)
    else:
      self.description = description
      self.pal = pal
      self.bricks = bricks
      
  def __str__(self):
    ret = BLSFile.defheading + "\n"
    ret += str(len(self.description)) + "\n"
    for line in self.description:
      ret += line + "\n"
    for palent in self.pal:
      ret += str(palent) + "\n"
    for i in range(64 - len(self.pal)):
      ret += "1.000000 0.000000 1.000000 0.000000\n"
    ret += "{:s} {:d}\n".format(BLSFile.linecountstr, len(self.bricks))
    for brick in self.bricks:
      ret += str(brick)

    return ret
