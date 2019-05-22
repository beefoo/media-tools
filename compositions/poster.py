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
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
addTextArguments(parser)
parser.add_argument('-tfile', dest="TEXT_FILE", default="titles/main.md", help="Input smarkdown file")
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="32x32", help="End size of grid")
parser.add_argument('-radius', dest="RADIUS", default=8.0, type=float, help="Target radius as a percentage of clip height")
parser.add_argument('-freq', dest="FREQ", default=2.4, type=float, help="Frequency")
parser.add_argument('-rot', dest="NROTATION", default=0.6, type=float, help="Amount of rotation (between 0 and 1)")
parser.add_argument('-bright', dest="FULL_BRIGHTNESS", action="store_true", help="Create image with full brightness?")
a = parser.parse_args()
aa = vars(a)
aa["OUTPUT_SINGLE_FRAME"] = 1
aa["PAD_START"] = 0
aa["PAD_END"] = 0
parseVideoArgs(a)

TEXTBLOCK_Y_OFFSET = roundInt(a.HEIGHT * a.TEXTBLOCK_Y_OFFSET)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

toScale = 1.0 * gridW / endGridW
container.vector.setTransform(scale=(toScale, toScale))

frameW = a.WIDTH / toScale
frameH = a.HEIGHT / toScale
frameX = (a.WIDTH - frameW) * 0.5
frameY = (a.HEIGHT - frameH) * 0.5

clips = samplesToClips(samples)

# Determine rotation offsets and brightness
for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)
    clip.setState("cx", clip.props["x"] + clip.props["width"] * 0.5)
    clip.setState("cy", clip.props["y"] + clip.props["height"] * 0.5)
    rotationOffset = 1.0 * ((gridW-clip.props["row"]-1)+clip.props["col"]) / (gridH + gridW - 2) * 2.0 * math.pi
    clip.setState("rotationOffset", rotationOffset)

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrPoster(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global frameX
    global frameY
    global frameW
    global frameH

    radius = a.RADIUS * clip.props["height"]
    freq = a.FREQ

    # Rotate clip around its center
    nrotation = a.NROTATION
    angle = (1.0 - nrotation) * 2.0 * math.pi + clip.getState("rotationOffset") * freq
    cx, cy = translatePoint(clip.getState("cx"), clip.getState("cy"), radius, angle, radians=True)
    x, y = (cx - clip.props["width"]*0.5, cy - clip.props["height"]*0.5)

    # make center dark
    brightness = 1.0
    if not a.FULL_BRIGHTNESS:
        nx = norm(cx, (frameX, frameX+frameW), limit=True)
        ny = norm(cy, (frameY, frameY+frameH), limit=True)
        bcx = 0.5
        bcy = 0.5
        bd = distance(bcx, bcy, nx, ny)
        nbmax = 1.0 # increase to make more of the center darker
        nbrightness = ease(lim(bd / nbmax), "cubicInOut")
        brightness = lerp(a.BRIGHTNESS_RANGE, nbrightness)

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

durationMs = 100
processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrPoster, containsAlphaClips=True)

# Read text
tprops = getTextProperties(a)
lines = parseMdFile(a.TEXT_FILE, a)
lines = addTextMeasurements(lines, tprops)

# Write text on top of frame
srcFn = a.OUTPUT_FRAME % "01"
targetFn = a.OUTPUT_FRAME % "poster"
im = Image.open(srcFn)

linesToImage(lines, targetFn, a.WIDTH, a.HEIGHT, color=a.TEXT_COLOR, tblockYOffset=TEXTBLOCK_Y_OFFSET, overwrite=a.OVERWRITE, bgImage=im)
