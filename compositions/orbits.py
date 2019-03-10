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
parser.add_argument('-bdivision', dest="BEAT_DIVISIONS", default=4, type=int, help="Number of times to divide each beat")
parser.add_argument('-roffset', dest="ROTATION_STEPS_OFFSET", default=4, type=int, help="Number of times to rotate before going to the next ring")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["VOLUME_RANGE"] = (0.6, 1.0)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

START_RINGS = int(startGridW / 2)
END_RINGS = int(endGridW / 2)
PLAY_OFFSET = 0.375 # play at the 3 o'clock spot, halfway between 0.25 and 0.5

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

def getRingCount(ring):
    ringGridW = ring * 2
    ringGridH = ringGridW
    return ringGridW * 2 + (ringGridH-2) * 2

subbeats = 2**a.BEAT_DIVISIONS
for step in range(END_RINGS):
    ring = step + 1
    ringOffset = getOffset(subbeats, step % subbeats)
    ringOffsetMs = roundInt(ringOffset * a.BEAT_MS)
    ringStartMs = a.PAD_START + (a.ROTATION_STEPS_OFFSET * a.BEAT_MS * step) + ringOffsetMs
    ringSamples = [s for s in samples if s["ring"]==ring]
    ringSamples = sorted(ringSamples, key=ringComparison)
    rotationSteps = END_RINGS * a.ROTATION_STEPS_OFFSET
    ringCellCount = getRingCount(ring)
    if ringCellCount != len(ringSamples):
        print("Error in ring cell count: %s != %s" % (ringCellCount, len(ringSamples)))
    for j, s in enumerate(ringSamples):
        sindex = s["index"]
        samples[sindex]["ringIndex"] = j
        samples[sindex]["rotateStartMs"] = ringStartMs
        samples[sindex]["rotateDurMs"] = a.BEAT_MS
        samples[sindex]["rotateEndMs"] = ringStartMs + rotationSteps * a.BEAT_MS
        samples[sindex]["ringIndexReversed"] = (j + int(rotationSteps/2)) % ringCellCount

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

def queuePlay(clip, ms, a):
    clip.queuePlay(ms, {
        "dur": clip.props["audioDur"],
        "volume": lerp(a.VOLUME_RANGE, (1.0 - clip.props["nDistanceFromCenter"])),
        "fadeOut": clip.props["fadeOut"],
        "fadeIn": clip.props["fadeIn"],
        "pan": 0,
        "reverb": clip.props["reverb"]
    })

def getClipPlayMs(playOffset, ringCellCount, ringIndex, rotateDurMs, reversed=False):
    if reversed:
        return (((1.0-playOffset) * ringCellCount + ringIndex) % ringCellCount) * rotateDurMs
    else:
        return ((playOffset * ringCellCount - ringIndex) % ringCellCount) * rotateDurMs

# queue clip plays
for clip in clips:
    rotateStartMs = clip.props["rotateStartMs"]
    rotateEndMs = clip.props["rotateEndMs"]
    rotateReverseMs = roundInt(lerp((rotateStartMs, rotateEndMs), 0.5))
    rotateDurMs = clip.props["rotateDurMs"]
    ringIndex = clip.props["ringIndex"]
    ringCellCount = getRingCount(clip.props["ring"])
    ringDurMs = rotateDurMs * ringCellCount
    clipPlayMs = getClipPlayMs(PLAY_OFFSET, ringCellCount, ringIndex, rotateDurMs)
    # play forward until we're half way
    ms = rotateStartMs + clipPlayMs
    while ms <= rotateReverseMs:
        queuePlay(clip, ms, a)
        ms += ringDurMs

    # now play in reverse
    ringIndex = clip.props["ringIndexReversed"]
    clipPlayMs = getClipPlayMs(PLAY_OFFSET, ringCellCount, ringIndex, rotateDurMs, reversed=True)
    ms = rotateReverseMs + clipPlayMs
    while ms <= rotateEndMs:
        queuePlay(clip, ms, a)
        ms += ringDurMs

