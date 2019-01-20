# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import numpy as np
import os
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_fedflixnara.csv", help="Input file")
parser.add_argument('-dir', dest="SAMPLE_FILE_DIRECTORY", default="tmp/ia_fedflixnara_samples/", help="Directory to where the .csv files with sample data is found")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="File to write results to. Leave blank to update the input file")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
THREADS = getThreadCount(a.THREADS)

# get files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

FEATURES_TO_ADD = ["samples", "medianPower", "medianHz", "medianClarity", "medianDur"]
for f in FEATURES_TO_ADD:
    if f not in set(fieldNames):
        fieldNames.append(f)

filenames = [a.SAMPLE_FILE_DIRECTORY + r["filename"]+".csv" for r in rows]

progress = 0
def getSampleFeatures(p):
    global FEATURES_TO_ADD
    global progress
    global rowCount

    result = dict([(f, -1) for f in FEATURES_TO_ADD])
    i, fn = p

    if os.path.isfile(fn):
        _, samples = readCsv(fn)

        result["samples"] = len(samples)
        result["medianPower"] = np.median([s["power"] for s in samples])
        result["medianHz"] = np.median([s["hz"] for s in samples])
        result["medianClarity"] = np.median([s["clarity"] for s in samples])
        result["medianDur"] = np.median([s["dur"] for s in samples])

    progress += 1
    printProgress(progress, rowCount)

    return (i, result)

pool = ThreadPool(THREADS)
results = pool.map(getSampleFeatures, filenames)
pool.close()
pool.join()

# Update rows
for i, r in results:
    rows[i].update(r)

writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
