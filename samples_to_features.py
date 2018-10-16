# -*- coding: utf-8 -*-

import argparse
import csv
from lib import *
import librosa
from matplotlib import pyplot as plt
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="audio/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_features.csv", help="CSV output file")
parser.add_argument('-append', dest="APPEND", default=1, type=int, help="Append to existing data?")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", default=0, type=int, help="Show plot?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
OUTPUT_FILE = args.OUTPUT_FILE
APPEND = args.APPEND > 0
OVERWRITE = args.OVERWRITE > 0
PLOT = args.PLOT > 0

FEATURES_TO_ADD = ["power", "hz", "note", "octave"]

# Read files
rows = []
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE and not APPEND:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

if APPEND and set(FEATURES_TO_ADD).issubset(set(fieldNames)) and not OVERWRITE:
    print("Headers already exists in %s. Skipping." % OUTPUT_FILE)
    sys.exit()

for i, row in enumerate(rows):
    rows[i]["path"] = AUDIO_DIRECTORY + row["filename"]

# Make sure output dir exist
outDir = os.path.dirname(OUTPUT_FILE)
if not os.path.exists(outDir):
    os.makedirs(outDir)

# find unique filepaths
filepaths = list(set([row["path"] for row in rows]))
params = [{
    "samples": [row for row in rows if row["path"]==fp],
    "path": fp
} for fp in filepaths]
fileCount = len(params)

progress = 0
def samplesToFeatures(p):
    global progress
    global rowCount

    fn = p["path"]
    samples = p["samples"]
    features = []

    # load audio
    fn = getAudioFile(fn)
    y, sr = librosa.load(fn)

    for sample in samples:
        sfeatures = sample.copy()
        sfeatures.update(getFeatures(y, sr, sample["start"], sample["dur"]))
        features.append(sfeatures)

        progress += 1
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*progress/rowCount*100,1))
        sys.stdout.flush()

    return features

# files = files[:1]
# for p in params:
#     samplesToFeatures(p)
# sys.exit(1)
pool = ThreadPool()
data = pool.map(samplesToFeatures, params)
pool.close()
pool.join()


# flatten data
data = [item for sublist in data for item in sublist]

headings = fieldNames[:]
for feature in FEATURES_TO_ADD:
    if feature not in headings:
        headings.append(feature)
with open(OUTPUT_FILE, 'wb') as f:
    writer = csv.writer(f)
    writer.writerow(headings)
    for i, d in enumerate(data):
        row = []
        for h in headings:
            row.append(d[h])
        writer.writerow(row)
print("Wrote %s rows to %s" % (len(data), OUTPUT_FILE))

if PLOT:
    plt.figure(figsize = (10,6))
    pows = [d["power"] for d in data]
    hzs = [d["hz"] for d in data]

    ax = plt.subplot(1, 2, 1)
    ax.set_title("Power distribution")
    plt.hist(pows, bins=50)

    ax = plt.subplot(1, 2, 2)
    ax.set_title("Frequency distribution")
    plt.hist(hzs, bins=50)

    plt.tight_layout()
    plt.show()
