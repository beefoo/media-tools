# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import random
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/*.csv", help="Input file pattern")
parser.add_argument('-dir', dest="INPUT_DIR", default="tmp/", help="Directory of input files (if reading from a manifest .csv file)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/combined_samples.csv", help="Write the result to file")

parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
parser.add_argument('-filter', dest="FILTER", default="samples>0", help="Query string to filter by")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")

parser.add_argument('-fsort', dest="SORT_PER_FILE", default="", help="Query string to sort by per sample file")
parser.add_argument('-ffilter', dest="FILTER_PER_FILE", default="", help="Query string to filter by per sample file")
parser.add_argument('-flim', dest="LIMIT_PER_FILE", default=-1, type=int, help="Target total sample count per file, -1 for everything")

parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show the stats")
parser.add_argument('-shuffle', dest="SHUFFLE", action="store_true", help="Shuffle the samples")
a = parser.parse_args()

# Read files
files = []
fromManifest = a.INPUT_FILE.endswith(".csv") and "*" not in a.INPUT_FILE
blacklist = []
if fromManifest:
    fieldNames, files = readCsv(a.INPUT_FILE)
    for i, f in enumerate(files):
        files[i]["sampleFilename"] = a.INPUT_DIR + f["filename"] + ".csv"
    blacklistFn = a.INPUT_FILE.replace(".csv", "_blacklist.csv")
    if os.path.isfile(blacklistFn):
        _, bfiles = readCsv(blacklistFn)
        if len(bfiles):
            blacklist = [b["filename"] for b in bfiles]
else:
    files = getFilenames(a.INPUT_FILE)
    files = [{"sampleFilename": f} for f in files]
fileCount = len(files)
print("Found %s files" % fileCount)

files = sortByQueryString(files, a.SORT)

if len(a.FILTER) > 0:
    files = filterByQueryString(files, a.FILTER)
    fileCount = len(files)
    print("Found %s files after filtering" % fileCount)

if len(blacklist) > 0:
    blacklist = set(blacklist)
    files = [f for f in files if f["filename"] not in blacklist]
    print("Removed %s files that were blacklisted" % (fileCount-len(files)))
    fileCount = len(files)

# check to see how many samples we should retrieve per file (if applicable)
limitPerFile = a.LIMIT_PER_FILE
if a.LIMIT > 0 and limitPerFile < 1:
    limitPerFile = roundInt(1.0 * a.LIMIT / fileCount)

allSamples = []
allFieldNames = []
for i, f in enumerate(files):
    fn = f["sampleFilename"]
    if os.path.isfile(fn):
        fieldNames, samples = readCsv(fn, verbose=False)
        allFieldNames = unionLists(allFieldNames, fieldNames)
        samples = filterByQueryString(samples, a.FILTER_PER_FILE)
        sampleCount = len(samples)
        if limitPerFile > 0 and sampleCount > limitPerFile:
            if a.SHUFFLE:
                random.seed(7)
                random.shuffle(samples)
                samples = samples[:limitPerFile]
            else:
                samples = sortByQueryString(samples, a.SORT_PER_FILE, limitPerFile)
        allSamples += samples
    printProgress(i+1, fileCount)

sampleCount = len(allSamples)
print("Found %s samples" % formatNumber(sampleCount))

if a.LIMIT > 0 and sampleCount > a.LIMIT:
    allSamples = sortByQueryString(allSamples, a.SORT_PER_FILE, a.LIMIT)
    sampleCount = len(allSamples)

if not a.PROBE:
    writeCsv(a.OUTPUT_FILE, allSamples, headings=allFieldNames)
