# -*- coding: utf-8 -*-

import argparse
import math
import os
from PIL import Image
from pprint import pprint
import sys

from lib.audio_mixer import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-props', dest="PROPS", default="tsne,tsne2", help="Properties to sort x,y matrix by")
parser.add_argument('-sort', dest="SORT", default="flatness=desc=0.5&power=desc", help="Query string to filter and sort by")
parser.add_argument('-lim', dest="LIMIT", default=1296, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-width', dest="IMAGE_W", default=1920, type=int, help="Image width in pixels")
parser.add_argument('-height', dest="IMAGE_H", default=1080, type=int, help="Image height in pixels")
parser.add_argument('-cell', dest="CELL_DIMENSIONS", default="40x40", help="Dimensions of each cell")
parser.add_argument('-count', dest="FILE_COUNT", default=6, type=int, help="Number of audio files to produce")
parser.add_argument('-id', dest="UNIQUE_ID", default="sample", help="Key for naming files")
parser.add_argument('-log', dest="LOG", default=0, type=int, help="Display using log?")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
SORT = args.SORT
PROP1, PROP2 = tuple([p for p in args.PROPS.strip().split(",")])
LIMIT = args.LIMIT
IMAGE_W = args.IMAGE_W
IMAGE_H = args.IMAGE_H
CELL_W, CELL_H = tuple([int(d) for d in args.CELL_DIMENSIONS.split("x")])
FILE_COUNT = args.FILE_COUNT
UNIQUE_ID = args.UNIQUE_ID
OVERWRITE = args.OVERWRITE > 0
LOG = args.LOG

AUDIO_FILE = "sprites/%s/%s.mp3" % (UNIQUE_ID, UNIQUE_ID)
MANIFEST_FILE = AUDIO_FILE.replace(".mp3", ".json")
IMAGE_FILE = "sprites/%s/%s.png" % (UNIQUE_ID, UNIQUE_ID)

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Sort and limit
rows = sortByQueryString(rows, SORT)
if LIMIT > 0 and len(rows) > LIMIT:
    rows = rows[:LIMIT]
rowCount = len(rows)

# use logarithmic scale
if LOG > 0:
    for i, row in enumerate(rows):
        base = LOG if LOG > 1 else math.e
        rows[i][PROP1] = math.log(row[PROP1], base)
        rows[i][PROP2] = math.log(row[PROP2], base)

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
    for row in fileRows:
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
    audioSpriteFiles.append(os.path.basename(outfilename))

# Now create the sprite image
clips = []
values1 = [row[PROP1] for row in rows]
values2 = [row[PROP2] for row in rows]
range1 = (min(values1), max(values1))
range2 = (min(values2), max(values2))
for i, row in enumerate(rows):
    nx = norm(row[PROP1], range1)
    ny = norm(row[PROP2], range2)
    x = roundInt((IMAGE_W - CELL_W) * nx)
    y = roundInt((IMAGE_H - CELL_H) * ny)
    clips.append({
        "x": x,
        "y": y,
        "w": CELL_W,
        "h": CELL_H,
        "filename": AUDIO_DIRECTORY + row["filename"],
        "t": row["start"] / 1000.0
    })
    sprites[i] += [round(1.0*x/IMAGE_W, 3), round(1.0*y/IMAGE_H, 3)]

print("Generating image...")
clipsToFrame({
    "filename": IMAGE_FILE,
    "overwrite": OVERWRITE,
    "width": IMAGE_W,
    "height": IMAGE_H,
    "clips": clips
})

# Write json sprite file
jsonData = {}
jsonData["audioSpriteFiles"] = audioSpriteFiles
jsonData["sprites"] = sprites
jsonData["image"] = os.path.basename(IMAGE_FILE)
jsonData["width"] = IMAGE_W
jsonData["height"] = IMAGE_H
jsonData["cellW"] = CELL_W
jsonData["cellH"] = CELL_H
writeJSON(MANIFEST_FILE, jsonData)
