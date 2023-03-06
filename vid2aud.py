#!/usr/bin/env python

import sys
import subprocess
import json
import pathlib

probeargs = ['ffprobe', '-loglevel', 'quiet', '-hide_banner', '-of', 'json', '-show_streams', '-i', '']
convertargs = ['ffmpeg', '-i', '', '-map', '0:a:0', '-c:a', 'copy', '']

outdir = pathlib.Path("music")
outdir.mkdir(exist_ok=True)

for item in sys.argv[1:]:
    probeargs[-1] = item
    proc = subprocess.run(probeargs, stdout=subprocess.PIPE)
    iteminfo = json.loads(proc.stdout)
    newname = pathlib.Path(pathlib.Path(item).name)
    for stream in iteminfo['streams']:
        if stream['codec_type'] == 'audio':
            codec = stream['codec_name']
            if codec == 'opus' or codec == 'vorbis':
                newname = newname.with_suffix(".ogg")
            elif codec == 'aac':
                newname = newname.with_suffix(".m4a")
            break
    outfile = outdir / newname
    print("Filename: {}  Codec: {}".format(item, codec))
    print("New File: {}".format(outfile))
    convertargs[2] = item
    convertargs[-1] = outfile
    subprocess.run(convertargs)
