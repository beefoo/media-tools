# -*- coding: utf-8 -*-

# Looks for samples (clips) in arbitrary media based on audio

# python -W ignore audio_to_samples.py -in "media/downloads/vivaldi/*.mp3" -out "tmp/vivaldi.csv" -count 1296 -features 1 -sort "clarity=desc"
# python -W ignore audio_to_samples.py -in "E:/landscapes/downloads/ia_politicaladarchive/*.mp4" -out "tmp/ia_politicaladarchive_samples.csv" -count 5000 -features 1 -sort "clarity=desc=0.75&power=desc=0.75&dur=desc=0.75"

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
parser.add_argument('-in', dest="INPUT_FILE", default="media/sample/bird.wav", help="Input file pattern")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/ia_politicaladarchive/", help="Input dir")
parser.add_argument('-samples', dest="SAMPLES", default=-1, type=int, help="Max samples to produce per media file, -1 for all")
parser.add_argument('-min', dest="MIN_DUR", default=80, type=int, help="Minimum sample duration in ms")
parser.add_argument('-max', dest="MAX_DUR", default=1000, type=int, help="Maximum sample duration in ms, -1 for no max")
parser.add_argument('-delta', dest="ONSET_DELTA", default=0.07, type=float, help="Onset delta; must be larger than 0")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples.csv", help="CSV output file")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")

# arguments for managing large media sets
parser.add_argument('-features', dest="FEATURES", action="store_true", help="Retrieve features?")
parser.add_argument('-count', dest="COUNT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")

args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
MEDIA_DIRECTORY = args.MEDIA_DIRECTORY
SAMPLES = args.SAMPLES
MIN_DUR = args.MIN_DUR
MAX_DUR = args.MAX_DUR
ONSET_DELTA = args.ONSET_DELTA
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = args.OVERWRITE
MULTIFILE_OUTPUT = ("%s" in OUTPUT_FILE)

FEATURES = args.FEATURES
COUNT = args.COUNT
FILTER = args.FILTER
SORT = args.SORT

# Audio config
FFT = 2048
HOP_LEN = int(FFT/4)

# Check if file exists already
# if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
#     print("%s already exists. Skipping." % OUTPUT_FILE)
#     sys.exit()

# Read files
fieldNames, files, fileCount = getFilesFromString(args)

if "duration" in fieldNames and "hasAudio" in fieldNames:
    files = filterWhere(files, [("duration", 0, ">"), ("hasAudio", 0, ">")])
    fileCount = len(files)
    print("Found %s rows after filtering" % fileCount)

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
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE and not MULTIFILE_OUTPUT:
    fieldNames, rows = readCsv(OUTPUT_FILE)
rowCount = len(rows)

progress = 0
# files = files[:1]

def getSamples(fn, sampleCount=-1):
    print("Retrieving samples for %s..." % fn)
    sampleData, y, sr = getAudioSamples(fn, min_dur=MIN_DUR, max_dur=MAX_DUR, fft=FFT, hop_length=HOP_LEN, delta=ONSET_DELTA)
    print("Found %s samples in %s." % (len(sampleData), fn))

    if len(sampleData) > 0:
        # optionally retrieve features
        if FEATURES:
            sampleData = getFeaturesFromSamples(fn, sampleData, y=y, sr=sr)
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
    headings += ["power", "hz", "clarity", "note", "octave"]
totalCount = 0
for i, f in enumerate(files):
    fn = f["filename"]
    basename = os.path.basename(fn)
    outputFilename = OUTPUT_FILE if not MULTIFILE_OUTPUT else OUTPUT_FILE % basename

    if MULTIFILE_OUTPUT and not OVERWRITE and os.path.isfile(outputFilename):
        print("Already found samples for %s. Skipping." % outputFilename)

    # Check if we already have this data
    elif not MULTIFILE_OUTPUT and not OVERWRITE and rowCount > 0 and len([row for row in rows if row["filename"]==basename]) > 0:
        totalCount += len([row for row in rows if row["filename"]==fn])
        print("Already found samples for %s. Skipping." % basename)

    else:
        result = getSamples(fn, samplesPerFile)
        # Progressively save samples per audio file
        append = (i > 0 and not MULTIFILE_OUTPUT)
        writeCsv(outputFilename, result, headings=headings, append=append)
        totalCount += len(result)

    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*(i+1)/fileCount*100,1))
    sys.stdout.flush()

print("%s samples in total." % totalCount)
