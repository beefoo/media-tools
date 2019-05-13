# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.cache_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-sdur', dest="STEP_MS", default=8192, type=int, help="Duration per step")
parser.add_argument('-shdur', dest="SHRINK_DUR", default="256,1024", help="Duration range to shrink a clip in ms")
parser.add_argument('-rstep', dest="RESIZE_STEP", default=2, type=int, help="Amount to resize clip per step in pixels at 1920px width")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.8", help="Volume range")
parser.add_argument('-cdur', dest="CLIP_DUR", default=128, type=int, help="Target clip play duration")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["INVERT_LOUDEST"] = True
aa["MAX_AUDIO_CLIPS"] = 8192
aa["RESIZE_STEP"] = a.RESIZE_STEP * (a.WIDTH / 1920.0)
aa["SHRINK_DUR"] = tuple([int(f) for f in a.SHRINK_DUR.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)
    shrinkDurMs = lerp(a.SHRINK_DUR, ease(1.0-clip.props["nDistanceFromCenter"]))
    deltaMs = a.STEP_MS - shrinkDurMs
    angleFromCenter = angleBetween(cCol, cRow, clip.props["col"], clip.props["row"])
    shrinkStartMs = lerp((0, deltaMs), (angleFromCenter % 360.0)/360.0)
    clip.setState("shrinkStartMs", shrinkStartMs)
    clip.setState("shrinkEndMs", shrinkStartMs+shrinkDurMs)

clipW = clips[0].props["width"]
steps = floorInt(-1.0 * (1.0 - clipW) / a.RESIZE_STEP)

startMs = a.PAD_START
shrinkMs = steps * a.STEP_MS
endMs = startMs + shrinkMs
durationMs = endMs

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
if fromScale != toScale:
    container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))
    # sort frames
    container.vector.sortFrames()

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrShrink(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global startMs
    global endMs
    global steps

    customProps = None
    alpha = 1.0

    if ms > startMs:

        nprogress = norm(ms, (startMs, endMs), limit=True)
        fstep = nprogress * steps
        step = min(floorInt(fstep), steps-1)
        stepMs = startMs + step * a.STEP_MS
        nShrinkProgress = norm(ms, (stepMs+clip.getState("shrinkStartMs"), stepMs+clip.getState("shrinkEndMs")), limit=True)

        aspectRatio = clip.vector.aspectRatio
        widthFrom = max(aspectRatio, clip.props["width"] - step * a.RESIZE_STEP)
        widthTo = max(aspectRatio, clip.props["width"] - (step+1) * a.RESIZE_STEP)
        heightFrom = 1.0 * widthFrom / aspectRatio
        heightTo = 1.0 * widthTo / aspectRatio

        w = lerp((widthFrom, widthTo), nShrinkProgress)
        h = lerp((heightFrom, heightTo), nShrinkProgress)
        x = clip.props["x"] + (clip.props["width"]-w) * 0.5
        y = clip.props["y"] + (clip.props["height"]-h) * 0.5
        customProps = {
            "pos": [x, y],
            "size": [w, h]
        }

        # if last step, fade out
        if step >= (steps-1):
            alpha = 1.0 - nShrinkProgress

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(alpha * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrShrink)
