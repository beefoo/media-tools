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
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-data', dest="WIND_DATA", default="data/wind/wnd10m.gdas.2004-01-01*.p.bz2", help="Wind data files")
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="64x64", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=60000, type=int, help="Target duration in seconds")
parser.add_argument('-dmax', dest="DATA_MAX", default=8.0, type=float, help="Intended data max (absolute range is typically around -20 to 20); lower this to move things faster")
parser.add_argument('-smax', dest="SPEED_MAX", default=2.0, type=float, help="Most we should move a clip per frame in pixels; assumes 30fps; assumes 1920x1080px")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
# adjust speed max for this fps and resolution
aa["SPEED_MAX"] = a.SPEED_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["PAD_END"] = 12000
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "cubicInOut"))

dataFiles = getFilenames(a.WIND_DATA)
windData = []
for fn in dataFiles:
    _, d =loadCacheFile(fn)
    windData.append(d)
stepTime = logTime(stepTime, "Read data files")
windDataCount = len(windData)
windData = np.array(windData)
print("Wind data shape = %s x %s x %s x %s" % windData.shape)

# windData /= np.max(np.abs(windData), axis=0)
print("Wind data shape = %s x %s x %s x %s" % windData.shape)
print("Wind range [%s, %s]" % (windData.min(), windData.max()))
stepTime = logTime(stepTime, "Normalize data")

# slice the data: take the middle half
steps, h, w, uv = windData.shape
percent = 0.5
sw = roundInt(w * percent)
sh = roundInt(sw / (1.0 * a.WIDTH / a.HEIGHT))
sx = roundInt((w - sw) * 0.5)
sy = roundInt((h - sh) * 0.5)
slicedWindData = np.zeros((steps, sh, sw, uv), dtype=windData.dtype)
for i in range(steps):
    slicedWindData[i] = windData[i,sy:(sy+sh),sx:(sx+sw),:]
windData = slicedWindData
print("Wind data shape after slice = %s x %s x %s x %s" % windData.shape)

# Initialize clip states
for i, clip in enumerate(clips):
    clip.setState("lastPlayedMs", 0)
    clip.setState("pos", (clip.props["x"], clip.props["y"]))
    clip.setState("rotation", 0)
    lifeDuration = clip.dur * 16
    clip.setState("lifeDuration", lifeDuration)
    clip.setState("life", lifeDuration)

# Write wind data to image
# u = windData[0][:,:,0]
# v = windData[0][:,:,1]
# mag = np.sqrt(u * u + v * v)
# mag /= np.max(mag, axis=0)
# mag = mag * 255.0
# pixels = mag.astype(np.uint8)
# from PIL import Image
# im = Image.fromarray(pixels, mode="L")
# im.save("output/wind_debug.png")

# plot data
# from matplotlib import pyplot as plt
# plt.hist(windData.reshape(-1), bins=100)
# plt.show()
# sys.exit()

startMs = a.PAD_START
ms = startMs + a.DURATION_MS
endMs = ms

# sort frames
container.vector.sortFrames()

stepData = None
currentMs = -1

# zero degrees = 3 o'clock (east), increasing clockwise
def angleFromUV(u, v):
    return 360.0 - math.atan2(v, u) * 180.0 / math.pi % 360.0

# custom clip to numpy array function to override default tweening logic
def clipToNpArrWind(clip, ms, containerW, containerH, precision, parent):
    global a
    global windData
    global startMs
    global endMs
    global stepData
    global currentMs

    dsteps, dh, dw, _ = windData.shape

    frameMs = frameToMs(1, a.FPS)
    life = clip.getState("life")
    lifeDuration = clip.getState("lifeDuration")
    alpha = clip.props["alpha"]
    alphaMultiplier = 0.0 if life < 0 else (1.0 * life / lifeDuration)
    alpha *= alphaMultiplier
    customProps = None

    if alpha > 0:
        nprogress = norm(ms, (startMs, endMs))
        fDataIndex = 1.0 * nprogress * (dsteps-1)
        dataIndex0 = floorInt(fDataIndex)
        dataIndex1 = ceilInt(fDataIndex)

        # ensure we only do this once per frame and not for every clip per frame
        if ms > currentMs or stepData is None:
            currentMs = ms
            # we're before the start
            if nprogress < 0.0:
                stepData = windData[0]
            # we're after the end
            elif nprogress > 1.0:
                stepData = windData[-1]
            # lerp data if we're in-between data frames
            elif dataIndex1 > dataIndex0:
                stepData = lerp((windData[dataIndex0], windData[dataIndex1]), nprogress)
            else:
                stepData = windData[dataIndex0]

        # increase in speed over time; fastest in the middle
        globalSpeed = easeSinInOutBell(lim(nprogress))

        x, y = clip.getState("pos")
        nx, ny = (1.0 * x / a.WIDTH, 1.0 * y / a.HEIGHT)
        nx, ny = (lim(nx), lim(ny))
        dcol, drow = (roundInt((dw-1) * nx), roundInt((dh-1) * ny))
        u, v = tuple(stepData[drow, dcol])
        nu, nv = (u / a.DATA_MAX, v / a.DATA_MAX)
        nu, nv = (lim(nu, (-1.0, 1.0)), lim(nv, (-1.0, 1.0)))
        moveX, moveY = (nu * a.SPEED_MAX * globalSpeed, nv * a.SPEED_MAX * globalSpeed)

        x += moveX
        y += moveY
        clip.setState("pos", (x, y))
        customProps = {
            "pos": [x, y]
        }

    if ms > startMs:
        life -= frameMs

    # reset life if died and we still have time for another full life
    if life <= 0 and ms < endMs-lifeDuration:
        life = lifeDuration
        clip.setState("pos", (clip.props["x"], clip.props["y"]))
    clip.setState("life", life)

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
        roundInt(props["blur"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, ms, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrWind, containsAlphaClips=True, isSequential=True)
