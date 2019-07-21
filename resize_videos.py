# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="path/to/*.mp4", help="Input media file pattern")
parser.add_argument('-width', dest="TARGET_WIDTH", default=640, type=int, help="Target width")
parser.add_argument('-height', dest="TARGET_HEIGHT", default=360, type=int, help="Target height")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/%s.mp4", help="Media output file pattern")
a = parser.parse_args()

from lib.io_utils import *

makeDirectories([a.OUTPUT_FILE])
filenames = getFilenames(a.INPUT_FILES)

for infile in filenames:
    basefn = getBasename(infile)
    command = ['ffmpeg',
               '-y',
               '-i', infile,
               '-vf', 'scale=%s:%s' % (a.TARGET_WIDTH, a.TARGET_HEIGHT),
               a.OUTPUT_FILE % basefn]
    print(" ".join(command))
    finished = subprocess.check_call(command)

print("Done.")
