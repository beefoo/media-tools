# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import shutil
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="MANIFEST_FILE", default="config/ia_fedflixnara_dev.txt", help="Input text file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/ia_fedflixnara_dev.mp4", help="Media output file")
a = parser.parse_args()

dirname = os.path.dirname(a.MANIFEST_FILE)
basename = os.path.basename(a.MANIFEST_FILE)

# temporarily copy to current directory
if len(dirname) > 0:
    shutil.copyfile(a.MANIFEST_FILE, basename)

# for more options: https://ffmpeg.org/ffmpeg-formats.html#concat
# https://trac.ffmpeg.org/wiki/Concatenate
# ffmpeg -f concat -safe 0 -i mylist.txt -c copy output
command = ['ffmpeg',
           '-f', 'concat',
           '-safe', '0',
           '-i', basename,
           '-c', 'copy', # https://ffmpeg.org/ffmpeg.html#Stream-copy
           a.OUTPUT_FILE]

print(" ".join(command))
finished = subprocess.check_call(command)

# delete temp file
if len(dirname) > 0:
    os.remove(basename)

print("Done.")
