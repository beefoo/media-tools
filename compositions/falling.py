# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
from operator import itemgetter
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
parser.add_argument('-maxcd', dest="MAX_COLUMN_DELTA", default=24, type=int, help="Max number of columns to move left and right")
parser.add_argument('-waves', dest="WAVE_COUNT", default=16, type=int, help="Number of sine waves to do")
parser.add_argument('-gridc', dest="GRID_CYCLES", default=16, type=int, help="Number of times to go through the full grid")
parser.add_argument('-duration', dest="TARGET_DURATION", default=120, type=int, help="Target duration in seconds")
parser.add_argument('-translate', dest="TRANSLATE_AMOUNT", default=0.33, type=float, help="Amount to translate clip as a percentage of height")
parser.add_argument('-prad', dest="PLAY_RADIUS", default=4.0, type=float, help="Radius of cells/clips to play at any given time")
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
visibleGridW = endGridW
visibleGridH = endGridH
containerScale = 1.0 * gridW / visibleGridW

container.vector.setTransform(scale=(containerScale, containerScale))

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

def getPosDelta(ms, containerW, containerH):
    global startMs
    global endMs
    global visibleGridW
    global visibleGridH
    global gridW
    global gridH
    global a

    cellW = 1.0 * containerW / gridW
    cellH = 1.0 * containerH / gridH

    nprogress = norm(ms, (startMs, endMs))
    firstHalf = (nprogress <= 0.5)

    # calculate how much we should move column from left to right along x-axis
    nx = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
    nwave = math.sqrt(nx / 16.0) * math.sin(a.WAVE_COUNT * 2.0 * math.pi * nx) if nx > 0 else 0
    if not firstHalf:
        nwave = -nwave
    waveColDelta = nwave * a.MAX_COLUMN_DELTA
    xDelta = cellW * waveColDelta

    # calculate how much we should move along the y-axis of grid
    ny = norm(nprogress, (0, 0.5)) if firstHalf else norm(nprogress, (1.0, 0.5))
    ny = ease(ny, "quadIn")
    halfGridCycles = a.GRID_CYCLES * 0.5
    ngrid = halfGridCycles * ny
    if not firstHalf:
        ngrid = halfGridCycles + halfGridCycles*(1.0-ny)
    nrow = (ngrid + 0.5) % 1
    yDelta = containerH * 0.5 - containerH * nrow

    return (xDelta, yDelta)

def dequeueClips(ms, clips, queue):
    global a

    indices = list(queue.keys())

    for cindex in indices:
        frameMs, ndistance = queue[cindex][-1]
        # we have passed this clip
        if frameMs < ms:
            ndistance, playMs = max(queue[cindex], key=itemgetter(0)) # get the loudest frame
            clip = clips[cindex]
            lastPlayedMs = clip.getState("lastPlayedMs")
            # check to make sure we don't play if already playing
            if lastPlayedMs is None or (playMs - lastPlayedMs) > clip.props["audioDur"]:
                clip.queuePlay(ms, {
                    "dur": clip.props["audioDur"],
                    "volume": lerp(a.VOLUME_RANGE, ndistance),
                    "fadeOut": clip.props["fadeOut"],
                    "fadeIn": clip.props["fadeIn"],
                    "pan": clip.props["pan"],
                    "reverb": clip.props["reverb"],
                    "matchDb": clip.props["matchDb"]
                })
                clip.queueTween(ms, clip.dur, ("alpha", a.ALPHA_RANGE[1], a.ALPHA_RANGE[0], "sin"))
                ty = clip.props["height"] * a.TRANSLATE_AMOUNT
                leftMs = roundInt(clip.dur * 0.2)
                rightMs = clip.dur - leftMs
                clip.queueTween(ms, leftMs, ("translateY", 0, ty, "sin"))
                clip.queueTween(ms+leftMs, rightMs, ("translateY", ty, 0, "sin"))
            queue.pop(cindex, None)

    return queue

def getNeighborClips(clips, frameCx, frameCy, radius):
    global gridW
    global gridH
    global a

    ccol = roundInt(frameCx)
    crow = roundInt(frameCy)
    iradius = roundInt(radius)
    halfRadius = roundInt(iradius/2)

    cols = [c+ccol-halfRadius for c in range(iradius)]
    rows = [c+crow-halfRadius for c in range(iradius)]

    frameClips = []
    for col in cols:
        for row in rows:
            # wrap around
            x = col % gridW
            y = row % gridH
            i = y * gridW + x
            clip = clips[i]
            distanceFromCenter = distance(x, y, frameCx, frameCy)
            nDistanceFromCenter = 1.0 - 1.0 * distanceFromCenter / radius
            clip.setState("nDistanceFromCenter", nDistanceFromCenter)
            frameClips.append(clip)

    return frameClips

# determine when/which clips are playing
totalFrames = msToFrame(endMs-startMs, a.FPS)
cx = a.WIDTH * 0.5
cy = a.HEIGHT * 0.5
radius = a.PLAY_RADIUS
queue = {}
for f in range(totalFrames):
    frame = f + 1
    frameMs = startMs + frameToMs(frame, a.FPS)
    xDelta, yDelta = getPosDelta(ms, a.WIDTH, a.HEIGHT)
    frameCx, frameCy = (cx - xDelta, cy - yDelta) # this is the current "center"
    frameCx, frameCy = (frameCx % a.WIDTH, frameCy % a.HEIGHT) # wrap around
    frameCx, frameCy = (1.0*frameCx/gridW, 1.0 * frameCy/gridH)

    frameClips = getNeighborClips(clips, frameCx, frameCy, radius)
    for clip in frameClips:
        cindex = clip.props["index"]
        ndistance = clip.getState("nDistanceFromCenter")
        if ndistance > 0:
            entry = (ndistance, frameMs)
            if cindex in queue:
                queue[cindex].append(entry)
            else:
                queue[cindex] = [entry]

    queue = dequeueClips(frameMs, clips, queue)
dequeueClips(endMs + frameToMs(1, a.FPS), clips, queue)


# custom clip to numpy array function to override default tweening logic
def clipToNpArrFalling(clip, ms, containerW, containerH, precision, parent):
    global startMs
    customProps = None

    if ms >= startMs:
        xDelta, yDelta = getPosDelta(ms, containerW, containerH)

        # offset the position
        x = clip.props["x"] + xDelta
        y = clip.props["y"] + yDelta

        # wrap around x and y
        x = x % containerW
        y = y % containerH

        customProps = {"pos": [x, y]}

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(props["alpha"] * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"])
    ], dtype=np.int32)

processComposition(a, clips, endMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrFalling)
