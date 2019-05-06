# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
from operator import itemgetter
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
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.8", help="Volume range")
parser.add_argument('-radius', dest="RADIUS", default=4.0, type=float, help="Target radius as a percentage of clip height")
parser.add_argument('-freq', dest="FREQ_RANGE", default="2.0,2.0", help="Frequency range")
parser.add_argument('-rdur', dest="ROTATION_DUR", default=8000, type=int, help="Target duration in ms")
parser.add_argument('-rot', dest="ROTATIONS", default=8, type=int, help="Total number of rotations")

a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["PAD_END"] = 6000
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially
aa["FRAME_ALPHA"] = 0.01 # decrease to make "trails" longer
aa["FREQ_RANGE"] = tuple([float(f) for f in a.FREQ_RANGE.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

degreesPerMs = 360.0 / a.ROTATION_DUR
for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)
    clip.setState("cx", clip.props["x"] + clip.props["width"] * 0.5)
    clip.setState("cy", clip.props["y"] + clip.props["height"] * 0.5)
    rotationOffset = 1.0 * ((gridW-clip.props["row"]-1)+clip.props["col"]) / (gridH + gridW - 2) * 2.0 * math.pi
    clip.setState("rotationOffset", rotationOffset)
    nBrightness = norm(clip.props["distanceFromCenter"], (0.5, min(gridW*0.5, gridH*0.5)-0.5), limit=True)
    nBrightness = easeSinInOutBell(nBrightness)
    clip.setState("nBrightness", nBrightness)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
if fromScale != toScale:
    container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))

rotationsMs = a.ROTATION_DUR * a.ROTATIONS
startMs = a.PAD_START
endMs = startMs + rotationsMs
durationMs = endMs

# sort frames
container.vector.sortFrames()

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrFlow(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global startMs
    global endMs

    customProps = None
    brightness = a.BRIGHTNESS_RANGE[0]

    if startMs <= ms < endMs:

        nprogress = norm(ms, (startMs, endMs))
        nprogress = easeSinInOutBell(nprogress)
        radius = a.RADIUS * nprogress * clip.props["height"]
        freq = lerp(a.FREQ_RANGE, nprogress)

        # Rotate clip around its center
        nrotation = 1.0 * (ms % a.ROTATION_DUR) / a.ROTATION_DUR
        angle = (1.0 - nrotation) * 2.0 * math.pi + clip.getState("rotationOffset") * freq
        cx, cy = translatePoint(clip.getState("cx"), clip.getState("cy"), radius, angle, radians=True)
        x, y = (cx - clip.props["width"]*0.5, cy - clip.props["height"]*0.5)

        # Set brightness
        brightness = lerp(a.BRIGHTNESS_RANGE, nprogress * clip.getState("nBrightness"))

        customProps = {
            "pos": [x, y]
        }

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
        roundInt(brightness * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrFlow, containsAlphaClips=True, isSequential=True)
