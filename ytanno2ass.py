import xml.etree.ElementTree as ET
from Tkinter import * #needed for fonts
import tkFont
import re
import sys

defaultFont = "Arial"
opaque = 0
translucent = 127
transparent = 255
boxBorders = "000000"
defaultBorderWidth = 1

#sometimes there's no appearance tag
speechDefaultEffects = ""
speechDefaultTextSize = 12 #probably wrong
speechDefaultFGColor = "000000"
speechDefaultBGColor = "FFFFFF"
speechDefaultBGAlpha = 1

# Try experimenting with WrapStyle.  Not super interested in perfect text placement but jsut getting it in the box
ASSHeader = """[Script Info]
Title: YouTube Annotations
ScriptType: v4.00+
WrapStyle: 1
ScaleBorderAndShadow: yes
YCbCr Matrix: None
"""
videoResKeys = ("PlayResX: ", "PlayResY: ")
# May need more values here but let's stay lean for now
styleHeading = """[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
#size is going to be overridden every time so this value is meaningless.  Font is totally meaningless for purely vector draws
styles = """Style: def,""" + defaultFont + """,12,&H00000000,&H00000000,&HFF000000,&HEE000000,0,0,0,0,100,100,0,0,0,0,2,7,0,0,0,1
"""
eventsHeading = """[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
eventKey = "Dialogue: "


def makeASSHeader(width, height):
  return ASSHeader + videoResKeys[0] + str(width) + "\n" + videoResKeys[1] \
    + str(height) + "\n\n" + styleHeading + styles + "\n" + eventsHeading


# just place everything at a 0, 0 margin since it doesn't seem to work reliably
def makeASSEvent(num, start, end, text):
  return eventKey + str(num) + "," + start + "," + end + ",def,,0,0,0,," + text + "\n"


def makeASSBox(x, y, w, h):
  # top left -> top right -> bottom right -> bottom left -> return to top left
  return "m " + str(x) + " " + str(y) \
	 + " l " + str(x + w) + " " + str(y) + " " \
	 + str(x + w) + " " + str(y + h) + " " \
	 + str(x) + " " + str(y + h) + " " \
	 + str(x) + " " + str(y)


def eightBitToHex(val):
    lookup = "0123456789ABCDEF"
    return lookup[val / 16] + lookup[val % 16]


#these return unicode byte arrays for writing to a file
def makeASSBoxWithStyle(x, y, w, h, bcolor, balpha, bsize, fcolor, falpha, keepopen=False):
  #set colors and draw a box
  return ("{\\3a&H" + eightBitToHex(balpha) + "\\1a&H" + eightBitToHex(falpha) + "\\1c&H" + fcolor + "\\3c&H" + bcolor + "\\bord" + str(bsize) \
	   + "\\p1}" + makeASSBox(x, y, w, h) + "{\\p0}").encode('utf8', errors='replace')


def makeASSTextWithStyle(text, x, y, color, size,):
  return ("{\\pos(" + str(x) + "," + str(y) + ")\\1c&H" + color + "\\fs" + str(int(size)) + "}" + text).encode('utf8', errors='replace')


def _getWidth(text, font):
  return (font.measure(text), 0)


#from http://code.activestate.com/recipes/577946-word-wrap-for-proportional-fonts/
def _wordWrap(text, width, extent_func, priv):
    '''
    Word wrap function / algorithm for wrapping text using proportional (versus 
    fixed-width) fonts.
    
    `text`: a string of text to wrap
    `width`: the width in pixels to wrap to
    `extent_func`: a function that returns a (w, h) tuple given any string, to
                   specify the size (text extent) of the string when rendered. 
                   the algorithm only uses the width.
    
    Returns a list of strings, one for each line after wrapping.
    '''
    lines = []
    pattern = re.compile(r'(\s+)')
    lookup = dict((c, extent_func(c, priv)[0]) for c in set(text))
    for line in text.splitlines():
        tokens = pattern.split(line)
        tokens.append('')
        widths = [sum(lookup[c] for c in token) for token in tokens]
        start, total = 0, 0
        for index in xrange(0, len(tokens), 2):
            if total + widths[index] > width:
                end = index + 2 if index == start else index
                lines.append(''.join(tokens[start:end]))
                start, total = end, 0
                if end == index + 2:
                    continue
            total += widths[index] + widths[index + 1]
        if start < len(tokens):
            lines.append(''.join(tokens[start:]))
    lines = [line.strip() for line in lines]
    return lines or ['']


def wordWrap(text, size, width):
  font = tkFont.Font(family = defaultFont, size = int(size), weight = tkFont.NORMAL, slant = tkFont.ROMAN)
  return _wordWrap(text, width, _getWidth, font)


def annoAlphaToASSAlpha(alpha):
  if alpha > 0.1:
    return translucent
  return opaque


def annosToASSFile(annos, assfile, width, height):
  assfile.write(makeASSHeader(width, height))
  
  num = 0
  for anno in annos:
    text = ""
    if anno['type'] == 'highlight': #just a box
      text = makeASSBoxWithStyle(anno['x'], anno['y'], anno['w'], anno['h'], anno['bgColor'], translucent, anno['highlightWidth'], "000000", transparent)
      assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
      num += 1
    elif anno['type'] == 'text':
      if anno['style'] == 'anchored': #a speech bubble with text inside
	alpha = annoAlphaToASSAlpha(anno['bgAlpha'])
	text = makeASSBoxWithStyle(anno['x'], anno['y'], anno['w'], anno['h'], boxBorders, opaque, defaultBorderWidth, anno['bgColor'], alpha)
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
	text = makeASSTextWithStyle(anno['text'], anno['x'], anno['y'], anno['fgColor'], anno['textSize'])
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
      elif anno['style'] == 'popup': #box with text
	alpha = annoAlphaToASSAlpha(anno['bgAlpha'])
	text = makeASSBoxWithStyle(anno['x'], anno['y'], anno['w'], anno['h'], boxBorders, opaque, defaultBorderWidth, anno['bgColor'], alpha)
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
	text = makeASSTextWithStyle(anno['text'], anno['x'], anno['y'], anno['fgColor'], anno['textSize'])
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
      elif anno['style'] == 'title' or anno['style'] == 'highlightText': #just text
	text = makeASSTextWithStyle(anno['text'], anno['x'], anno['y'], anno['fgColor'], anno['textSize'])
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
      elif anno['style'] == 'label': #box with bottom-aligned text, just top align it...
	alpha = annoAlphaToASSAlpha(anno['bgAlpha'])
	text = makeASSBoxWithStyle(anno['x'], anno['y'], anno['w'], anno['h'], anno['bgColor'], alpha, defaultBorderWidth, "000000", transparent)
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
	text = "{\\3a&H00" #turn border back on for readability
	if anno['fgColor'] == "000000": # as of this writing, youtube only supports black and white so do simple invert
	  text += "\\3c&HFFFFFF}"
	text += makeASSTextWithStyle(anno['text'], anno['x'], anno['y'], anno['fgColor'], anno['textSize'])
	assfile.write(makeASSEvent(num, anno['start'], anno['end'], text))
	num += 1
      else:
	raise Exception("Unimplemented annotation style")
    else:
      raise Exception("Unimplemented annotation type")


def getXMLFromFile(filename):
  tree = ET.parse(filename)
  return tree.getroot()


def videoTimeToMS(time):
  if(time == 'never'): # sillyness with highlight type, gets overwritten
    return -1
  
  parts = time.split(':')
  hours = 0
  mins = 0

  if(len(parts) == 3):
    hours = int(parts[0])
    mins = int(parts[1])
    msecs = int(float(parts[2]) * 1000)
  elif(len(parts) == 2):
    mins = int(parts[0])
    msecs = int(float(parts[1]) * 1000)
  elif(len(parts) == 1):
    msecs = int(float(parts[0]) * 1000)
  else:
    raise Exception("Unrecognized time format")
  
  return (hours * 60 * 60 * 1000) + (mins * 60 * 1000) + msecs


def MSToASSTime(time):
  time /= 10 # ASS time is only down to centiseconds, so cut off the thousandths
  hours = time / (100 * 60 * 60)
  mins = (time - (hours * 100 * 60 * 60)) / (100 * 60)
  secs = (time - (hours * 100 * 60 * 60) - (mins * 100 * 60)) / 100
  csecs = time % 100

  return "%d:%02d:%02d.%02d" % (hours, mins, secs, csecs)


#slow but should be safe.  Not terribly speed-critical
def RGBIntToBGRHex(color):
  red = color / (256 * 256)
  green = (color - (red * 256 * 256)) / 256
  blue = color % 256

  return eightBitToHex(blue) + eightBitToHex(green) + eightBitToHex(red)


def XMLElementToAnnotationsList(elem, width, height):
  annos = list()
  
  if elem.tag != 'document':
    raise Exception("root tag isn't 'document'")

  xmlannos = elem.find('annotations').findall('annotation')
  if xmlannos == None:
    raise Exception("didn't find any annotations")

  for xmlanno in xmlannos:
    anno = dict()

    # text - any sort of text annotation
    # highlight - just a box
    anno['type'] = xmlanno.get('type')

    appearance = xmlanno.find('appearance')

    if anno['type'] == 'text':
      anno['text'] = xmlanno.find('TEXT') # only text types have text.
      if anno['text'] == None:
	anno['text'] = ""
      else:
	anno['text'] = anno['text'].text
      
      # popup - big ugly box
      # label - box with text at bottom on hover
      # highlightText - refers to a highlight type by id, x and y are RELATIVE
      # anchored - speech bubble
      # title - undecorated text
      anno['style'] = xmlanno.get('style') # also the only ones with a style
      if anno['style'] == 'anchored':
	anno['textSize'] = float(appearance.get('textSize'))
	anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('fgColor')))
	anno['bgColor'] = RGBIntToBGRHex(int(appearance.get('bgColor')))
	anno['bgAlpha'] = float(appearance.get('bgAlpha'))
      elif anno['style'] == 'speech': #like an anchored, but may be missing an appearance
	anno['style'] = 'anchored'
	if appearance == None:
	  anno['textSize'] = speechDefaultTextSize
	  anno['fgColor'] = speechDefaultFGColor
	  anno['bgColor'] = speechDefaultBGColor
	  anno['bgAlpha'] = speechDefaultBGAlpha
	else:
	  if 'textSize' not in anno:
	    anno['textSize'] = speechDefaultTextSize
	  else:
	    anno['textSize'] = float(appearance.get('textSize'))
	  anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('fgColor')))
	  anno['bgColor'] = RGBIntToBGRHex(int(appearance.get('bgColor')))
	  anno['bgAlpha'] = float(appearance.get('bgAlpha'))
      elif anno['style'] == 'popup':
	anno['effects'] = appearance.get('effects')
	anno['textSize'] = float(appearance.get('textSize'))
	anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('fgColor')))
	anno['bgColor'] = RGBIntToBGRHex(int(appearance.get('bgColor')))
	anno['bgAlpha'] = float(appearance.get('bgAlpha'))
      elif anno['style'] == 'title':
	anno['textSize'] = float(appearance.get('textSize'))
	anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('fgColor')))
      elif anno['style'] == 'highlightText':
	anno['textSize'] = float(appearance.get('textSize'))
	anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('highlightFontColor')))
	# get id of relative highlight
	anno['relativeid'] = xmlanno.find('segment').get('spaceRelative')
      elif anno['style'] == 'label':
	anno['effects'] = appearance.get('effects')
	anno['textSize'] = float(appearance.get('textSize'))
	anno['fgColor'] = RGBIntToBGRHex(int(appearance.get('highlightFontColor')))
	anno['bgColor'] = RGBIntToBGRHex(int(appearance.get('fgColor'))) # this may be wrong
	anno['bgAlpha'] = float(appearance.get('bgAlpha'))
      else:
	print("WARNING: Unsupported style \"%s\"" % anno['style'])
	continue
    elif anno['type'] == 'highlight':
      anno['id'] = xmlanno.get('id') # annotation id, used by highlight
      anno['bgColor'] = RGBIntToBGRHex(int(appearance.get('bgColor')))
      anno['bgAlpha'] = float(appearance.get('borderAlpha'))
      anno['highlightWidth'] = float(appearance.get('highlightWidth'))
    else:
      print("WARNING: Unsupported type \"%s\"" % anno['type'])
      continue
    # effects - bevel, dropshadow, textdropshadow
    # textSize - text height, 100 = video height?
    # fgColor - text color
    # bgColor - box color
    # bgAlpha - solid is almost 0 and transparent is nonzero?
    # highlightWidth - box line width for highlights

    if anno['type'] == 'text' and anno['style'] == 'anchored': # speech bubble ones use a different name
      annoregion = xmlanno.find('segment').find('movingRegion').findall('anchoredRegion')
      anno['sx'] = float(annoregion[0].get('sx')) # TODO figure this out, speech bubble pointer location
      anno['sy'] = float(annoregion[0].get('sy'))
    else:
      annoregion = xmlanno.find('segment').find('movingRegion').findall('rectRegion')
    anno['x'] = int(float(annoregion[0].get('x')) / 100 * width) # location.  all location values seem to be from 0 to 100
    anno['y'] = int(float(annoregion[0].get('y')) / 100 * height) # 0,0 being top left, 100,100 being bottom right
    anno['w'] = int(float(annoregion[0].get('w')) / 100 * width) # size
    anno['h'] = int(float(annoregion[0].get('h')) / 100 * height)
    anno['start'] = videoTimeToMS(annoregion[0].get('t')) # start and end time in video
    anno['end'] = videoTimeToMS(annoregion[1].get('t'))
    
    action = xmlanno.find('action')
    if action != None and action.get('type') == 'openUrl': # get URLs to place on link annotations
      anno['link'] = action.find('url').get('value')
    annos.append(anno)
    
    print("%s" % anno['type'])
    if anno['type'] == 'text':
      print("%s \"%s\"" % (anno['style'], anno['text']))

  #resolve highlights and make relative values absolute, copy time to highlightText
  for anno in annos:
    if anno['type'] == 'text' and anno['style'] == 'highlightText':
      if anno['relativeid'] == None or anno['relativeid'] == "":
	raise Exception("No spaceRelative for highlightText")
      relanno = None
      for findanno in annos:
	if 'id' in findanno and findanno['id'] == anno['relativeid']:
	  relanno = findanno
      if relanno == None:
	raise Exception("highlightText refers to id that does not exist")
      anno['x'] = relanno['x'] + anno['x']
      anno['y'] = relanno['y'] + anno['y']
      anno['start'] = relanno['start']
      anno['end'] = relanno['end']

  #sort annotations by start time
  annos.sort(key = lambda x: x['start'])

  #convert times to ASS times h:MM:SS.CC, scale font heights
  root = Tk()  # have the window open as short a time as possible
  for anno in annos:
    anno['start'] = MSToASSTime(anno['start'])
    anno['end'] = MSToASSTime(anno['end'])
    if anno['type'] == 'text':
      anno['textSize'] = anno['textSize'] / 100 * height

    #also wrap text.  This part is ugly and requires creating a window
    if anno['type'] == 'text':
      anno['text'] = wordWrap(anno['text'], anno['textSize'], anno['w'])
      
      newtext = ""
      for line in enumerate(anno['text']):
	newtext += line[1]
	if line[0] < len(anno['text']) - 1: # don't add new line to last line
	  newtext += "\\N"
      anno['text'] = newtext
  root.destroy()

  return annos

if len(sys.argv) != 4:
  print("USAGE: ytanno2ass.py <file> <width> <height>")
else:
  root = getXMLFromFile(sys.argv[1])
  annos = XMLElementToAnnotationsList(root, int(sys.argv[2]), int(sys.argv[3]))
  with open("%s.ass" % sys.argv[1], "w") as assfile:
    annosToASSFile(annos, assfile, int(sys.argv[2]), int(sys.argv[3]))
