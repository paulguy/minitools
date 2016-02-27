#!/bin/sh

ffmpeg -f rawvideo -pixel_format gray -video_size 80x80 -framerate 15 -i $1 \
-f u8 -ar 44100 -ac 1 -i $2 -c:a mp3 -c:v h264 -sws_flags neighbor -s 800x800  \
-aspect 4:3 ${1}.mkv