# initialize container scale
container.vector.addKeyFrame("scale", 0, fromScale)

zoomStartMs = a.PAD_START + a.BEAT_MS * START_RINGS
zoomSteps = END_RINGS-START_RINGS
scaleXs = [a.PAD_START]
scaleYs = [fromScale]
for step in range(zoomSteps):
    stepRing = START_RINGS + step + 1
    stepGridW = stepRing * 2
    stepZoomScale = 1.0 * gridW / stepGridW
    stepMs = zoomStartMs + step * a.ROTATION_STEPS_OFFSET * a.BEAT_MS
    # ease = "sin" if step > 0 else "quintIn"
    # container.vector.addKeyFrame("scale", stepMs, stepZoomScale, ease)
    scaleXs.append(stepMs)
    scaleYs.append(stepZoomScale)

ms = max([s["rotateEndMs"] for s in samples]) + a.BEAT_MS

# pprint(list(zip(scaleXs, scaleYs)))
# sys.exit()

pivot = 0.9
tweenStartMs = roundInt(lerp((scaleXs[0], scaleXs[1]), pivot))
container.queueTween(scaleXs[0], tweenStartMs-scaleXs[0], ("scale", scaleYs[0], scaleYs[1], "quadIn"))
container.queueTween(tweenStartMs, scaleXs[-1]-tweenStartMs, ("scale", scaleYs[1], scaleYs[-1], "quadOut"))

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
    global PLAY_OFFSET

    rotateStartMs = clip.props["rotateStartMs"]
    rotateEndMs = clip.props["rotateEndMs"]
    rotateReverseMs = roundInt(lerp((rotateStartMs, rotateEndMs), 0.5))
    alpha = clip.props["alpha"]
    ringProps = None

    ended = reversed = False
    _ms = ms

    # reverse half way through
    if ms > rotateReverseMs:
        reversed = True

    # freeze when we're at the end
    if ms > rotateEndMs:
        ended = True
        ms = rotateEndMs

    # only rotate if it's started already
    if ms >= rotateStartMs:
        clipW = clip.props["width"]
        clipH = clip.props["height"]
        ring = clip.props["ring"]
        rotateDurMs = clip.props["rotateDurMs"]
        ringIndex = clip.props["ringIndex"] if not reversed else clip.props["ringIndexReversed"]

        cellW = 1.0 * containerW / gridW
        cellH = 1.0 * containerH / gridH
        marginX = (cellW-clipW) * 0.5
        marginY = (cellH-clipH) * 0.5
        ringGridW = ring * 2
        ringGridH = ringGridW
        ringCellCount = getRingCount(ring)
        ringWidth = cellW * ringGridW
        ringHeight = cellH * ringGridH
        ringX = (containerW-ringWidth) * 0.5
        ringY = (containerH-ringHeight) * 0.5
        ringDurMs = rotateDurMs * ringCellCount

        if ringIndex >= ringCellCount:
            print("Error: ring index out of bounds (%s >= %s)" % (ringIndex, ringCellCount))

        elapsedMs = ms - rotateStartMs if not reversed else ms - rotateReverseMs
        msRing = elapsedMs % ringDurMs # amount of time into the progress of the rotation
        nRingProgress = 1.0 * msRing / ringDurMs # normalized progress of rotation
        cellOffset = nRingProgress * ringCellCount
        if reversed:
            cellOffset = -cellOffset
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
        clipPlayMs = getClipPlayMs(PLAY_OFFSET, ringCellCount, ringIndex, rotateDurMs, reversed=reversed)

        if clipPlayMs <= msRing < (clipPlayMs+clipDur):
            # fade out after we ended rotating
            if ended:
                elapsedAfterEnded = _ms - rotateEndMs
                if elapsedAfterEnded < clipDur:
                    msRing = (_ms - rotateReverseMs) % ringDurMs
                    msRing = lim(msRing, (clipPlayMs, clipPlayMs+clipDur))
                else:
                    msRing = clipPlayMs+clipDur
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
