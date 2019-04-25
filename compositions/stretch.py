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
parser.add_argument('-grid0', dest="START_GRID", default="32x32", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.4,0.8", help="Volume range")
parser.add_argument('-sdur', dest="STRETCH_DURATION", default=16384, type=int, help="How long it takes to stretech to full height")
parser.add_argument('-stms', dest="STRETCH_TO_MS", default=8192, type=int, help="Target stretch duration")
parser.add_argument('-step', dest="STEP_MS", default=2048, type=int, help="Start next clips after this amount of time")
a = parser.parse_args()
parseVideoArgs(a)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# start with everything with minimum brightness
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

steps = roundInt(endGridH * 0.5)
startMs = a.PAD_START
stretchMs = (steps-1) * a.STEP_MS + a.STRETCH_DURATION * 2 # 2x to shrink back down to normal size
zoomDur = roundInt(stretchMs * 0.5)
fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
container.queueTween(startMs, zoomDur, ("scale", fromScale, toScale, "cubicInOut"))
durationMs = startMs + stretchMs

def stretchAndPlayClip(a, clips, ms, row, col, gridW):
    index = row * gridW + col
    clip = clips[index]
    clip.setState("isPlayable", True)
    audioDur = clip.props["audioDur"]
    targetStretch = 1.0 * a.STRETCH_TO_MS / audioDur
    progress = 0.0
    elapsedMs = 0
    while progress <= 1.0:
        volume = lerp(a.VOLUME_RANGE, 1.0-progress)
        stretchAmount = lerp((1.0, targetStretch), progress)
        clipMs = ms + elapsedMs
        clip.queuePlay(clipMs, {
            "start": clip.props["audioStart"],
            "dur": clip.props["audioDur"],
            "volume": volume,
            "fadeOut": clip.props["fadeOut"],
            "fadeIn": clip.props["fadeIn"],
            "pan": clip.props["pan"],
            "reverb": clip.props["reverb"],
            "matchDb": clip.props["matchDb"],
            "stretch": stretchAmount
        })
        clipDur = roundInt(audioDur * stretchAmount)
        leftMs = roundInt(clipDur * 0.2)
        rightMs = clipDur - leftMs
        clip.queueTween(clipMs, leftMs, [
            ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin")
        ])
        clip.queueTween(clipMs+leftMs, rightMs, [
            ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
        ])
        elapsedMs += clipDur
        progress = 1.0 * elapsedMs / a.STRETCH_DURATION
    # queue stretch in/out
    clipScaleTo = 1.0 * a.HEIGHT / clip.props["height"]
    clip.queueTween(ms, a.STRETCH_DURATION, ("scaleY", 1.0, clipScaleTo, "quadInOut"))
    clip.queueTween(ms+a.STRETCH_DURATION, a.STRETCH_DURATION, ("scaleY", clipScaleTo, 1.0, "quadInOut"))

# stretch and play the middle row of clips
rowIndex = floorInt((gridH-1) * 0.5)
midCol = (gridW-1) * 0.5
for i in range(steps):
    clipMs = startMs + i * a.STEP_MS
    colLeft = floorInt(midCol) - i
    colRight = ceilInt(midCol) + i
    stretchAndPlayClip(a, clips, clipMs, rowIndex, colLeft, gridW)
    stretchAndPlayClip(a, clips, clipMs, rowIndex, colRight, gridW)

# move the rest of the clips out of the way as the middle row stretches
midRow = (gridH-1) * 0.5
deltaY = (a.HEIGHT - clips[0].props["height"]) * 0.5
for clip in clips:
    if clip.getState("isPlayable"):
        continue

    col = clip.props["col"]
    step = floorInt(midCol) - col if col < midCol else col - ceilInt(midCol)
    clipMs = startMs + step * a.STEP_MS

    row = clip.props["row"]
    translateYTo = deltaY if row > midRow else -deltaY

    clip.queueTween(clipMs, a.STRETCH_DURATION, ("translateY", 0, translateYTo, "quadInOut"))
    clip.queueTween(clipMs+a.STRETCH_DURATION, a.STRETCH_DURATION, ("translateY", translateYTo, 0, "quadInOut"))

# sort frames
container.vector.sortFrames()
stepTime = logTime(stepTime, "Created video clip sequence")

processComposition(a, clips, durationMs, sampler, stepTime, startTime)
