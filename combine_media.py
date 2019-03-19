# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="MANIFEST_FILE", default="path/to/ia_fedflixnara_dev.txt", help="Input text file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="output/", help="Directory with media")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/ia_fedflixnara_dev.mp4", help="Media output file")
a = parser.parse_args()

dirname = os.path.dirname(a.MANIFEST_FILE)
basename = os.path.basename(a.MANIFEST_FILE)

if not os.path.isfile(a.MANIFEST_FILE):
    print("Could not find file %s" % a.MANIFEST_FILE)
    sys.exit()

manifestLines = []
with open(a.MANIFEST_FILE) as f:
    manifestLines = [l.strip() for l in f.readlines()]

if len(manifestLines) <= 0:
    print("Could not find instructions in %s" % a.MANIFEST_FILE)
    sys.exit()

# insert media dir
for i, line in enumerate(manifestLines):
    if line.startswith("file"):
        insertPosition = 5
        if line[insertPosition] in ['"', "'"]:
            insertPosition = 6
        newLine = line[:insertPosition] + a.MEDIA_DIRECTORY + line[insertPosition:]
        manifestLines[i] = newLine

# Write to temporary file
tmpFilename = "tmp_" + basename
with open(tmpFilename, 'w') as f:
    for line in manifestLines:
        f.write("%s\n" % line)

# for more options: https://ffmpeg.org/ffmpeg-formats.html#concat
# https://trac.ffmpeg.org/wiki/Concatenate
# ffmpeg -f concat -safe 0 -i mylist.txt -c copy output
command = ['ffmpeg',
           '-f', 'concat',
           '-safe', '0',
           '-i', tmpFilename,
           '-c', 'copy', # https://ffmpeg.org/ffmpeg.html#Stream-copy
           a.OUTPUT_FILE]

print(" ".join(command))
finished = subprocess.check_call(command)

# delete temp file
os.remove(tmpFilename)

print("Done.")
