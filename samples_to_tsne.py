# -*- coding: utf-8 -*-

import argparse
import csv
import librosa
from matplotlib import pyplot as plt
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
from sklearn.manifold import TSNE
import sys
from lib import getFeatureVector, readCsv

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="audio/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_tsne.csv", help="CSV output file")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", default=0, type=int, help="Show plot?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = args.OVERWRITE > 0
PLOT = args.PLOT > 0
PRECISION = 5

# TSNE config
COMPONENTS = 1
LEARNING_RATE = 150 # increase if too dense, decrease if too uniform
VERBOSITY = 2
ANGLE = 0.1 # increase to make faster, decrease to make more accurate

# Read files
rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

for i, row in enumerate(rows):
    rows[i]["path"] = AUDIO_DIRECTORY + row["filename"]

# Make sure output dir exist
outDir = os.path.dirname(OUTPUT_FILE)
if not os.path.exists(outDir):
    os.makedirs(outDir)

progress = 0
def doTSNE(row):
    global progress
    global rowCount

    featureVector = getFeatureVector(row["path"], row["start"], row["dur"])

    progress += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/rowCount*100,1))
    sys.stdout.flush()

    return {
        "filename": row["filename"],
        "start": row["start"],
        "dur": row["dur"],
        "featureVector": featureVector
    }

# files = files[:1]
# for fn in files:
#     doTSNE(fn)
pool = ThreadPool()
data = pool.map(doTSNE, rows)
pool.close()
pool.join()
# sys.exit(1)

featureVectors = [d["featureVector"] for d in data]
model = TSNE(n_components=COMPONENTS, learning_rate=LEARNING_RATE, verbose=VERBOSITY, angle=ANGLE).fit_transform(featureVectors)

print("Writing data to file...")
dims = ["x", "y", "z"]
headings = ["filename", "start", "dur"]
modelNorm = []

for i in range(COMPONENTS):
    headings.append(dims[i])
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
        row = [d["filename"], d["start"], d["dur"]]
        for j in range(COMPONENTS):
            row.append(round(modelNorm[j][i], PRECISION))
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
