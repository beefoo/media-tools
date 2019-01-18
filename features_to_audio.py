# -*- coding: utf-8 -*-

# python features_to_audio.py -in tmp/samples_features.csv -sort hz=asc -out output/sort_hz.mp3

import argparse
import csv
from lib.audio_utils import *
from lib.audio_mixer import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
from pydub import AudioSegment
import sys
import time

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-sort', dest="SORT", default="hz=asc", help="Sort string")
parser.add_argument('-overlap', dest="OVERLAP", default=100, type=int, help="Overlap clips in milliseconds")
parser.add_argument('-left', dest="PAD_LEFT", default=500, type=int, help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default=2000, type=int, help="Pad right in milliseconds")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sort_tsne.mp3", help="Output media file")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
SORT = args.SORT
OVERLAP = args.OVERLAP
PAD_LEFT = args.PAD_LEFT
PAD_RIGHT = args.PAD_RIGHT
OUTPUT_FILE = args.OUTPUT_FILE

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# Sort rows and add sequence
rows = sortByQueryString(rows, SORT)
ms = PAD_LEFT
instructions = []
for i, row in enumerate(rows):
    instructions.append({
        "filename": AUDIO_DIRECTORY + row["filename"],
        "ms": ms,
        "start": row["start"],
        "dur": row["dur"]
    })
    delta = min(OVERLAP, roundInt(row["dur"] * 0.5))
    ms += delta
sequenceDuration = ms + PAD_RIGHT
print("Total time: %s" % formatSeconds(sequenceDuration/1000))

# Mix audio
mixAudio(instructions, sequenceDuration, OUTPUT_FILE)
