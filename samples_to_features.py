# -*- coding: utf-8 -*-

import argparse
import csv
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
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
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_features.csv", help="CSV output file")
parser.add_argument('-append', dest="APPEND", default=1, type=int, help="Append to existing data?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", action="store_true", help="Show plot?")
parser.add_argument('-threads', dest="THREADS", default=4, type=int, help="Number of threads")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
MEDIA_DIRECTORY = args.MEDIA_DIRECTORY
OUTPUT_FILE = args.OUTPUT_FILE
APPEND = args.APPEND > 0
OVERWRITE = args.OVERWRITE
PLOT = args.PLOT
THREADS = args.THREADS

FEATURES_TO_ADD = ["power", "hz", "clarity", "note", "octave"]

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
    rows[i]["path"] = MEDIA_DIRECTORY + row["filename"]

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# find unique filepaths
filepaths = list(set([row["path"] for row in rows]))
params = [{
    "samples": [row for row in rows if row["path"]==fp],
    "path": fp
} for fp in filepaths]
fileCount = len(params)

def samplesToFeatures(p):
    fn = p["path"]
    samples = p["samples"]
    features = getFeaturesFromSamples(fn, samples)
    return features

# files = files[:1]
# for p in params:
#     samplesToFeatures(p)
# sys.exit(1)
threads = getThreadCount(THREADS)
pool = ThreadPool(threads)
data = pool.map(samplesToFeatures, params)
pool.close()
pool.join()

# flatten data
data = [item for sublist in data for item in sublist]

headings = fieldNames[:]
for feature in FEATURES_TO_ADD:
    if feature not in headings:
        headings.append(feature)
writeCsv(OUTPUT_FILE, data, headings)

if PLOT:
    plt.figure(figsize = (10,6))
    pows = [d["power"] for d in data]
    hzs = [d["hz"] for d in data]
    flts = [d["clarity"] for d in data]

    ax = plt.subplot(1, 3, 1)
    ax.set_title("Power distribution")
    plt.hist(pows, bins=50)

    ax = plt.subplot(1, 3, 2)
    ax.set_title("Frequency distribution")
    plt.hist(hzs, bins=50)

    ax = plt.subplot(1, 3, 3)
    ax.set_title("Clarity distribution")
    plt.hist(flts, bins=50)

    plt.tight_layout()
    plt.show()
