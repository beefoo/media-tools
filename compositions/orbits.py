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
parser.add_argument('-grid', dest="GRID", default="32x32", help="Size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="256x256", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=1024, type=int, help="Duration of beat")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=-1, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=-1, type=int, help="Ensure the middle x audio files play")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
START_GRID_W, START_GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
END_GRID_W, END_GRID_H = tuple([int(v) for v in a.END_GRID.strip().split("x")])
GRID_W, GRID_H = (max(START_GRID_W, END_GRID_W), max(START_GRID_H, END_GRID_H))

START_RINGS = int(START_GRID_W / 2)
END_RINGS = int(END_GRID_W / 2)

fromScale = 1.0 * GRID_W / START_GRID_W
toScale = 1.0 * GRID_W / END_GRID_W

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow = initGridComposition(a, GRID_W, GRID_H, stepTime)

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# initialize container scale
container.vector.setTransform(scale=(fromScale, fromScale))
container.vector.addKeyFrame("scale", 0, fromScale, "sin")

ms = a.PAD_START
zoomStartMs = ms + a.BEAT_MS * START_RINGS
ms = zoomStartMs
zoomSteps = END_RINGS-START_RINGS
for step in range(zoomSteps):
    stepRing = START_RINGS + step + 1
    stepGridW = stepRing * 2
    stepZoomScale = 1.0 * GRID_W / stepGridW
    stepMs = zoomStartMs + step * a.BEAT_MS
    container.vector.addKeyFrame("scale", stepMs, stepZoomScale, "sin")
    ms += a.BEAT_MS

stepTime = logTime(stepTime, "Create plays/tweens")

container.vector.setTransform(scale=(1.0, 1.0))
# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

processComposition(a, clips, ms, sampler, stepTime, startTime)
