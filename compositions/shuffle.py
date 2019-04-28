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
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="64x64", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="32x32", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=2048, type=int, help="Duration of beat")
parser.add_argument('-bps', dest="BEATS_PER_SHUFFLE", default=8, type=int, help="Number of beats to play per shuffle")
parser.add_argument('-count', dest="SHUFFLE_COUNT", default=5, type=int, help="Number of shuffles to play")
parser.add_argument('-bdivision', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide each beat")
parser.add_argument('-transition', dest="TRANSITION_MS", default=4096, type=int, help="Duration of transition")
parser.add_argument('-mos', dest="MAX_OFFSET_STEP", default=8, type=int, help="Max offset step per shuffle")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.6,1.0", help="Volume range")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)

SUB_BEATS = 2 ** a.BEAT_DIVISIONS

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

def normalizeOffset(row, col, offsetY, offsetX, gridH, gridW):
    newRow = (row + offsetY) % gridH
    newCol = (col + offsetX) % gridW
    return (newRow, newCol)

# assign offsets per shuffle
offsetPositions = np.zeros((a.SHUFFLE_COUNT, gridH, gridW, 2), dtype=int)
shuffledIndices = np.zeros((a.SHUFFLE_COUNT, gridH, gridW), dtype=int)
shuffledIndices[0] = np.array(range(gridH*gridW)).reshape(gridH, gridW)
gridRatio = 1.0 * min(startGridW, endGridW) / gridW
for index in range(a.SHUFFLE_COUNT-1):
    i = index + 1
    prev = offsetPositions[i-1]
    for row in range(gridH):
        for col in range(gridW):
            j = row * gridW + col
            s = samples[j]
            offsetX = prev[row, col, 1]
            offsetY = prev[row, col, 0]
            prevRow, prevCol, = normalizeOffset(s["row"], s["col"], offsetY, offsetX, gridH, gridW)
            # offset vertical on even step
            if i % 2 == 0:
                # offset more as we get closer to center
                centerCol = 0.5 * (gridW-1)
                nDistanceFromCenter = lim(abs(prevCol-centerCol) / centerCol / gridRatio)
                offset = roundInt(lerp((a.MAX_OFFSET_STEP, 1), ease(nDistanceFromCenter)))
                if prevCol % 2 > 0:
                    offset = -offset
                offsetY += offset
            # offset horizontal on odd step
            else:
                # offset more as we get closer to center
                centerRow = 0.5 * (gridH-1)
                nDistanceFromCenter = lim(abs(prevRow-centerRow) / centerRow / gridRatio)
                offset = roundInt(lerp((a.MAX_OFFSET_STEP, 1), ease(nDistanceFromCenter)))
                if prevRow % 2 > 0:
                    offset = -offset
                offsetX += offset
            # store the cumulative offsets
            offsetPositions[i, row, col] = [offsetY, offsetX]
            # assign new index
            newRow, newCol = normalizeOffset(s["row"], s["col"], offsetY, offsetX, gridH, gridW)
            shuffledIndices[i, int(newRow), int(newCol)] = s["index"]

def getClipIndices(shuffledIndices, i, playRows, playCols):
    indices = shuffledIndices[i]
    clipIndices = []
    for col in playCols:
        row = playRows[col % 2]
        clipIndices.append(indices[row, col])
    return clipIndices

def playTransition(a, clips, clipMs, clipIndices, reverse=False):
    volume = a.VOLUME_RANGE[0]
    clipDur = roundInt(a.TRANSITION_MS * 1.25)
    for clipIndex in clipIndices:
        clip = clips[clipIndex]
        clip.queuePlay(clipMs, {
            "start": clip.props["audioStart"],
            "dur": clip.props["audioDur"],
            "volume": volume,
            "fadeOut": clip.props["fadeOut"],
            "fadeIn": clip.props["fadeIn"],
            "pan": clip.props["pan"],
            "reverb": clip.props["reverb"],
            "matchDb": clip.props["matchDb"],
            "stretchTo": clipDur,
            "reverse": reverse
        })
        leftMs = roundInt(clipDur * 0.2)
        rightMs = clipDur - leftMs
        clip.queueTween(clipMs, leftMs, [
            ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin")
        ])
        clip.queueTween(clipMs+leftMs, rightMs, [
            ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
        ])

shuffleDur = a.BEATS_PER_SHUFFLE * a.BEAT_MS
subBeatDur = roundInt(1.0 * a.BEAT_MS / SUB_BEATS)
cRow = roundInt(gridH * 0.5)
playRows = [cRow-1, cRow]
colOffset = roundInt((gridW - SUB_BEATS) * 0.5)
playCols = [colOffset+i for i in range(SUB_BEATS)]
for i in range(a.SHUFFLE_COUNT):
    clipIndices = getClipIndices(shuffledIndices, i, playRows, playCols)
    # pprint(clipIndices)
    # print("-----")
    for beat in range(a.BEATS_PER_SHUFFLE):
        for subbeat in range(SUB_BEATS):
            clipMs = a.PAD_START + shuffleDur * i + a.TRANSITION_MS * i + beat * a.BEAT_MS + subbeat * subBeatDur
            clipMs = roundInt(clipMs)
            clipIndex = clipIndices[subbeat]
            clip = clips[clipIndex]
            volume = a.VOLUME_RANGE[(subbeat+1) % 2]
            # play clip
            clip.queuePlay(clipMs, {
                "start": clip.props["audioStart"],
                "dur": clip.props["audioDur"],
                "volume": volume,
                "fadeOut": clip.props["fadeOut"],
                "fadeIn": clip.props["fadeIn"],
                "pan": clip.props["pan"],
                "reverb": clip.props["reverb"],
                "matchDb": clip.props["matchDb"]
            })
            leftMs = roundInt(clip.props["renderDur"] * 0.2)
            rightMs = clip.props["renderDur"] - leftMs
            clip.queueTween(clipMs, leftMs, [
                ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin")
            ])
            clip.queueTween(clipMs+leftMs, rightMs, [
                ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
            ])
    # play stetched during the transition
    if i < a.SHUFFLE_COUNT-1:
        clipMs = a.PAD_START + shuffleDur * (i+1) + a.TRANSITION_MS * i
        playTransition(a, clips, clipMs, clipIndices)

startMs = a.PAD_START
shuffleMs = (shuffleDur + a.TRANSITION_MS) * a.SHUFFLE_COUNT - a.TRANSITION_MS
reverseMs = a.TRANSITION_MS * (a.SHUFFLE_COUNT-1)

# reverse the shuffles
for index in range(a.SHUFFLE_COUNT-1):
    i = a.SHUFFLE_COUNT - 1 - index
    clipIndices = getClipIndices(shuffledIndices, i, playRows, playCols)
    clipMs = startMs + shuffleMs + index * a.TRANSITION_MS
    playTransition(a, clips, clipMs, clipIndices, reverse=True)

zoomDur = roundInt(shuffleMs * 0.5)
container.queueTween(startMs, zoomDur, ("scale", fromScale, toScale, "cubicInOut"))
durationMs = startMs + shuffleMs + reverseMs

stepTime = logTime(stepTime, "Create plays/tweens")

# sort frames
container.vector.sortFrames()

# custom clip to numpy array function to override default tweening logic
def clipToNpArrShuffle(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global startMs
    global durationMs
    global shuffleMs
    global shuffleDur
    global offsetPositions
    global gridW
    global gridH

    customProps = None
    crow = clip.props["row"]
    ccol = clip.props["col"]
    cellW = 1.0 * a.WIDTH / gridW
    cellH = 1.0 * a.HEIGHT / gridH
    margin = a.CLIP_MARGIN * cellW * 0.5

    # we are in the main shuffling stage
    if startMs <= ms < (startMs+shuffleMs):
        nprogress = norm(ms, (startMs, startMs+shuffleMs+a.TRANSITION_MS)) # need to add one more TRANSITION_MS to calculate progress correctly
        fshuffle = a.SHUFFLE_COUNT * nprogress
        shuffleIndex = min(floorInt(fshuffle), a.SHUFFLE_COUNT-1)
        nshuffle = lim(fshuffle - shuffleIndex) # progress within current shuffle
        transitionThreshold = 1.0 * shuffleDur / (shuffleDur + a.TRANSITION_MS) # threshold within nshuffle to start transitioning

        offsetY, offsetX = tuple(offsetPositions[shuffleIndex, crow, ccol])
        newRow, newCol = normalizeOffset(crow, ccol, offsetY, offsetX, gridH, gridW)

        # we are transitioning to the next shuffle; don't transition if last shuffle
        if nshuffle > transitionThreshold and shuffleIndex < a.SHUFFLE_COUNT-1:
            ntransition = norm(nshuffle, (transitionThreshold, 1.0), limit=True)
            toOffsetY, toOffsetX = tuple(offsetPositions[shuffleIndex+1, crow, ccol])
            deltaOffsetY, deltaOffsetX = (toOffsetY-offsetY, toOffsetX-offsetX) # amount we move from previous positions
            fromRow, fromCol = (newRow, newCol) # previous positions
            newRow, newCol = (lerp((fromRow, fromRow+deltaOffsetY), ease(ntransition)), lerp((fromCol, fromCol+deltaOffsetX), ease(ntransition)))
            newRow, newCol = (newRow % gridH, newCol % gridW)

        x = newCol * cellW + margin
        y = newRow * cellH + margin
        customProps = {"pos": [x, y]}

    # we are reverse transitioning
    elif ms >= (startMs+shuffleMs):
        nprogress = norm(ms, (startMs+shuffleMs, durationMs))
        fshuffle = (a.SHUFFLE_COUNT-1) * (1.0-nprogress)
        shuffleIndex = lim(ceilInt(fshuffle), (1, a.SHUFFLE_COUNT-1))
        ntransition = lim(shuffleIndex - fshuffle) # progress within current transition

        offsetY, offsetX = tuple(offsetPositions[shuffleIndex, crow, ccol])
        toOffsetY, toOffsetX = tuple(offsetPositions[shuffleIndex-1, crow, ccol])
        deltaOffsetY, deltaOffsetX = (toOffsetY-offsetY, toOffsetX-offsetX) # amount we move from previous positions
        fromRow, fromCol = normalizeOffset(crow, ccol, offsetY, offsetX, gridH, gridW)
        newRow, newCol = (lerp((fromRow, fromRow+deltaOffsetY), ease(ntransition)), lerp((fromCol, fromCol+deltaOffsetX), ease(ntransition)))
        newRow, newCol = (newRow % gridH, newCol % gridW)

        x = newCol * cellW + margin
        y = newRow * cellH + margin
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

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrShuffle)
