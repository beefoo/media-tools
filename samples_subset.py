# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
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

parser.add_argument('-stats', dest="JUST_STATS", default=0, type=int, help="Just show the stats")
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

files = sortByQueryString(files, a.SORT)

if len(a.FILTER) > 0:
    files = filterByQueryString(files, a.FILTER)
    fileCount = len(files)
    print("Found %s files after filtering" % fileCount)

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
            samples = sortByQueryString(samples, a.SORT_PER_FILE, limitPerFile)
        allSamples += samples
    printProgress(i+1, fileCount)

sampleCount = len(allSamples)
print("Found %s samples" % formatNumber(sampleCount))

if a.LIMIT > 0 and sampleCount > a.LIMIT:
    allSamples = sortByQueryString(allSamples, a.SORT_PER_FILE, a.LIMIT)
    sampleCount = len(allSamples)

if a.JUST_STATS < 1:
    writeCsv(a.OUTPUT_FILE, allSamples, headings=allFieldNames)
