# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-sdir', dest="SAMPLE_DATA_DIR", default="tmp/", help="Directory of sample data")
parser.add_argument('-buf', dest="BUFFER_SIZE", default=256, type=int, help="Max number of samples in buffer at any given time")
parser.add_argument('-unit', dest="SAMPLE_UNIT", default=16, type=int, help="Rate at which to add/remove samples to/from buffer")
parser.add_argument('-ng', dest="NOTE_GROUPS", default=4, type=int, help="Number of note groups in buffer")
parser.add_argument('-vfilter', dest="FILTER_VIDEOS", default="samples>500&medianPower>0.5", help="Query string to filter videos by")
parser.add_argument('-filter', dest="FILTER", default="power>0&octave>=0", help="Query string to filter samples by")
parser.add_argument('-sort', dest="SORT", default="power=desc=0.5&clarity=desc", help="Query string to sort samples by")
parser.add_argument('-ptl', dest="PERCENTILE", default=0.2, type=float, help="Top percentile of samples to select from each film")
parser.add_argument('-lim', dest="LIMIT", default=100, type=int, help="Limit number of samples per film")
parser.add_argument('-beats', dest="BEATS_PER_MEASURE", default=16, type=int, help="Number of beats per measure")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

# Get video data
startTime = logTime()
_, videos = readCsv(a.INPUT_FILE)

# Filter videos
videos = filterByQueryString(videos, a.FILTER_VIDEOS)
videoCount = len(videos)
print("%s videos after filtering" % videoCount)

# Sort videos such that films with the greatest volume will be in the middle
videos = sortBy(videos, ("medianPower", "asc"))
maxPower = max([v["medianPower"] for v in videos])
videos = addIndices(videos)
videos = sorted(videos, key=lambda v: v["medianPower"] if v["index"] % 2 == 0 else -v["medianPower"]+maxPower*2)
currentVideoIndex = 0

# from matplotlib import pyplot as plt
# plt.plot(range(len(videos)), [v["medianPower"] for v in videos])
# plt.show()

def fillQueue(q):
    global a
    global currentVideoIndex
    global videos
    global videoCount

    if currentVideoIndex >= videoCount:
        return q

    while len(q) < a.SAMPLE_UNIT and currentVideoIndex < videoCount:
        v = videos[currentVideoIndex]
        currentVideoIndex += 1
        # read samples
        sampleDataFilename = a.SAMPLE_DATA_DIR + v["filename"] + ".csv"
        _, samples = readCsv(sampleDataFilename)
        # filter, sort, and limit
        samples = filterByQueryString(samples, a.FILTER)
        samples = sortByQueryString(samples, a.SORT)
        sampleCount = len(samples)
        targetLen = min(a.LIMIT, parseInt(sampleCount * a.PERCENTILE))
        if targetLen <= 0:
            samples = []
        else:
            samples = samples[:targetLen]
        # add samples to queue
        q += samples

    return q

def addToBuffer(samples, buf, size):
    bufSize = len(buf)
    sampleCount = len(samples)
    totalSize = bufSize + sampleCount
    delta = totalSize - size

    buf += samples
    if delta > 0:
        buf = buf[delta:]

    return buf

def removeFromBuffer(sampleCount, buf):
    bufSize = len(buf)
    if bufSize > sampleCount:
        return buf[sampleCount:]
    else:
        return []

def playMeasure(startMs, buf):
    global a

    # Group samples by notes
    noteGroups = groupList(buff, "note")

    # Sort by group size
    noteGroups = sorted(noteGroups, key=lambda g: g["count"], reverse=True)

    # Limit the number of groups
    if len(noteGroups) > a.NOTE_GROUPS:
        noteGroups = noteGroups[:a.NOTE_GROUPS]

    # Group notes by octave
    for i, group in enumerate(noteGroups):
        octaveGroups = groupList(group["items"], "octave")

        # Sort by octave
        octaveGroups = sorted(octaveGroups, key=lambda g: g["octave"])

        noteGroups[i]["octaveCount"] = len(octaveGroups)
        noteGroups[i]["groups"] = octaveGroups

    # Make the beat unit the median duration of samples in buffer
    beatMs = np.median([s["dur"] for s in buf])

    ms = startMs
    for i in range(a.BEATS_PER_MEASURE):

        ms += beatMs

    return ms

buffer = []
queue = fillQueue(queue)
ms = 0

# Each step in this loop is considered a "measure"
while True:
    # Retrieve samples from queue
    samplesToAdd, queue = dequeue(queue, a.SAMPLE_UNIT)

    # add samples to buffer
    if len(samplesToAdd) > 0:
        buffer = addToBuffer(samplesToAdd, buffer, a.BUFFER_SIZE)

    # if no more samples, start removing samples from buffer
    else:
        buffer = removeFromBuffer(a.SAMPLE_UNIT, buffer)
        # buffer is empty, we're done
        if len(buffer) <= 0:
            break

    ms = playMeasure(ms, buffer)

    # Attempt to fill queue with more samples
    queue = fillQueue(queue)
