# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import statistics
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file pattern")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/", help="Output dir; leave blank if overwriting original files")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing audio?")
parser.add_argument('-plot', dest="PLOT", action="store_true", help="Plot the data?")
parser.add_argument('-threads', dest="THREADS", default=4, type=int, help="Number of threads")
parser.add_argument('-db', dest="TARGET_DB", default=-15, type=float, help="Target median decibels")
parser.add_argument('-mindb', dest="MIN_DB", default=-24, type=float, help="Target minumum decibels")
parser.add_argument('-maxdb', dest="MAX_DB", default=-6, type=float, help="Target maximum decibels")
parser.add_argument('-group', dest="GROUP_BY", default="", help="Group files by key; leave blank for no grouping")
a = parser.parse_args()

# Parse arguments
OVERWRITE_SELF = len(a.OUTPUT_DIR) < 1
HAS_GROUPS = len(a.GROUP_BY) > 0

if OVERWRITE_SELF and not a.OVERWRITE:
    print("Enter an output directory or add --ovewrite to overwrite self")
    sys.exit()

# Read files
fieldNames, files, fileCount = getFilesFromString(a)

fileGroups = []
if HAS_GROUPS:
    fileGroups = groupList(files, a.GROUP_BY)
else:
    fileGroups = [{ "items": files }]

def getDecibel(filename):
    audio = getAudio(filename, verbose=False)
    return audio.dBFS

plotData = []
for group in fileGroups:
    title = group[a.GROUP_BY] if HAS_GROUPS else "audio"
    print("Processing %s group..." % title)
    filenames = [item["filename"] for item in group["items"]]

    pool = ThreadPool(getThreadCount(a.THREADS))
    dbs = pool.map(getDecibel, filenames)
    pool.close()
    pool.join()

    medianDb = statistics.median(dbs)
    print("Median dB: %s" % medianDb)
    print("=====")

    if a.PLOT:
        plotData.append({
            "data": sorted(dbs),
            "median": medianDb,
            "title": title
        })

if a.PLOT:
    import numpy as np
    from matplotlib import pyplot as plt

    count = len(plotData)
    cols = 1
    rows = 1
    if count > 2:
        rows = 2
        cols = ceilInt(1.0 * count / rows )

    plt.figure(figsize = (10,6))
    for i, d in enumerate(plotData):
        ax = plt.subplot(rows, cols, i+1)
        ax.set_title(d["title"])
        y = np.array(d["data"])
        x = np.arange(len(y))
        plt.scatter(x, y, s=4)
        plt.axhline(y=d["median"], color='r', linestyle='-')

    plt.tight_layout()
    plt.show()
    sys.exit()
