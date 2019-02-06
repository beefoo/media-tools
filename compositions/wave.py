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
parser.add_argument('-beatms', dest="BEAT_MS", default=1024, type=int, help="Milliseconds per beat")
parser.add_argument('-beats', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide beat, e.g. 1 = 1/2 notes, 2 = 1/4 notes, 3 = 1/8th notes, 4 = 1/16 notes")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.2,1.0", help="Volume range")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

# parse number sequences
VOLUME_RANGE = [float(v) for v in a.VOLUME_RANGE.strip().split(",")]
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
UNIT_MS = roundInt(2 ** (-a.BEAT_DIVISIONS) * a.BEAT_MS)
STEP_MS = a.BEAT_MS * a.STEP_BEATS
print("Smallest unit: %ss" % UNIT_MS)
print("%ss per step" % roundInt(STEP_MS/1000.0))

# Get video data
startTime = logTime()
_, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

gridCount = GRID_W * GRID_H
if gridCount > sampleCount:
    print("Not enough samples (%s) for the grid you want (%s x %s = %s). Exiting." % (sampleCount, GRID_W, GRID_H, gridCount))
    sys.exit()
elif gridCount < sampleCount:
    print("Too many samples (%s), limiting to %s" % (sampleCount, gridCount))
    samples = samples[:gridCount]

clips = samplesToClips(samples)

# get audio sequence
audioSequence = clipsToSequence(clips)
stepTime = logTime(startTime, "Processed audio clip sequence")

# plotAudioSequence(audioSequence)
# sys.exit()

currentFrame = 1

videoDurationMs = frameToMs(currentFrame, a.FPS)
audioDurationMs = getAudioSequenceDuration(audioSequence)
durationMs = max(videoDurationMs, audioDurationMs) + a.PAD_END
print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
print("Total time: %s" % formatSeconds(durationMs/1000.0))

if not a.VIDEO_ONLY and (not os.path.isfile(a.AUDIO_OUTPUT_FILE) or a.OVERWRITE):
    mixAudio(audioSequence, durationMs, a.AUDIO_OUTPUT_FILE)
    stepTime = logTime(stepTime, "Mix audio")

logTime(startTime, "Total execution time")
