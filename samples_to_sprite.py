# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from PIL import Image
from pprint import pprint
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-sort', dest="SORT", default="flatness=desc=0.75&power=desc", help="Query string to sort by")
parser.add_argument('-lim', dest="LIMIT", default=1296, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-cell', dest="CELL_DIMENSIONS", default="40x40", help="Dimensions of each cell")
parser.add_argument('-cols', dest="COLUMNS", default=48, type=int, help="Number of cells per row")
parser.add_argument('-count', dest="FILE_COUNT", default=6, type=int, help="Number of audio files to produce")
parser.add_argument('-id', dest="UNIQUE_ID", default="sample", help="Key for naming files")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
SORT = args.SORT
LIMIT = args.LIMIT
CELL_W, CELL_H = tuple([int(d) for d in args.CELL_DIMENSIONS.split("x")])
COLUMNS = args.COLUMNS
FILE_COUNT = args.FILE_COUNT
UNIQUE_ID = args.UNIQUE_ID
OVERWRITE = args.OVERWRITE > 0

AUDIO_FILE = "sprites/%s/%s.mp3" % (UNIQUE_ID, UNIQUE_ID)
MANIFEST_FILE = AUDIO_FILE.replace(".mp3", ".json")
IMAGE_FILE = "sprites/%s/%s.png" % (UNIQUE_ID, UNIQUE_ID)

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

jsonData = readJSON(MANIFEST_FILE)

# Sort and limit
rows = sortByQueryString(rows, SORT)
if LIMIT > 0 and len(rows) > LIMIT:
    rows = rows[:LIMIT]
rowCount = len(rows)
ROWS = ceilInt(1.0 * rowCount / COLUMNS)

# Check for 1-d TSNE
if "tsne" in fieldNames:
    rows = sortBy(rows, ("tsne", "asc"))

    # Check for 2-d TSNE
    if "tsne2" in fieldNames:
        newRows = []
        for i in range(ROWS):
            i0 = i * COLUMNS
            i1 = (i+1) * COLUMNS
            if i >= ROWS-1:
                row = rows[i0:]
            else:
                row = rows[i0:i1]
            sortedRow = sorted(row, key=lambda k: k['tsne2'])
            newRows += sortedRow
        rows = newRows[:]

# Sort rows and add sequence
totalDur = sum([r["dur"] for r in rows])
print("Total duration: %s" % formatSeconds(totalDur/1000.0))
print("Each file will be about %s" % formatSeconds(totalDur/1000.0/FILE_COUNT))

# Make sure output dirs exist
makeDirectories([AUDIO_FILE, IMAGE_FILE])

samplesPerFile = ceilInt(1.0 * rowCount / FILE_COUNT)
audioSpriteFiles = []
sprites = []
for file in range(FILE_COUNT):
    iStart = file * samplesPerFile
    iEnd = iStart + samplesPerFile
    fileRows = rows[iStart:iEnd]
    if file >= (FILE_COUNT-1):
        fileRows = rows[iStart:]

    # build the audio
    instructions = []
    ms = 0
    for row in rows:
        instructions.append({
            "ms": ms,
            "filename": AUDIO_DIRECTORY + row["filename"],
            "start": row["start"],
            "dur": row["dur"]
        })
        sprites.append([file, ms, row["dur"]])
        ms += row["dur"]
    outfilename = AUDIO_FILE.replace(".mp3", ".%s.mp3" % zeroPad(file+1, FILE_COUNT))
    if not os.path.isfile(outfilename) or OVERWRITE:
        mixAudio(instructions, ms+1000, outfilename)
    else:
        print("Already created %s" % outfilename)
    audioSpriteFiles.append(outfilename)

jsonData["audioSpriteFiles"] = audioSpriteFiles
jsonData["sprites"] = sprites
writeJSON(MANIFEST_FILE, jsonData)

# Now create the sprite image
IMAGE_W = CELL_W * COLUMNS
IMAGE_H = CELL_H * ROWS
clips = []
x = 0
y = 0
for row in rows:
    clips.append({
        "x": x,
        "y": y,
        "w": CELL_W,
        "h": CELL_H,
        "filename": AUDIO_DIRECTORY + row["filename"],
        "t": row["start"] / 1000.0
    })
    x += CELL_W
    if x >= IMAGE_W:
        x = 0
        y += CELL_H
clipsToFrame({
    "filename": IMAGE_FILE,
    "overwrite": OVERWRITE,
    "width": IMAGE_W,
    "height": IMAGE_H,
    "clips": clips
})
