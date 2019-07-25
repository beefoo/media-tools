# -*- coding: utf-8 -*-

import argparse
import os
import re
import shutil
import sys

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/frame.*.png", help="Inpuyt frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output file pattern; leave blank if renaming")
parser.add_argument('-start', dest="START_FRAMES_AT", default=1, help="Make the first frame start at this number")
a = parser.parse_args()
aa = vars(a)

renameFiles = (len(a.OUTPUT_FILE) <= 0)
if not renameFiles:
    makeDirectories(a.OUTPUT_FILE)
else:
    aa["OUTPUT_FILE"] = a.INPUT_FILE.replace("*", "%s")
filenames = getFilenames(a.INPUT_FILE)

patternStr = a.INPUT_FILE.replace("*", "([0-9]+)")
pattern = re.compile(patternStr)
padCount = None
files = []
for filename in filenames:
    matches = pattern.match(filename)

    if not matches:
        print("Did not match: %s" % filename)
        continue

    match = matches.group(1)

    if padCount is None:
        padCount = len(match)

    number = int(match.lstrip("0"))
    files.append({
        "filename": filename,
        "number": number
    })

fileCount = len(files)
if fileCount < 1:
    print("No files found")
    sys.exit()

startNumberBefore = min([f["number"] for f in files])
delta = a.START_FRAMES_AT - startNumberBefore
if delta == 0:
    print("No change needed")
    sys.exit()

isReversed = (delta > 0)
files = sorted(files, key=lambda f: f["number"], reverse=isReversed)

for i, f in enumerate(files):
    numberStr = str(f["number"]+delta).zfill(padCount)
    newFilename = a.OUTPUT_FILE % numberStr
    if renameFiles:
        os.rename(f["filename"], newFilename)
        # print("%s -> %s" % (f["filename"], newFilename))
    else:
        shutil.copyfile(f["filename"], newFilename)
    printProgress(i+1, fileCount)
