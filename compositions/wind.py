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
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.1,0.8", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=60000, type=int, help="Target duration in ms")
parser.add_argument('-dmax', dest="DATA_MAX", default=8.0, type=float, help="Intended data max (absolute range is typically around -20 to 20); lower this to move things faster")
parser.add_argument('-smax', dest="SPEED_MAX", default=0.5, type=float, help="Most we should move a clip per frame in pixels; assumes 30fps; assumes 1920x1080px")
parser.add_argument('-mmax', dest="MOVE_MAX", default=20.0, type=float, help="Distance to move before resetting")
parser.add_argument('-rstep', dest="ROTATION_STEP", default=0.1, type=float, help="Rotation step in degrees")
parser.add_argument('-tend', dest="TRANSITION_END_MS", default=12000, type=int, help="How long the ending transition should be")
parser.add_argument('-sort', dest="SORT_STRING", default="power=desc=0.5&clarity=desc", help="Query string for sorting samples")
parser.add_argument('-pdur', dest="PULSE_MS", default=256, type=int, help="How long each pulse should be")
parser.add_argument('-msdur', dest="MIN_STEP_MS", default=512, type=int, help="Minumum step between pulses")
parser.add_argument('-pcount', dest="PULSE_COUNT", default=32, type=int, help="Number of pulses per clip play")
parser.add_argument('-pnotes', dest="PLAY_NOTES", default=8, type=int, help="Number of notes to alternate between")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
# adjust speed max for this fps and resolution
aa["SPEED_MAX"] = a.SPEED_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["MOVE_MAX"] = a.MOVE_MAX * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["PAD_END"] = 16000
aa["TRANSITION_END_STEP"] = 1.0 / (a.TRANSITION_END_MS / frameToMs(1.0, a.FPS))
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially
aa["FRAME_ALPHA"] = 0.01
aa["ALPHA_RANGE"] = (1.0, 1.0)

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

samplesGroupedByNote = groupList(samples, "note", sort=True)
noteGroupCount = len(samplesGroupedByNote)
if a.PLAY_NOTES > noteGroupCount:
    print("Not enough notes: requested %s but have %s; reducing" % (a.PLAY_NOTES, noteGroupCount))
    aa["PLAY_NOTES"] = noteGroupCount

# within each group sort by clarity, filter by power and frequency
for i, group in enumerate(samplesGroupedByNote):
    samplesGroupedByNote[i]["items"] = sortByQueryString(group["items"], a.SORT_STRING)
    samplesGroupedByNote[i]["currentIndex"] = 0

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
endMs = startMs + a.DURATION_MS
durationMs = endMs

def playNextNoteClip(a, clips, groups, index, ms, nsequenceStep):
    group = groups[index]
    gsamples = group["items"]
    gcount = len(gsamples)

    # retrieve clips in group
    groupIndices = set([s["index"] for s in gsamples])
    groupClips = [clip for clip in clips if clip.props["index"] in groupIndices]

    # reset group clips if all played
    if allClipStatesEqual(groupClips, "played", True):
        print("Resetting clips in group %s" % index)
        updateClipStates(groupClips, ("played", None))

    # find the next available clip
    clip = None
    for i in range(gcount):
        sample = gsamples[i]
        checkClip = clips[sample["index"]]
        if checkClip.vector.isVisible(a.WIDTH, a.HEIGHT, ms, alphaCheck=False) and checkClip.getState("played") is None:
            clip = checkClip
            break

    if clip is None:
        print("No visible clip found for group %s at %s" % (index, formatSeconds(ms/1000.0)))
        return

    count = a.PULSE_COUNT
    dur = a.PULSE_MS*2
    reverb = lerp((60, 100), nsequenceStep)

    clip.setState("played", True)

    for i in range(count):
        nstep = 1.0 * i / (count-1)
        nstep = easeSinInOutBell(nstep)
        volume = lerp(a.VOLUME_RANGE, nstep)
        clipPlayMs = ms + i * dur
        clipDur = min(clip.props["audioDur"], roundInt(dur/2))
        clip.queuePlay(clipPlayMs, {
            "dur": clipDur,
            "volume": volume,
            "fadeOut": getClipFadeDur(clipDur, percentage=0.2, maxDur=-1),
            "fadeIn": getClipFadeDur(clipDur, percentage=0.1),
            "pan": clip.props["pan"],
            "reverb": reverb,
            "maxDb": clip.props["maxDb"]
        })
        leftMs = roundInt(clipDur * 0.2)
        rightMs = clipDur - leftMs
        clip.queueTween(clipPlayMs, leftMs, [
            ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin")
        ])
        clip.queueTween(clipPlayMs+leftMs, rightMs, [
            ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
        ])

ms = startMs
stepDurMs = a.PULSE_MS * a.PULSE_COUNT * 2
offsetMs = a.PULSE_MS
currentNoteIndex = 0
while ms < endMs:
    nstep = norm(ms, (startMs, endMs))
    playNextNoteClip(a, clips, samplesGroupedByNote, currentNoteIndex, ms, nstep)
    currentNoteIndex = 0 if currentNoteIndex >= a.PLAY_NOTES-1 else currentNoteIndex+1
    playNextNoteClip(a, clips, samplesGroupedByNote, currentNoteIndex, ms+a.PULSE_MS, nstep)
    currentNoteIndex = 0 if currentNoteIndex >= a.PLAY_NOTES-1 else currentNoteIndex+1
    stepDurMs = max(a.MIN_STEP_MS, roundInt(stepDurMs * 0.25))
    ms += stepDurMs + offsetMs
    offsetMs = roundInt(offsetMs * 0.5)
    offsetMs = a.PULSE_MS if offsetMs < 32 else offsetMs

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

# sort frames
container.vector.sortFrames()

# zero degrees = 3 o'clock (east), increasing positive counter clockwise, decreasing negative clockwise
def angleFromUV(u, v):
    return math.atan2(v, u) * 180.0 / math.pi

# custom clip to numpy array function to override width/height calculation
def clipToNpArrWindCalculation(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
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
        globalSpeed = ease(nprogress)
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

        if abs(moveX) > 0 or abs(moveY) > 0:
            clip.setState("lastMove", (moveX, moveY))

        customProps = {
            "pos": [x, y]
        }

    # reset the position after active range
    elif  ms >= endMs:
        x, y = clip.getState("pos")
        moveX, moveY = clip.getState("lastMove")
        alpha = clip.getState("alpha")
        rotation = clip.getState("rotation")
        if alpha > 0.0:
            x += moveX
            y += moveY
            alpha -= a.TRANSITION_END_STEP
            alpha = max(alpha, 0.0)
            clip.setState("pos", (x, y))
            clip.setState("alpha", alpha)
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
        roundInt(alpha * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(rotation * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrWind, containsAlphaClips=True, isSequential=True, customClipToArrCalcFunction="default")
