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
parser.add_argument('-grid0', dest="START_GRID", default="32x32", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="64x64", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=1024, type=int, help="Duration of beat")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=-1, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=-1, type=int, help="Ensure the middle x audio files play")
parser.add_argument('-bdivision', dest="BEAT_DIVISIONS", default=4, type=int, help="Number of times to divide each beat")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

START_RINGS = int(startGridW / 2)
END_RINGS = int(endGridW / 2)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]
    samples[i]["ring"] = getRing(s["col"], s["row"], cCol, cRow)

def ringComparison(s):
    x = s["col"]
    y = s["row"]
    if x >= y:
        return (0, x, y)
    else:
        return (1, -x, -y)

subbeats = 2**a.BEAT_DIVISIONS
for step in range(END_RINGS):
    ring = step + 1
    ringOffset = getOffset(subbeats, step % subbeats)
    ringOffsetMs = roundInt(ringOffset * a.BEAT_MS)
    print(ringOffsetMs)
    ringStartMs = a.PAD_START + step * a.BEAT_MS + ringOffsetMs
    ringSamples = [s for s in samples if s["ring"]==ring]
    ringSamples = sorted(ringSamples, key=ringComparison)
    for j, s in enumerate(ringSamples):
        sindex = s["index"]
        samples[sindex]["ringIndex"] = j
        samples[sindex]["rotateStartMs"] = ringStartMs
        samples[sindex]["rotateDurMs"] = a.BEAT_MS

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# initialize container scale
container.vector.addKeyFrame("scale", 0, fromScale)

zoomStartMs = a.PAD_START + a.BEAT_MS * START_RINGS
ms = zoomStartMs
zoomSteps = END_RINGS-START_RINGS
scaleXs = [a.PAD_START]
scaleYs = [fromScale]
for step in range(zoomSteps):
    stepRing = START_RINGS + step + 1
    stepGridW = stepRing * 2
    stepZoomScale = 1.0 * gridW / stepGridW
    stepMs = zoomStartMs + step * a.BEAT_MS
    # ease = "sin" if step > 0 else "quintIn"
    # container.vector.addKeyFrame("scale", stepMs, stepZoomScale, ease)
    scaleXs.append(stepMs)
    scaleYs.append(stepZoomScale)
    ms += a.BEAT_MS

# pprint(list(zip(scaleXs, scaleYs)))
# sys.exit()

# # tween container zoom between first two keyframes
# container.queueTween(scaleXs[0], scaleXs[2]-scaleXs[0], ("scale", scaleYs[0], scaleYs[2], "cubicIn"))
#
# # tween container zoom from second to last keyframe
# container.queueTween(scaleXs[2], scaleXs[-1]-scaleXs[2], ("scale", scaleYs[2], scaleYs[-1], "cubicOut"))

tweenStartMs = roundInt(lerp((scaleXs[0], scaleXs[1]), 0.5))
container.queueTween(tweenStartMs, scaleXs[-1]-tweenStartMs, ("scale", scaleYs[0], scaleYs[-1], "sin"))

# See how well the data maps to the tweened data
# container.vector.plotKeyframes("scale", additionalPlots=[([x/1000.0 for x in scaleXs], scaleYs)])
# sys.exit()

stepTime = logTime(stepTime, "Create plays/tweens")

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

def getRingCellPos(index, count, ringX, ringY, cellW, cellH):
    index = index % count
    x = ringX
    y = ringY
    quarter = int(count/4)
    half = int(count/2)
    threeQuarters = int(count*3/4)
    if index <= quarter:
        x = ringX + index * cellW
    elif index <= half:
        x = ringX + cellW * quarter
        y = ringY + cellH * (index-quarter)
    elif index <= threeQuarters:
        x = ringX + (threeQuarters-index) * cellW
        y = ringY + cellH * quarter
    else:
        y = ringY + (count-index) * cellH
    return (x, y)

# custom clip to numpy array function to override default tweening logic
def clipToNpArrOrbits(clip, ms, containerW, containerH, precision, parent):
    global gridW
    global gridH
    rotateStartMs = clip.props["rotateStartMs"]
    alpha = clip.props["alpha"]
    ringProps = None

    # only rotate if it's started already
    if ms >= rotateStartMs:
        clipW = clip.props["width"]
        clipH = clip.props["height"]
        ring = clip.props["ring"]
        rotateDurMs = clip.props["rotateDurMs"]
        ringIndex = clip.props["ringIndex"]

        cellW = 1.0 * containerW / gridW
        cellH = 1.0 * containerH / gridH
        marginX = (cellW-clipW) * 0.5
        marginY = (cellH-clipH) * 0.5
        ringGridW = ring * 2
        ringGridH = ringGridW
        ringCellCount = ringGridW * 2 + (ringGridH-2) * 2
        ringWidth = cellW * ringGridW
        ringHeight = cellH * ringGridH
        ringX = (containerW-ringWidth) * 0.5
        ringY = (containerH-ringHeight) * 0.5
        ringDurMs = rotateDurMs * ringCellCount

        if ringIndex >= ringCellCount:
            print("Error: ring index out of bounds (%s >= %s)" % (ringIndex, ringCellCount))

        elapsedMs = ms - rotateStartMs
        msRing = elapsedMs % ringDurMs # amount of time into the progress of the rotation
        nRingProgress = 1.0 * msRing / ringDurMs # normalized progress of rotation
        cellOffset = nRingProgress * ringCellCount
        currentIndex = (1.0 * ringIndex + cellOffset) % ringCellCount # current cell index in the ring

        # lerp between two cell spaces
        i0 = floorInt(currentIndex)
        i1 = ceilInt(currentIndex)
        lerpValue = currentIndex - i0
        lerpValue = ease(lerpValue, "cubicInOut")
        x0, y0 = getRingCellPos(i0, ringCellCount, ringX, ringY, cellW, cellH)
        x1, y1 = getRingCellPos(i1, ringCellCount, ringX, ringY, cellW, cellH)
        x = lerp((x0, x1), lerpValue) + marginX
        y = lerp((y0, y1), lerpValue) + marginY
        ringProps = {"pos": [x, y]}

        # determine alpha based on if clip is currently playing (when it crosses the 3-o'clock position)
        clipDur = clip.dur
        clipPlayMs = (0.375 * ringCellCount - ringIndex) * rotateDurMs
        if clipPlayMs < 0:
            clipPlayMs = ringDurMs + clipPlayMs
        if clipPlayMs <= msRing < (clipPlayMs+clipDur):
            nalpha = 1.0 - norm(msRing, (clipPlayMs, clipPlayMs+clipDur))
            alpha = lerp((alpha, 1.0), nalpha)

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

processComposition(a, clips, ms, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrOrbits)
