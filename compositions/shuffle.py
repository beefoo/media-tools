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
parser.add_argument('-count', dest="SHUFFLE_COUNT", default=8, type=int, help="Number of shuffles to play")
parser.add_argument('-bdivision', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide each beat")
parser.add_argument('-transition', dest="TRANSITION_MS", default=2048, type=int, help="Duration of transition")
parser.add_argument('-mos', dest="MAX_OFFSET_STEP", default=32, type=int, help="Max offset step per shuffle")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.6,0.8", help="Volume range")
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

# assign offsets per shuffle
offsetPositions = np.zeros((a.SHUFFLE_COUNT, gridH, gridW, 2), dtype=int)
shuffledIndices = np.zeros((a.SHUFFLE_COUNT, gridH, gridW), dtype=int)
shuffledIndices[0] = np.array(range(gridH*gridW)).reshape(gridH, gridW)
for index in range(a.SHUFFLE_COUNT-1):
    i = index + 1
    prev = offsetPositions[i-1]
    for row in range(gridH):
        for col in range(gridW):
            j = row * gridW + col
            s = samples[j]

            offsetX = prev[row, col, 1]
            offsetY = prev[row, col, 0]
            prevRow = (s["row"] + offsetY) % gridH
            prevCol = (s["col"] + offsetX) % gridW
            # offset vertical on even step
            if i % 2 == 0:
                # offset more as we get closer to center
                centerCol = 0.5 * (gridW-1)
                nDistanceFromCenter = abs(prevCol-centerCol) / centerCol
                offset = roundInt(lerp((a.MAX_OFFSET_STEP, 1), ease(nDistanceFromCenter)))
                if prevCol % 2 > 0:
                    offset = -offset
                offsetY += offset
            # offset horizontal on odd step
            else:
                # offset more as we get closer to center
                centerRow = 0.5 * (gridH-1)
                nDistanceFromCenter = abs(prevRow-centerRow) / centerRow
                offset = roundInt(lerp((a.MAX_OFFSET_STEP, 1), ease(nDistanceFromCenter)))
                if prevRow % 2 > 0:
                    offset = -offset
                offsetX += offset
            # store the cumulative offsets
            offsetPositions[i, row, col] = [offsetY, offsetX]
            # assign new index
            newRow = (s["row"] + offsetY) % gridH
            newCol = (s["col"] + offsetX) % gridW
            shuffledIndices[i, int(newRow), int(newCol)] = s["index"]

shuffleDur = a.BEATS_PER_SHUFFLE * a.BEAT_MS
subBeatDur = roundInt(1.0 * a.BEAT_MS / SUB_BEATS)
cRow = roundInt(gridH * 0.5)
playRows = [cRow-1, cRow]
colOffset = roundInt((gridW - SUB_BEATS) * 0.5)
playCols = [colOffset+i for i in range(SUB_BEATS)]
for i in range(a.SHUFFLE_COUNT):
    indices = shuffledIndices[i]
    clipIndices = []
    for col in playCols:
        row = playRows[col % 2]
        clipIndices.append(indices[row, col])
    pprint(clipIndices)
    print("-----")
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
                ("brightness", 0, a.BRIGHTNESS_RANGE[1], "sin")
            ])
            clip.queueTween(clipMs+leftMs, rightMs, [
                ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
            ])

zoomDur = roundInt(shuffleDur * a.SHUFFLE_COUNT * 0.5)
container.queueTween(a.PAD_START, zoomDur, ("scale", fromScale, toScale, "cubicInOut"))
durationMs = a.PAD_START + shuffleDur * a.SHUFFLE_COUNT

stepTime = logTime(stepTime, "Create plays/tweens")

# sort frames
container.vector.sortFrames()

# custom clip to numpy array function to override default tweening logic
def clipToNpArrShuffle(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    customProps = None
    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(_ms, containerW, containerH, parent, customProps=customProps)

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
