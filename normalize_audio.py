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
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/normalize/", help="Output dir")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing audio?")
parser.add_argument('-plot', dest="PLOT", action="store_true", help="Plot the data?")
parser.add_argument('-threads', dest="THREADS", default=4, type=int, help="Number of threads")
parser.add_argument('-db', dest="TARGET_DB", default=-14, type=float, help="Target median decibels")
parser.add_argument('-mindb', dest="MIN_DB", default=-22, type=float, help="Target minimum decibels")
parser.add_argument('-maxdb', dest="MAX_DB", default=-6, type=float, help="Target maximum decibels")
parser.add_argument('-group', dest="GROUP_BY", default="", help="Group files by key; leave blank for no grouping")
a = parser.parse_args()

# Parse arguments
HAS_GROUPS = len(a.GROUP_BY) > 0

if a.MEDIA_DIRECTORY == a.OUTPUT_DIR:
    print("Input and output directory cannot be the same")
    sys.exit()

makeDirectories(a.OUTPUT_DIR)

# Read files
fieldNames, files, fileCount = getFilesFromString(a)

fileGroups = []
if HAS_GROUPS:
    fileGroups = groupList(files, a.GROUP_BY)
else:
    fileGroups = [{ "items": files }]

def getDecibel(p):
    index, filename = p
    audio = getAudio(filename, verbose=False)
    return (index, audio.dBFS)

plotData = []
convertProps = []
for i, group in enumerate(fileGroups):
    title = group[a.GROUP_BY] if HAS_GROUPS else "audio"
    print("Processing %s group..." % title)
    itemprops = [(j, item["filename"]) for j, item in enumerate(group["items"])]

    pool = ThreadPool(getThreadCount(a.THREADS))
    results = pool.map(getDecibel, itemprops)
    pool.close()
    pool.join()

    medianDb = statistics.median([r[1] for r in results])
    print("Median dB: %s" % medianDb)
    print("=====")

    for j, db in results:
        deltaDb = db - medianDb
        targetDb = a.TARGET_DB + deltaDb
        targetDb = lim(targetDb, (a.MIN_DB, a.MAX_DB))
        sourceFile = group["items"][j]["filename"]
        destFile = a.OUTPUT_DIR + os.path.basename(sourceFile)
        convertProps.append((sourceFile, targetDb, destFile))

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

def changeVolume(p):
    sourceFile, targetDb, destFile = p
    audio = getAudio(sourceFile, verbose=False)
    audio = matchDb(audio, targetDb)
    format = destFile.split(".")[-1]
    audio.export(destFile, format=format)

print("Converting audio...")
pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(changeVolume, convertProps)
pool.close()
pool.join()
print("Done.")
