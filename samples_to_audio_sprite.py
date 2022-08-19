# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/samples.csv", help="Input csv file")
parser.add_argument('-dir', dest="INPUT_DIR", default="path/to/audio/", help="Directory of input audio files")
parser.add_argument('-out', dest="OUT_AUDIO", default="output/sprite.mp3", help="Output audio file")
parser.add_argument('-data', dest="OUT_DATA", default="output/sprite.json", help="Output data file")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-reverb', dest="REVERB", default=0, type=int, help="Add reverb (0-100)")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show the stats")
a = parser.parse_args()

fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
fxPad = 500
print("Found %s samples" % sampleCount)

if len(a.SORT) > 0:
    samples = sortByQueryString(samples, a.SORT)

if len(a.FILTER) > 0:
    samples = filterByQueryString(samples, a.FILTER)
    sampleCount = len(samples)
    print("%s samples after filtering" % sampleCount)

if a.LIMIT > 0 and sampleCount > a.LIMIT:
    samples = samples[:a.LIMIT]
    sampleCount = len(samples)
    print("%s samples after limiting" % sampleCount)

ms = 0
pad = 10
instructions = []
jsonData = {}
for i, s in enumerate(samples):
    fn = a.INPUT_DIR + s["filename"]
    start = s["start"]
    dur = s["dur"]
    instruction = {
        "filename": fn,
        "start": start,
        "dur": dur,
        "ms": ms
    }
    if a.REVERB > 0:
        instruction["reverb"] = a.REVERB
        dur += fxPad
    instructions.append(instruction)
    jsonData[str(i)] = [ms, dur]
    ms += pad + dur
totalDuration = ms

print("Total duration: %s" % formatSeconds(roundInt(totalDuration / 1000.0)))
if a.PROBE:
    sys.exit()

if a.REVERB > 0:
    mixAudio(instructions, totalDuration, a.OUT_AUDIO, sfx=True, fxPad=fxPad)
else:
    mixAudio(instructions, totalDuration, a.OUT_AUDIO, sfx=False)
writeJSON(a.OUT_DATA, jsonData)