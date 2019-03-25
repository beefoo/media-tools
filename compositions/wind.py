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
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-data', dest="WIND_DATA", default="data/wind/wnd10m.gdas.2004-01-01-00.0.p.bz2", help="Wind data files")
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="64x64", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=60000, type=int, help="Target duration in ms")
parser.add_argument('-dmax', dest="DATA_MAX", default=8.0, type=float, help="Intended data max (absolute range is typically around -20 to 20); lower this to move things faster")
parser.add_argument('-smax', dest="SPEED_MAX", default=0.5, type=float, help="Most we should move a clip per frame in pixels; assumes 30fps; assumes 1920x1080px")
parser.add_argument('-mmax', dest="MOVE_MAX", default=20.0, type=float, help="Distance to move before resetting")
parser.add_argument('-bcount', dest="BLOW_COUNT", default=8, type=int, help="Number of times to blow the wind")
parser.add_argument('-bdur', dest="BLOW_DURATION", default=4000, type=int, help="Blow duration in ms")
parser.add_argument('-bspeed', dest="BLOW_SPEED", default=1.0, type=float, help="Blow speed")
parser.add_argument('-bradius', dest="BLOW_RADIUS", default=8.0, type=float, help="Blow radius")
parser.add_argument('-rstep', dest="ROTATION_STEP", default=0.1, type=float, help="Rotation step in degrees")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
# adjust speed max for this fps and resolution
aa["SPEED_MAX"] = a.SPEED_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["MOVE_MAX"] = a.MOVE_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["BLOW_SPEED"] = a.BLOW_SPEED * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["PAD_END"] = 12000
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially
aa["FRAME_ALPHA"] = 0.1

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
container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))

_, windData = loadCacheFile(a.WIND_DATA)
dataFiles = getFilenames(a.WIND_DATA)
stepTime = logTime(stepTime, "Read data files")
windData = np.array(windData)
print("Wind data shape = %s x %s x %s" % windData.shape)

# windData /= np.max(np.abs(windData), axis=0)
print("Wind range [%s, %s]" % (windData.min(), windData.max()))

# slice the data: take the middle half
h, w, uv = windData.shape
percent = 0.5
sw = roundInt(w * percent)
sh = roundInt(sw / (1.0 * a.WIDTH / a.HEIGHT))
sx = roundInt((w - sw) * 0.5)
sy = roundInt((h - sh) * 0.5)
windData = windData[sy:(sy+sh),sx:(sx+sw),:]
print("Wind data shape after slice = %s x %s x %s" % windData.shape)

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

# Initialize clip states
for i, clip in enumerate(clips):
    clip.setState("pos", (clip.props["x"], clip.props["y"]))
    clip.setState("rotation", 0)
    clip.setState("distanceTravelled", 0)
    clip.setState("moveMax", a.MOVE_MAX + a.MOVE_MAX * pseudoRandom(i+1))

def getMovePositionWithWind(a, windData, x, y, speed):
    dh, dw, _ = windData.shape
    nx, ny = (1.0 * x / a.WIDTH, 1.0 * y / a.HEIGHT)
    nx, ny = (lim(nx), lim(ny))
    dcol, drow = (roundInt((dw-1) * nx), roundInt((dh-1) * ny))
    u, v = tuple(windData[drow, dcol])
    nu, nv = (u / a.DATA_MAX, v / a.DATA_MAX)
    nu, nv = (lim(nu, (-1.0, 1.0)), lim(nv, (-1.0, 1.0)))
    moveX, moveY = (nu * speed, nv * speed)
    return (u, v, moveX, moveY)

