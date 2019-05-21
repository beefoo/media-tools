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

from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-radius', dest="RADIUS", default=4.0, type=float, help="Target radius as a percentage of clip height")
parser.add_argument('-freq', dest="FREQ", default=2.0, type=float, help="Frequency")
a = parser.parse_args()
aa = vars(a)
aa["OUTPUT_SINGLE_FRAME"] = 1
parseVideoArgs(a)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = lerp(a.BRIGHTNESS_RANGE, 1.0-ease(s["nDistanceFromCenter"]))

clips = samplesToClips(samples)

# Determine rotation offsets and brightness
for i, clip in enumerate(clips):
    clip.setState("cx", clip.props["x"] + clip.props["width"] * 0.5)
    clip.setState("cy", clip.props["y"] + clip.props["height"] * 0.5)
    rotationOffset = 1.0 * ((gridW-clip.props["row"]-1)+clip.props["col"]) / (gridH + gridW - 2) * 2.0 * math.pi
    clip.setState("rotationOffset", rotationOffset)

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrPoster(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a

    radius = a.RADIUS * clip.props["height"]
    freq = a.FREQ

    # Rotate clip around its center
    nrotation = 1.0
    angle = (1.0 - nrotation) * 2.0 * math.pi + clip.getState("rotationOffset") * freq
    cx, cy = translatePoint(clip.getState("cx"), clip.getState("cy"), radius, angle, radians=True)
    x, y = (cx - clip.props["width"]*0.5, cy - clip.props["height"]*0.5)

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
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

durationMs = 500
processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrPoster, containsAlphaClips=True)
