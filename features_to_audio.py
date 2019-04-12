# -*- coding: utf-8 -*-

# python features_to_audio.py -in tmp/samples_features.csv -sort hz=asc -out output/sort_hz.mp3

import argparse
from lib.audio_mixer import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
import os
from pprint import pprint
import random
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-sort', dest="SORT", default="hz=asc", help="Sort string")
parser.add_argument('-lim', dest="LIMIT", default=4096, type=int, help="Limit number of clips; -1 if all")
parser.add_argument('-lsort', dest="LIMIT_SORT", default="power=desc=0.8&clarity=desc", help="Sort string if/before reducing clip size")
parser.add_argument('-overlap', dest="OVERLAP", default=256, type=int, help="Overlap clips in milliseconds")
parser.add_argument('-overlapp', dest="OVERLAP_PERCENT", default=0.5, type=float, help="Overlap clips in percentage of clip duration")
parser.add_argument('-left', dest="PAD_LEFT", default=500, type=int, help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default=2000, type=int, help="Pad right in milliseconds")
parser.add_argument('-volume', dest="VOLUME", default=0.6, type=float, help="Volume to be applied to each clip")
parser.add_argument('-rvb', dest="REVERB", default=80, type=int, help="Reverberence (0-100)")
parser.add_argument('-mdb', dest="MATCH_DB", default=-16, type=int, help="Match decibels, -9999 for none")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="If true, just output the duration and do not process")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sort_tsne.mp3", help="Output media file")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

if a.LIMIT > 0 and rowCount > a.LIMIT:
    rows = sortByQueryString(rows, a.LIMIT_SORT)
    rows = rows[:a.LIMIT] if len(rows) > a.LIMIT else rows
    rowCount = len(rows)
    print("Reduced sample size to %s" % rowCount)

# Sort rows and add sequence
rows = sortByQueryString(rows, a.SORT)
ms = a.PAD_LEFT
instructions = []
for i, row in enumerate(rows):
    instructions.append({
        "filename": a.AUDIO_DIRECTORY + row["filename"],
        "ms": ms,
        "start": row["start"],
        "dur": row["dur"],
        "fadeIn": min(100, roundInt(row["dur"] * 0.1)),
        "fadeOut": roundInt(row["dur"] * 0.5),
        "volume": a.VOLUME,
        "reverb": a.REVERB,
        "matchDb": a.MATCH_DB
    })
    delta = min(a.OVERLAP, roundInt(row["dur"] * a.OVERLAP_PERCENT))
    ms += delta
sequenceDuration = ms + a.PAD_RIGHT
print("Total time: %s" % formatSeconds(sequenceDuration/1000))

if a.PROBE:
    sys.exit()

# Mix audio
mixAudio(instructions, sequenceDuration, a.OUTPUT_FILE)
