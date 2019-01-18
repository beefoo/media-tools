# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/*.csv", help="Input file pattern")
parser.add_argument('-dir', dest="INPUT_DIR", default="tmp/", help="Directory of input files (if reading from a manifest .csv file)")
parser.add_argument('-sort', dest="SORT", default="start=asc", help="Query string to sort by")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-per', dest="LIMIT_PER_FILE", default=-1, type=int, help="Target sample count per file, -1 for everything")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/combined_samples.csv", help="Write the result to file?")
a = parser.parse_args()

# Read files
files = []
fromManifest = a.INPUT_FILE.endswith(".csv") and "*" not in a.INPUT_FILE
if fromManifest:
    fieldNames, files = readCsv(a.INPUT_FILE)
    for i, f in enumerate(files):
        files[i]["sampleFilename"] = a.INPUT_DIR + f["filename"] + ".csv"
else:
    files = getFilenames(a.INPUT_FILE)
    files = [{"sampleFilename": f} for f in files]
fileCount = len(files)
print("Found %s files" % fileCount)

# check to see how many samples we should retrieve per file (if applicable)
limitPerFile = a.LIMIT_PER_FILE
if a.LIMIT > 0:
    limitPerFile = roundInt(1.0 * a.LIMIT / fileCount)
    firstFile = files[0]
    if "samples" in firstFile:
        totalCount = sum([f["samples"] for f in files])
        if totalCount <= a.LIMIT:
            limitPerFile = -1

allSamples = []
allFieldNames = []
for i, f in enumerate(files):
    fn = f["sampleFilename"]
    if os.path.isfile(fn):
        fieldNames, samples = readCsv(fn)
        allFieldNames = unionLists(allFieldNames, fieldNames)
        sampleCount = len(samples)
        if limitPerFile > 0 and sampleCount > limitPerFile:
            samples = sortByQueryString(samples, a.SORT)
            samples = samples[:limitPerFile]
        allSamples += samples
    printProgress(i+1, fileCount)

writeCsv(a.OUTPUT_FILE, allSamples, headings=allFieldNames)
