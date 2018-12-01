# -*- coding: utf-8 -*-

# Looks for samples (clips) in arbitrary media based on audio

# python -W ignore audio_to_samples.py -in "media/downloads/vivaldi/*.mp3" -out "tmp/vivaldi.csv" -count 1296 -features 1 -sort "flatness=asc"
# python -W ignore audio_to_samples.py -in "E:/landscapes/downloads/ia_politicaladarchive/*.mp4" -out "tmp/ia_politicaladarchive_samples.csv" -count 5000 -features 1 -sort "flatness=asc=0.75&power=desc=0.75&dur=desc=0.75"

import argparse
import csv
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
import librosa
import os
from os.path import join
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/sample/bird.wav", help="Input file pattern")
parser.add_argument('-samples', dest="SAMPLES", default=-1, type=int, help="Max samples to produce per media file, -1 for all")
parser.add_argument('-min', dest="MIN_DUR", default=80, type=int, help="Minimum sample duration in ms")
parser.add_argument('-max', dest="MAX_DUR", default=1000, type=int, help="Maximum sample duration in ms, -1 for no max")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples.csv", help="CSV output file")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")

# arguments for managing large media sets
parser.add_argument('-features', dest="FEATURES", default=0, type=int, help="Retrieve features?")
parser.add_argument('-count', dest="COUNT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")

args = parser.parse_args()

# Parse arguments
INPUT_FILES = args.INPUT_FILES
SAMPLES = args.SAMPLES if args.SAMPLES > 0 else None
MIN_DUR = args.MIN_DUR
MAX_DUR = args.MAX_DUR
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = args.OVERWRITE > 0

FEATURES = args.FEATURES > 0
COUNT = args.COUNT
FILTER = args.FILTER
SORT = args.SORT

# Audio config
FFT = 2048
HOP_LEN = FFT/4

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Read files
files = getFilenames(INPUT_FILES)
fileCount = len(files)

# Determine the number of samples per file
samplesPerFile = SAMPLES
if COUNT > 0 and fileCount > 0:
    samplesPerFile = ceilInt(1.0 * COUNT / fileCount)
if samplesPerFile > 0:
    print("%s samples per file." % samplesPerFile)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# Get existing data
rows = []
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    fieldNames, rows = readCsv(OUTPUT_FILE)
rowCount = len(rows)

progress = 0
# files = files[:1]

def getSamples(fn, sampleCount=-1):
    sampleData = getAudioSamples(fn, min_dur=MIN_DUR, max_dur=MAX_DUR, fft=FFT, hop_length=HOP_LEN)
    print("Found %s samples in %s." % (len(sampleData), fn))

    # optionally retrieve features
    if FEATURES:
        sampleData = getFeaturesFromSamples(fn, sampleData)
    # optionally, filter results
    if len(FILTER) > 0:
        sampleData = filterByQueryString(sampleData, FILTER)
    # optionally sort results
    if len(SORT) > 0:
        sampleData = sortByQueryString(sampleData, SORT)

    # if too many samples
    if sampleCount > 0 and len(sampleData) > sampleCount:
        sampleData = sampleData[:sampleCount]

    return sampleData

headings = ["filename", "start", "dur"]
if FEATURES:
    headings += ["power", "hz", "flatness", "note", "octave"]
totalCount = 0
for i, fn in enumerate(files):

    # Check if we already have this data
    if not OVERWRITE and rowCount > 0 and len([row for row in rows if row["filename"]==fn]) > 0:
        totalCount += len([row for row in rows if row["filename"]==fn])
        print("Already found samples for %s. Skipping.")

    else:
        result = getSamples(fn, samplesPerFile)
        # Progressively save samples per audio file
        append = (i > 0)
        writeCsv(OUTPUT_FILE, result, headings=headings, append=append)
        totalCount += len(result)

    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*(i+1)/fileCount*100,1))
    sys.stdout.flush()

print("%s samples in total." % totalCount)