# def dequeueClips(ms, clips, queue):
#     global a
#     indices = list(queue.keys())
#
#     for cindex in indices:
#         lastEntry = queue[cindex][-1]
#         frameMs = lastEntry[1]
#         clip = clips[cindex]
#         thresholdMs = clip.dur * 2
#         # we have passed this clip
#         if (ms - frameMs) > thresholdMs:
#             ndistance, playMs = max(queue[cindex], key=itemgetter(0)) # get the loudest frame
#             lastPlayedMs = clip.getState("lastPlayedMs")
#             # check to make sure we don't play if already playing
#             if lastPlayedMs is None or (playMs - lastPlayedMs) > thresholdMs:
#                 clip.queuePlay(playMs, {
#                     "dur": clip.props["audioDur"],
#                     "volume": lerp(a.VOLUME_RANGE, ndistance),
#                     "fadeOut": clip.props["fadeOut"],
#                     "fadeIn": clip.props["fadeIn"],
#                     "pan": clip.props["pan"],
#                     "reverb": clip.props["reverb"],
#                     "maxDb": clip.props["maxDb"]
#                 })
#                 clip.setState("lastPlayedMs", playMs)
#                 alphaTo = lerp(a.ALPHA_RANGE, ndistance)
#                 clipDur = clip.dur * 2
#                 leftMs = max(10, roundInt(clipDur * 0.5))
#                 rightMs = clipDur - leftMs
#                 clip.queueTween(frameMs, leftMs, ("alpha", a.ALPHA_RANGE[0], alphaTo, "sin"))
#                 clip.queueTween(frameMs+leftMs, rightMs, ("alpha", alphaTo, a.ALPHA_RANGE[0], "sin"))
#             queue.pop(cindex, None)
#
#     return queue
#
# blowFrames = msToFrame(a.BLOW_DURATION, a.FPS)
# blowStartMs = startMs + a.BLOW_DURATION
# maxScale = max(fromScale, toScale)
# blowW = 1.0 * a.WIDTH / maxScale
# blowX0 = (a.WIDTH - blowW) * 0.5
# blowX1 = blowX0 + blowW
# blowH = 1.0 * a.HEIGHT / maxScale
# blowY0 = (a.HEIGHT - blowH) * 0.5
# blowY1 = blowY0 + blowH
# blowStepMs = roundInt(1.0 * a.DURATION_MS / (a.BLOW_COUNT+1))
# queue = {}
# for blow in range(a.BLOW_COUNT):
#     # for each blow, choose a random starting point in the center of the grid
#     nprogress = 1.0 * blow / (a.BLOW_COUNT-1)
#     blowStartMs = a.BLOW_DURATION + blow * blowStepMs
#     nrand = pseudoRandom(blow+7)
#     x = lerp((blowX0, blowX1), nrand)
#     y = lerp((blowY0, blowY1), nrand)
#     for frame in range(blowFrames):
#         frameMs = blowStartMs + frameToMs(frame, a.FPS)
#         u, v, moveX, moveY = getMovePositionWithWind(a, windData, x, y, a.BLOW_SPEED)
#         x += moveX
#         y += moveY
#         frameClips = getNeighborClips(clips, x, y, gridW, gridH, a.BLOW_RADIUS)
#         for ndistance, clip in frameClips:
#             cindex = clip.props["index"]
#             if ndistance > 0:
#                 entry = (ndistance, frameMs)
#                 if cindex in queue:
#                     queue[cindex].append(entry)
#                 else:
#                     queue[cindex] = [entry]
#         queue = dequeueClips(frameMs, clips, queue)

# sort frames
container.vector.sortFrames()

# zero degrees = 3 o'clock (east), increasing positive counter clockwise, decreasing negative clockwise
def angleFromUV(u, v):
    return math.atan2(v, u) * 180.0 / math.pi

# custom clip to numpy array function to override default tweening logic
def clipToNpArrWind(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global windData
    global startMs
    global endMs

    customProps = None
    rotation = 0.0

    alpha = clip.props["alpha"]

    if startMs <= ms < endMs:

        nprogress = norm(ms, (startMs, endMs))
        # increase in speed over time; fastest in the middle
        globalSpeed = easeSinInOutBell(nprogress)
        x, y = clip.getState("pos")
        distanceTravelled = clip.getState("distanceTravelled")
        u, v, moveX, moveY = getMovePositionWithWind(a, windData, x, y, a.SPEED_MAX * globalSpeed)
        distanceTravelled += distance(0, 0, moveX, moveY)
        # start to reduce alpha halway through max move distance
        moveMax = clip.getState("moveMax")
        halfDistance = moveMax * 0.5
        if distanceTravelled > halfDistance:
            alpha *= ease(norm(distanceTravelled, (moveMax, halfDistance), limit=True))
        clip.setState("distanceTravelled", distanceTravelled)

        # fade in after reset
        resetMs = clip.getState("resetMs")
        if resetMs is not None:
            timeSinceReset = ms - resetMs
            if timeSinceReset < clip.dur:
                alpha *= ease(1.0 * timeSinceReset / clip.dur)

        # determine rotation from uv
        targetAngle = angleFromUV(u, v)
        currentAngle = clip.getState("rotation")
        deltaAngle = targetAngle - currentAngle
        rotationDirection = 1.0 if deltaAngle >= 0 else -1.0
        rotationStep = a.ROTATION_STEP
        deltaAngle = min(deltaAngle, rotationStep) if rotationDirection > 0 else max(deltaAngle, -rotationStep)
        rotation = currentAngle + deltaAngle
        clip.setState("rotation", rotation)

        x += moveX
        y += moveY
        # reset if we reached max distance moved
        if distanceTravelled >= moveMax:
            clip.setState("pos", (clip.props["x"], clip.props["y"]))
            clip.setState("resetMs", ms)
            clip.setState("distanceTravelled", 0)
            clip.setState("moveMax", a.MOVE_MAX)
        else:
            clip.setState("pos", (x, y))
        clip.setState("alpha", alpha)

        customProps = {
            "pos": [x, y]
        }

    # reset the position after active range
    elif ms >= endMs:
        absoluteEndMs = endMs + a.PAD_END
        nprogress = lim(norm(ms, (endMs, absoluteEndMs)))
        nprogress = ease(nprogress)
        x, y = clip.getState("pos")
        x1, y1 = (clip.props["x"], clip.props["y"])
        rotation = lerp((clip.getState("rotation"), 0.0), nprogress)
        alpha = lerp((clip.getState("alpha"), clip.props["alpha"]), nprogress)
        if x != x1 or y != y1:
            x = lerp((x, x1), nprogress)
            y = lerp((y, y1), nprogress)
            customProps = {
                "pos": [x, y]
            }

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    # alpha from keyframe should override frame alpha
    alpha = props["alpha"] if props["alpha"] > clip.props["alpha"] else alpha

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(alpha * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(rotation * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, ms, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrWind, containsAlphaClips=True, isSequential=True)
