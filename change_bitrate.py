# -*- coding: utf-8 -*-

import argparse
import os
import re
import shutil
import subprocess
import sys

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/downloads/*.mp3", help="Input file pattern")
parser.add_argument('-bitrate', dest="BITRATE", default=128, help="Target bitrate")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/128k/", help="Output file pattern")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output details?")
a = parser.parse_args()

files = getFilenames(a.INPUT_FILE)

OUTPUT_DIR = a.OUTPUT_DIR if len(a.OUTPUT_DIR) > 0 else os.path.dirname(a.INPUT_FILE) + "/"

if not a.PROBE:
    makeDirectories([OUTPUT_DIR])

hasTmp = False
for i, fn in enumerate(files):
    infn = fn.replace("\\", "/")
    outfn = OUTPUT_DIR + os.path.basename(infn)
    if outfn == infn:
        hasTmp = True
        outfn = OUTPUT_DIR + "tmp/" + os.path.basename(infn)
        if i==0 and not a.PROBE:
            makeDirectories([outfn])
    command = ['ffmpeg','-y',
                '-i', infn,
                '-map','0:a:0',
                '-b:a', '%sk' % a.BITRATE,
                outfn]
    print(" ".join(command))

    if a.PROBE:
        continue

    finished = subprocess.check_call(command)
    if hasTmp:
        os.remove(infn)
        shutil.copyfile(outfn, infn)

if hasTmp and not a.PROBE:
    shutil.rmtree(OUTPUT_DIR + "tmp")

print("Done.")
