# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
from matplotlib import pyplot as plt
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
import re
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/downloads/double-bass/*.mp3", help="Input files")
parser.add_argument('-pattern', dest="PATTERN", default="([a-z\-]+)\_([A-Z]s?)([0-9])\_([0-9]+)\_([a-z\-]+)\_([a-z\-]+)\.mp3", help="File pattern")
parser.add_argument('-features', dest="PATTERN_FEATURES", default="group,note,octave,note_dur,dynamic,articulation", help="Features that the pattern maps to")
parser.add_argument('-out', dest="OUTPUT_FILE", default="media/sampler/double-bass.csv", help="CSV output file")
parser.add_argument('-append', dest="APPEND", default=1, type=int, help="Append to existing data?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", action="store_true", help="Show plot?")
args = parser.parse_args()

# Parse arguments
INPUT_FILES = args.INPUT_FILES
OUTPUT_FILE = args.OUTPUT_FILE
PATTERN = args.PATTERN
PATTERN_FEATURES = args.PATTERN_FEATURES.split(",")
APPEND = args.APPEND > 0
OVERWRITE = args.OVERWRITE
PLOT = args.PLOT

# Read files
files = getFilenames(INPUT_FILES)
fileCount = len(files)
filenames = [os.path.basename(fn) for fn in files]
rows = [{"index": i, "filename": os.path.basename(fn), "filepath": fn} for i, fn in enumerate(files)]

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE and not APPEND:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Open existing file
fieldNames = ["filename", "dur", "start"]
if os.path.isfile(OUTPUT_FILE) and APPEND:
    fieldNames, oldRows = readCsv(OUTPUT_FILE)
    if set(PATTERN_FEATURES).issubset(set(fieldNames)) and not OVERWRITE:
        print("Headers already exists in %s. Skipping." % OUTPUT_FILE)
        sys.exit()
    # Update rows
    for row in oldRows:
        if row["filename"] in filenames:
            existingRow = [r for r in rows if r["filename"]==row["filename"]].pop(0)
            index = existingRow["index"]
            rows[index].update(row)

pattern = re.compile(PATTERN)
progress = 0
def getFeatures(row):
    global pattern
    global progress
    global fileCount

    matches = pattern.match(row["filename"])
    if not matches:
        print("Did not match: %s" % row["filename"])
        return None

    for j, feature in enumerate(PATTERN_FEATURES):
        row[feature] = matches.group(j+1)

    if "dur" not in row or OVERWRITE:
        row["dur"] = getDurationFromAudioFile(row["filepath"])
        row["start"] = 0
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/(fileCount-1)*100,1))
    sys.stdout.flush()
    progress += 1
    return row

pool = ThreadPool()
rows = pool.map(getFeatures, rows)
pool.close()
pool.join()

# remove non-matched rows
rows = [row for row in rows if row is not None]

headings = fieldNames[:]
for feature in PATTERN_FEATURES:
    if feature not in headings:
        headings.append(feature)
writeCsv(OUTPUT_FILE, rows, headings)
