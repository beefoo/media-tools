# -*- coding: utf-8 -*-

# Instructions
# 1. Breathe in, the clips rise and play backwards
# 2. Breathe out, the clips fall and play forwards
# 3. Play similar-sounding clips on each breadth
# 4. Use real breathing data if possible

import argparse
import inspect
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
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)

parser.add_argument('-data', dest="DATA_FILE", default="../media/downloads/m002.csv", help="Path to data file generated from breathing_data.py")
parser.add_argument('-bcount', dest="BREADTH_COUNT", default=20, type=int, help="Number of breadths")
parser.add_argument('-lim', dest="LIMIT_DATA", default=120, type=int, help="Limit data in seconds, -1 if no limit")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

REDUCE_DATA = a.LIMIT_DATA * 1000
startTime = logTime()

# Read data
breathingFields, breathingData = readCsv(a.DATA_FILE, encoding=False)
stepTime = logTime(startTime, "Read breathing data")

# Get sample data
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
stepTime = logTime(stepTime, "Read samples")
if a.COUNT > 0:
    if a.COUNT <= sampleCount:
        samples = sortBy(samples, ("flatness", "asc")) # get samples with least flatness
        samples = samples[:a.COUNT]
    else:
        print("Warning: %s samples requested, but only %s found" % (a.COUNT, sampleCount))

if REDUCE_DATA > 0:
    breathingData = breathingData[:REDUCE_DATA]

# Find peaks
minima, maxima = findPeaks([d["resp"] for d in breathingData], distance=2200, height=0.0) # require at least 2.2 seconds between peaks
breadthCount = min(len(minima), len(maxima)) - 1 # subtract one because we skip the first minima
print("Found %s peaks" % breadthCount)
stepTime = logTime(stepTime, "Find peaks")

if breadthCount < a.BREADTH_COUNT:
    print("Not enough data! Found %s, but need %s breadths" % (breadthCount, a.BREADTH_COUNT))

for i, ms0 in enumerate(minima):
    # Start at second minima
    if i < 1:
        continue

    if i >= a.BREADTH_COUNT:
        break

    # Find the next maxima
    peakms = findNextValue(maxima, ms0)
    if peakms is None:
        print("Could not find maxima after %s" % formatSeconds(ms0/1000.0))
        break

    # Find next minima
    if i >= len(minima)-2:
        print("Could not find minima after %s" % formatSeconds(ms0/1000.0))
        break
    ms1 = minima[i+1]

    breadthDuration = ms1 - ms0
    breadthData = breathingData[ms0:ms1]
    print("Breadth %s duration: %sms" % (i+1, breadthDuration))

    inhaleDuration = peakms - ms0
    exhaleDuration = ms1 - peakms

    # segmentLength = 500 # look at this much time to determine velocity
    # hlen = segmentLength/2
    # for j, d in enumerate(breadthData):
    #     # correlate breathing data to velocity

logTime(startTime, "Total time")
