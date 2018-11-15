# -*- coding: utf-8 -*-

import argparse
import csv
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
import librosa
from matplotlib import pyplot as plt
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
from sklearn.manifold import TSNE
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_tsne.csv", help="CSV output file")
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
PRECISION = 5

# TSNE config
DIMS = ["tsne", "tsne2", "tsne3"]
COMPONENTS = 1
LEARNING_RATE = 150 # increase if too dense, decrease if too uniform
VERBOSITY = 2
ANGLE = 0.1 # increase to make faster, decrease to make more accurate
FEATURES_TO_ADD = DIMS[:COMPONENTS]

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

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# find unique filepaths
filepaths = list(set([row["path"] for row in rows]))
params = [{
    "samples": [row for row in rows if row["path"]==fp],
    "path": fp
} for fp in filepaths]
fileCount = len(params)

progress = 0
def doTSNE(p):
    global progress
    global rowCount

    fn = p["path"]
    samples = p["samples"]
    featureVectors = []

    # load audio
    fn = getAudioFile(fn)
    y, sr = librosa.load(fn)
    for sample in samples:
        featureVector = getFeatureVector(y, sr, sample["start"], sample["dur"])
        featureVectors.append({
            "filename": sample["filename"],
            "start": sample["start"],
            "dur": sample["dur"],
            "featureVector": featureVector
        })

        progress += 1
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*progress/rowCount*100,1))
        sys.stdout.flush()

    return featureVectors

# files = files[:1]
# for fn in files:
#     doTSNE(fn)
pool = ThreadPool()
data = pool.map(doTSNE, params)
pool.close()
pool.join()
# sys.exit(1)

# flatten data
data = [item for sublist in data for item in sublist]
# remove invalid vectors
data = [d for d in data if True not in np.isnan(d["featureVector"])]
featureVectors = [d["featureVector"] for d in data]
model = TSNE(n_components=COMPONENTS, learning_rate=LEARNING_RATE, verbose=VERBOSITY, angle=ANGLE).fit_transform(featureVectors)

print("Writing data to file...")
headings = fieldNames[:]
modelNorm = []

for i in range(COMPONENTS):
    if DIMS[i] not in headings:
        headings.append(DIMS[i])
    # normalize model between 0 and 1
    if COMPONENTS > 1:
        values = model[:,i]
    else:
        values = model[:]
    minValue = np.min(values)
    maxValue = np.max(values)
    valuesNorm = (values - minValue) / (maxValue - minValue)
    modelNorm.append(valuesNorm)

with open(OUTPUT_FILE, 'wb') as f:
    writer = csv.writer(f)
    writer.writerow(headings)
    for i, d in enumerate(data):
        row = []
        for h in headings:
            if h in DIMS:
                j = DIMS.index(h)
                row.append(round(modelNorm[j][i], PRECISION))
            else:
                row.append(d[h])
        writer.writerow(row)
print("Wrote %s rows to %s" % (len(data), OUTPUT_FILE))

if PLOT and 1 <= COMPONENTS <= 2:
    plt.figure(figsize = (10,10))
    filenames = list(set([d["filename"] for d in data]))
    colors = [filenames.index(d["filename"]) for d in data]
    if COMPONENTS == 2:
        plt.scatter(model[:,0], model[:,1], c=colors)
    else:
        plt.bar(np.arange(len(model)), model[:])
    plt.show()
