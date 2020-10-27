# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import sys

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/sample/*.wav", help="Input file pattern")
parser.add_argument('-out', dest="OUT_AUDIO", default="output/sprite.mp3", help="Output audio file")
parser.add_argument('-data', dest="OUT_DATA", default="output/sprite.json", help="Output data file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display durations?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILES)

if a.PROBE:
    sys.exit()

ms = 0
pad = 10
instructions = []
jsonData = {}
for fn in filenames:
    basename = getBasename(fn)
    audio = getAudio(fn)
    dur = len(audio)
    instructions.append({
        "filename": fn,
        "start": 0,
        "dur": dur,
        "ms": ms
    })
    jsonData[basename] = [ms, dur]
    ms += pad + dur
totalDuration = ms

mixAudio(instructions, totalDuration, a.OUT_AUDIO, sfx=False)
writeJSON(a.OUT_DATA, jsonData)
