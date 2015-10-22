import argparse
import BLPalette
import GPLPalette
import PaletteCore

extraExt = '.extra'

argparser = argparse.ArgumentParser(
  description="Convert between Blockland and GIMP palette formats",
  epilog="Only provide one mode.")
argparser.add_argument('--to-gpl', metavar='FILENAME', help="convert Blockland .txt to .gpl")
argparser.add_argument('--to-bl-txt', metavar='FILENAME', help="convert .gpl to Blockland .txt")
argparser.add_argument('--no-restore-alphas', action='store_true',
                       help="Don't read alpha values from extra data.")
argparser.add_argument('--no-restore-divs', action='store_true',
                       help="Don't read divs from extra data.")
argparser.add_argument('--no-restore-extra', action='store_true',
                       help="Don't read any extra data.")

args = argparser.parse_args()

if args.to_gpl != None and args.to_bl_txt != None:
  print("Both modes given at once.")
elif args.to_gpl != None:
  blpal = BLPalette.BLPalette()
  gplpal = GPLPalette.GPLPalette()
  
  outfilename = args.to_gpl[:args.to_gpl.rindex('.')] + '.gpl'
  extrafilename = outfilename + extraExt
  print("Reading {:s}...".format(args.to_gpl))
  with open(args.to_gpl, "r") as infile:
    for line in infile:
      blpal.add_line(line)
  
  print("Converting data structures...")
  for color in blpal.palette:
    gplpal.add_entry(GPLPalette.GPLColor.fromColor(color))
  
  print("Writing extra data to {:s}...".format(extrafilename))
  with open(extrafilename, 'w') as extrafile:
    extrafile.write(str(len(blpal.palette)) + ' ')
    for color in enumerate(blpal.palette):
      extrafile.write(str(color[1].a) + ' ')
    extrafile.write(str(len(blpal.divs)) + ' ')
    for div in blpal.divs:
      extrafile.write(str(div[0]) + ' ')
    for div in blpal.divs:
      extrafile.write(str(div[1]) + ' ')
  
  print("Writing to {:s}...".format(outfilename))
  with open(outfilename, "w") as outfile:
    for line in gplpal:
      outfile.write(line + '\n')
      
  print("Done!")
elif args.to_bl_txt != None:
  blpal = BLPalette.BLPalette()
  gplpal = GPLPalette.GPLPalette()
  
  outfilename = args.to_bl_txt[:args.to_bl_txt.rindex('.')] + '.txt'
  extrafilename = args.to_bl_txt + extraExt
  print("Reading {:s}...".format(args.to_bl_txt))
  with open(args.to_bl_txt, "r") as infile:
    for line in infile:
      gplpal.add_line(line)
  
  print("Converting data structures...")
  for color in gplpal.palette:
    blpal.add_entry(BLPalette.BLColor.fromColor(color))

  if not args.no_restore_extra:
    print("Reading extra data from {:s}...".format(extrafilename))
    extra = ""
    with open(extrafilename, 'r') as extrafile:
      extra = extrafile.read()
    extra = extra.split()
    alphacount = int(extra[0])
    alphastart = 1
    alphaend = 1 + alphacount
    divcount = int(extra[alphaend])
    divlinesstart = 1 + alphacount + 1
    divlinesend = 1 + alphacount + 1 + divcount
    divnamesstart = 1 + alphacount + 1 + divcount
    divnamesend = 1 + alphacount + 1 + divcount + divcount
    alphas = extra[alphastart:alphaend]
    divlines = extra[divlinesstart:divlinesend]
    divnames = extra[divnamesstart:divnamesend]
    if not args.no_restore_alphas:
      for alpha in enumerate(alphas):
        blpal.palette[alpha[0]].a = int(alpha[1])
    if not args.no_restore_divs:
      for i in range(0, divcount):
        blpal.add_div(int(divlines[i]), divnames[i])
  
  print("Writing to {:s}...".format(outfilename))
  with open(outfilename, "w") as outfile:
    for line in blpal:
      outfile.write(line + '\n')
      
  print("Done!")
else:
  print("No mode given.")
  argparser.print_usage()
