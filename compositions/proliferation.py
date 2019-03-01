# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="16x16", help="Size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="256x256", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=4096, type=int, help="Duration of beat")

a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
START_GRID_W, START_GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
END_GRID_W, END_GRID_H = tuple([int(v) for v in a.END_GRID.strip().split("x")])
GRID_W, GRID_H = (max(START_GRID_W, END_GRID_W), max(START_GRID_H, END_GRID_H))
ZOOM_EASE = "cubicIn"

fromScale = 1.0 * GRID_W / START_GRID_W
toScale = 1.0 * GRID_W / END_GRID_W

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime = initGridComposition(a, GRID_W, GRID_H, stepTime)

cCol, cRow = ((GRID_W-1) * 0.5, (GRID_H-1) * 0.5)
for i, s in enumerate(samples):
    # make clip longer if necessary
    samples[i]["audioDur"] = s["dur"]
    samples[i]["dur"] = s["dur"] if s["dur"] > a.MIN_CLIP_DUR else int(math.ceil(1.0 * a.MIN_CLIP_DUR / s["dur"]) * s["dur"])
    samples[i]["distanceFromCenter"] = distance(cCol, cRow, s["col"], s["row"])
samples = sorted(samples, key=lambda s: (s["distanceFromCenter"], -s["clarity"]))

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# queue the middle four
playedIndices = set([])
queuedIndices = set([c.props["index"] for c in clips[:4]])
clips = sorted(clips, key=lambda c: c.props["index"])

ms = a.PAD_START

while len(queuedIndices) > 0:
    if len(queuedIndices) > 0:

        # play the next clip in queue

        # after playing, add the closest neighbor not played to queue

        # remove from queue and put in played

        pass # TODO

    break

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

processComposition(a, clips, ms, sampler, stepTime, startTime)
