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
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.8", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=60000, type=int, help="Target duration in ms")
parser.add_argument('-smax', dest="SPEED_MAX", default=0.8, type=float, help="Most we should move a clip per frame in pixels; assumes 30fps; assumes 1920x1080px")
parser.add_argument('-rstep', dest="ROTATION_STEP", default=0.1, type=float, help="Rotation step in degrees")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
# adjust speed max for this fps and resolution
aa["SPEED_MAX"] = a.SPEED_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
# aa["PAD_END"] = 16000
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = 1.0
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# fromScale = 1.0 * gridW / startGridW
# toScale = 1.0 * gridW / endGridW
# if fromScale != toScale:
#     container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))
vectorData = np.zeros((a.HEIGHT, a.WIDTH, 4))
cx = (a.WIDTH-1) * 0.5
cy = (a.HEIGHT-1) * 0.5
for row in range(a.HEIGHT):
    for col in range(a.WIDTH):
        distanceFromCenter = distance(cx, cy, col, row)
        angleFromCenter = angleBetween(cx, cy, col, row)
        angleTowardCenter = (angleFromCenter + 180.0) % 360.0
        normalAngleTowardCenter = (angleTowardCenter - 90.0) % 360.0
        mag = norm(distanceFromCenter, (0.5, min(a.WIDTH*0.5, a.HEIGHT*0.5)-0.5), limit=True)
        # clips should move toward the ring around the center, then along the ring
        fromAngle = angleFromCenter
        toAngle = (fromAngle + 90.0) % 360.0
        if mag > 0.5:
            fromAngle = angleTowardCenter
            toAngle = (fromAngle - 90.0) % 360.0
        mag = easeSinInOutBell(mag)
        angle = lerp((fromAngle, toAngle), mag)
        radians = math.radians(angle)
        u = mag * math.cos(radians)
        v = mag * math.sin(radians)
        vectorData[row, col] = np.array([u, v, mag, angle])

def resetClips(clips):
    # Initialize clip states
    for i, clip in enumerate(clips):
        clip.setState("pos", (clip.props["x"], clip.props["y"]))
        clip.setState("alpha", clip.props["alpha"])
        clip.setState("rotation", 0)
        clip.setState("distanceTravelled", 0)

def getVector(a, vdata, x, y):
    dh, dw, _ = vdata.shape
    nx, ny = (1.0 * x / a.WIDTH, 1.0 * y / a.HEIGHT)
    nx, ny = (lim(nx), lim(ny))
    dcol, drow = (roundInt((dw-1) * nx), roundInt((dh-1) * ny))
    return tuple(vdata[drow, dcol])

def clipPositionAtTime(a, clip, ms, vdata, startMs, endMs):
    x = None
    y = None
    rotation = 0.0
    alpha = clip.props["alpha"]

    if ms >= startMs:
        nprogress = norm(ms, (startMs, endMs))
        # increase in speed over time; fastest in the middle
        globalSpeed = ease(nprogress)
        x, y = clip.getState("pos")
        speed = a.SPEED_MAX * globalSpeed
        u, v, mag, angle = getVector(a, vdata, x, y)
        moveX, moveY = (u*speed, v*speed)

        distanceTravelled = clip.getState("distanceTravelled")
        distanceTravelled += distance(0, 0, moveX, moveY)
        clip.setState("distanceTravelled", distanceTravelled)

        currentAngle = clip.getState("rotation")
        deltaAngle = angle - currentAngle
        rotationDirection = 1.0 if deltaAngle >= 0 else -1.0
        rotationStep = a.ROTATION_STEP
        deltaAngle = min(deltaAngle, rotationStep) if rotationDirection > 0 else max(deltaAngle, -rotationStep)
        rotation = currentAngle + deltaAngle
        clip.setState("rotation", rotation)

        x += moveX
        y += moveY
        clip.setState("pos", (x, y))
        clip.setState("alpha", alpha)

        # TODO
        # if distanceTravelled >= moveMax:

    return x, y, alpha, rotation

resetClips(clips)

startMs = a.PAD_START
endMs = startMs + a.DURATION_MS
durationMs = endMs

# stepTime = logTime(stepTime, "Determine audio sequence")

# sort frames
container.vector.sortFrames()

# custom clip to numpy array function to override default tweening logic
def clipToNpArrStir(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global vectorData
    global startMs
    global endMs

    customProps = None
    _x, _y, alpha, rotation = clipPositionAtTime(a, clip, ms, vectorData, startMs, endMs)

    if _x is not None and _y is not None:
        customProps = {
            "pos": [_x, _y]
        }

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
        roundInt(rotation * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrStir, containsAlphaClips=True, isSequential=True, customClipToArrCalcFunction="default")
