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
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="32x32", help="End size of grid")
parser.add_argument('-maxcd', dest="MAX_COLUMN_DELTA", default=32, type=int, help="Max number of columns to move left and right")
parser.add_argument('-waves', dest="WAVE_COUNT", default=16, type=int, help="Number of sine waves to do")
parser.add_argument('-gridc', dest="GRID_CYCLES", default=2, type=int, help="Number of times to go through the full grid")
parser.add_argument('-duration', dest="TARGET_DURATION", default=120, type=int, help="Target duration in seconds")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["VOLUME_RANGE"] = (0.4, 0.8)

TARGET_DURATION_MS = roundInt(a.TARGET_DURATION * 1000)

# xs = np.linspace(0, 1.0, num=1000)
# ys = []
# for nprogress in xs:
#     firstHalf = nprogress <= 0.5
#     x = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
#     nwave = math.sqrt(x / 12.0) * math.sin(a.WAVE_COUNT * 2.0 * math.pi * x) if x > 0 else 0
#     if not firstHalf:
#         nwave = -nwave
#     waveColDelta = nwave * a.MAX_COLUMN_DELTA
#     ys.append(waveColDelta)
# import matplotlib.pyplot as plt
# plt.plot(xs, ys)
# plt.show()
# sys.exit()

# xs = np.linspace(0, 1.0, num=1000)
# ys = []
# for nprogress in xs:
#     firstHalf = nprogress <= 0.5
#     ny = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
#     ny = ease(ny, "cubicIn")
#     halfGridCycles = a.GRID_CYCLES * 0.5
#     ngrid = halfGridCycles * ny
#     if not firstHalf:
#         ngrid = halfGridCycles + halfGridCycles*(1.0-ny)
#     ys.append(ngrid)
# import matplotlib.pyplot as plt
# plt.plot(xs, ys)
# plt.show()
# sys.exit()

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# hack: make start and end the same; we are not zooming
startGridW = endGridW
startGridH = endGridH
containerScale = 1.0 * gridW / startGridW

container.setTransform(scale=(containerScale, containerScale))

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

startMs = a.PAD_START
ms = startMs + TARGET_DURATION_MS
endMs = ms

# custom clip to numpy array function to override default tweening logic
def clipToNpArrFalling(clip, ms, containerW, containerH, precision, parent):
    global startMs
    global endMs
    global startGridW
    global startGridH
    global gridW
    global gridH
    global a

    alpha = clip.props["alpha"]
    cellW = 1.0 * containerW / gridW
    ringProps = None
    nprogress = norm(ms, (startMs, endMs))
    firstHalf = (nprogress <= 0.5)

    # calculate how much we should move column from left to right along x-axis
    nx = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
    nwave = math.sqrt(nx / 12.0) * math.sin(a.WAVE_COUNT * 2.0 * math.pi * nx) if nx > 0 else 0
    if not firstHalf:
        nwave = -nwave
    waveColDelta = nwave * a.MAX_COLUMN_DELTA
    xDelta = cellW * waveColDelta

    # calculate how much we should move along the y-axis of grid
    ny = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
    ny = ease(ny, "cubicIn")
    halfGridCycles = a.GRID_CYCLES * 0.5
    ngrid = halfGridCycles * ny
    if not firstHalf:
        ngrid = halfGridCycles + halfGridCycles*(1.0-ny)
    nrow = (ngrid + 0.5) % 1
    yDelta = containerH * 0.5 - containerH * nrow
    # TODO: account for ends

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=ringProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(alpha * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"])
    ], dtype=np.int32)

processComposition(a, clips, ms, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrFalling)
