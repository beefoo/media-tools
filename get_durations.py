# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.video_utils import *
import os
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/ia_politicaladarchive/", help="Input dir")
parser.add_argument('-fk', dest="FILENAME_KEY", default="filename", help="Key to retrieve filename")
parser.add_argument('-dk', dest="DURATION_KEY", default="duration", help="Key to save duration")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
MEDIA_DIRECTORY = args.MEDIA_DIRECTORY
FILENAME_KEY = args.FILENAME_KEY
DURATION_KEY = args.DURATION_KEY

# get unique video files
print("Reading file...")
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# add duration key
if DURATION_KEY not in fieldNames:
    fieldNames.append(DURATION_KEY)

print("Getting durations...")
for i, row in enumerate(rows):
    duration = 0
    if FILENAME_KEY in row and len(row[FILENAME_KEY]) > 0:
        filepath = MEDIA_DIRECTORY + row[FILENAME_KEY]
        duration = getDurationFromFile(filepath)
    rows[i][DURATION_KEY] = duration
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*i/(rowCount-1)*100,1))
    sys.stdout.flush()

writeCsv(INPUT_FILE, rows, headings=fieldNames)
