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
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="32x32", help="End size of grid")
parser.add_argument('-maxcd', dest="MAX_COLUMN_DELTA", default=16, type=int, help="Max number of columns to move left and right")
parser.add_argument('-waves', dest="WAVE_COUNT", default=4, type=int, help="Number of sine waves to do")
parser.add_argument('-gridc', dest="GRID_CYCLES", default=2, type=int, help="Number of times to go through the full grid")
parser.add_argument('-duration', dest="TARGET_DURATION", default=180, type=int, help="Target duration in seconds")
parser.add_argument('-translate', dest="TRANSLATE_AMOUNT", default=0.5, type=float, help="Amount to translate clip as a percentage of height")
parser.add_argument('-rotate', dest="ROTATE_AMOUNT", default=12.0, type=float, help="Max amount to rotate clip in degrees")
parser.add_argument('-prad', dest="PLAY_RADIUS", default=8.0, type=float, help="Radius of cells/clips to play at any given time")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.8", help="Volume range")
parser.add_argument('-dpdur', dest="DELAY_PLAY_MS", default=1000, type=int, help="Don't play the first x ms of moving")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)

TARGET_DURATION_MS = roundInt(a.TARGET_DURATION * 1000)
VELOCITY_X_MAX = 0.853 # expected velocity x max

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# hack: make start and end the same; we are not zooming
visibleGridW = endGridW
visibleGridH = endGridH
containerScale = 1.0 * gridW / visibleGridW

container.vector.setTransform(scale=(containerScale, containerScale))

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

startMs = a.PAD_START
ms = startMs + TARGET_DURATION_MS
endMs = ms

def getWave(nx, waveCount):
    return math.sqrt(nx / 16.0) * math.sin(waveCount * 2.0 * math.pi * nx) if nx > 0 else 0

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
    nwave = getWave(nx, a.WAVE_COUNT)
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
        lastEntry = queue[cindex][-1]
        frameMs = lastEntry[1]
        clip = clips[cindex]
        thresholdMs = clip.props["renderDur"] * 2
        # we have passed this clip
        if (ms - frameMs) > thresholdMs:
            ndistance, playMs, xVelocity, nprogress = max(queue[cindex], key=itemgetter(0)) # get the loudest frame
            lastPlayedMs = clip.getState("lastPlayedMs")
            # check to make sure we don't play if already playing
            if lastPlayedMs is None or (playMs - lastPlayedMs) > thresholdMs:
                clip.setState("lastPlayedMs", playMs)
                # don't play the initial clips
                if playMs > (a.PAD_START + a.DELAY_PLAY_MS):
                    clip.queuePlay(playMs, {
                        "start": clip.props["audioStart"],
                        "dur": clip.props["audioDur"],
                        "volume": lerp(a.VOLUME_RANGE, ndistance),
                        "fadeOut": clip.props["fadeOut"],
                        "fadeIn": clip.props["fadeIn"],
                        "pan": clip.props["pan"],
                        "reverb": clip.props["reverb"],
                        "maxDb": clip.props["maxDb"]
                    })
                    speed = easeSinInOutBell(nprogress)
                    clipDur = roundInt(lerp((clip.props["renderDur"]*1.5, clip.props["renderDur"]*2), speed))
                    clipDur = max(1000, clipDur)
                    leftMs = roundInt(clipDur * 0.5)
                    rightMs = clipDur - leftMs

                    # offset this depending on the xoffset and y speed
                    ty = clip.props["height"] * a.TRANSLATE_AMOUNT * speed * ndistance * 2
                    xMultiplier = -1.0 * xVelocity
                    tx = clip.props["height"] * a.TRANSLATE_AMOUNT * xMultiplier * speed * ndistance
                    rotation = a.ROTATE_AMOUNT * speed * abs(xVelocity)
                    if tx > 0.0:
                        rotation *= -1.0

                    brightnessTo = lerp(a.BRIGHTNESS_RANGE, ndistance)
                    clip.queueTween(playMs, leftMs, [
                        ("brightness", a.BRIGHTNESS_RANGE[0], brightnessTo, "sin"),
                        ("translateX", 0, tx, "sin"),
                        ("translateY", 0, ty, "sin"),
                        ("rotation", 0.0, rotation, "sin")
                    ])
                    clip.queueTween(playMs+leftMs, rightMs, [
                        ("brightness", brightnessTo, a.BRIGHTNESS_RANGE[0], "sin"),
                        ("translateX", tx, 0, "sin"),
                        ("translateY", ty, 0, "sin"),
                        ("rotation", rotation, 0.0, "sin")
                    ])
            queue.pop(cindex, None)

    return queue

# determine when/which clips are playing
totalFrames = msToFrame(endMs-startMs, a.FPS)
cx = a.WIDTH * 0.5
cy = a.HEIGHT * 0.5
radius = a.PLAY_RADIUS
queue = {}
xs = []
ys = []
prevXDelta = 0
for f in range(totalFrames):
    frame = f + 1
    frameMs = startMs + frameToMs(frame, a.FPS)
    nprogress = norm(frameMs, (startMs, endMs))
    xDelta, yDelta = getPosDelta(frameMs, a.WIDTH, a.HEIGHT)
    frameCx, frameCy = (cx - xDelta, cy - yDelta) # this is the current "center"
    frameCx, frameCy = (frameCx % a.WIDTH, frameCy % a.HEIGHT) # wrap around
    gridCx, gridCy = (1.0*frameCx/a.WIDTH*gridW, 1.0 * frameCy/a.HEIGHT*gridH)

    xVelocity = xDelta - prevXDelta # this number is positive if camera moves left
    nxVelocity = lim(xVelocity / VELOCITY_X_MAX, (-1.0, 1.0))
    prevXDelta = xDelta
    # xs.append(xVelocity)
    xs.append(xDelta)
    ys.append(yDelta)

    frameClips = getNeighborClips(clips, gridCx, gridCy, gridW, gridH, radius)
    for ndistance, clip in frameClips:
        cindex = clip.props["index"]
        if ndistance > 0:
            entry = (ndistance, frameMs, xVelocity, nprogress)
            if cindex in queue:
                queue[cindex].append(entry)
            else:
                queue[cindex] = [entry]

    queue = dequeueClips(frameMs, clips, queue)

dequeueClips(endMs + frameToMs(1, a.FPS), clips, queue)

# sort frames
container.vector.sortFrames()

# import matplotlib.pyplot as plt
# ts = np.linspace(startMs/1000.0, endMs/1000.0, num=len(ys))
# plt.scatter(ts, xs, 3)
# # plt.scatter(ts, ys, 3)
# plt.show()
# # print(max(xs))
# sys.exit()

# custom clip to numpy array function to override default tweening logic
def clipToNpArrFalling(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global startMs
    global endMs

    customProps = None

    if startMs <= ms < endMs:
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
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, endMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrFalling, containsAlphaClips=True)
