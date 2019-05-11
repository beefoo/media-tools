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
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.4,0.8", help="Volume range")
parser.add_argument('-bdur', dest="BREATH_DUR", default=8000, type=int, help="Breath duration in ms")
parser.add_argument('-bcount', dest="BREATH_COUNT", default=16, type=int, help="Number of breaths")
parser.add_argument('-bstep', dest="BREATH_STEP", default=0.92, type=float, help="Amount to scale radius for each breath")
parser.add_argument('-props', dest="CLUSTER_PROPS", default="tsne,tsne2", help="X and Y properties for clustering")
parser.add_argument('-blur', dest="BLUR_AMOUNT", default=8.0, type=float, help="Amount to blur frame")
parser.add_argument('-bstart', dest="BLUR_START", default=0.75, type=float, help="When to start blurring, as a percentage of breath composition")
parser.add_argument('-scale', dest="SCALE_AMOUNT", default=1.0, type=float, help="Amount to scale each clip")
parser.add_argument('-trans', dest="TRANSITION_MS", default=16000, type=int, help="Duration it take to transition to blurred and scaled clips")
parser.add_argument('-rot', dest="ANGLE_RANGE", default="0.0,360.0", help="Range of angle rotation a clip should make in degrees")
parser.add_argument('-maxapc', dest="MAX_AUDIO_CLIPS_PER_CLUSTER", default=64, type=int, help="Max number of clips to play per cluster")
parser.add_argument('-cdur', dest="CLIP_DUR", default=128, type=int, help="Target clip play duration")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
# aa["PAD_END"] = 6000
# aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially
# aa["FRAME_ALPHA"] = 0.01 # decrease to make "trails" longer
aa["REVERB"] = 100

PROP1, PROP2 = tuple([p for p in a.CLUSTER_PROPS.strip().split(",")])
aa["ANGLE_RANGE"] = tuple([float(v) for v in a.ANGLE_RANGE.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# add clusters
print("Calculating clusters...")
samples, clusterCenters = addClustersToList(samples, PROP1, PROP2, nClusters=a.BREATH_COUNT)
stepTime = logTime(stepTime, "Calculated clusters")

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

# set z-index based on distance from center (center in front)
samples = sorted(samples, key=lambda s: s["distanceFromCenter"], reverse=True)
samples = addIndices(samples, "zindex", startIndex=1)
samples = sorted(samples, key=lambda s: s["index"])

# add normalized values for cluster props
samples = addNormalizedValues(samples, PROP1, "n"+PROP1)
samples = addNormalizedValues(samples, PROP2, "n"+PROP2)

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

offsetX = (a.WIDTH - a.HEIGHT) * 0.5
cx = a.WIDTH*0.5
cy = a.HEIGHT*0.5
for clip in clips:
    clip.vector.setParent(container.vector)

    # make them squares based on height
    fromH = clip.props["height"]
    toH = fromH * a.SCALE_AMOUNT

    toX = clip.props["n"+PROP1] * (a.HEIGHT-fromH-1) + (fromH-toH) * 0.5 + offsetX
    toY = clip.props["n"+PROP2] * (a.HEIGHT-fromH-1) + (fromH-toH) * 0.5

    clip.setState("tx", toX)
    clip.setState("ty", toY)
    clip.setState("tw", toH)
    clip.setState("th", toH)
    clip.setState("distanceFromCenter", distance(cx, cy, toX, toY))
    clip.setState("angleFromCenter", angleBetween(cx, cy, toX, toY))

    # randomly assign breath offset, rotations
    clip.setState("breathOffset", lerp((0.0, a.BREATH_DUR*0.25), pseudoRandom(clip.props["index"]+1)))
    clip.setState("angleToRotate", lerp(a.ANGLE_RANGE, pseudoRandom(clip.props["index"]+2)))

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
if fromScale != toScale:
    container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))

startMs = a.PAD_START
breatheStartMs = startMs + a.TRANSITION_MS
breatheMs = a.BREATH_DUR * a.BREATH_COUNT
endMs = breatheStartMs + breatheMs
durationMs = endMs

# group clips by cluster
clipGroups = [[] for i in range(a.BREATH_COUNT)]
for clip in clips:
    clipGroups[clip.props["cluster"]].append(clip)

exhaleMs = roundInt(a.BREATH_DUR * 0.5)
for i, group in enumerate(clipGroups):
    center = clusterCenters[i]
    volumeMultiplier = 1.0 - 1.0 * i / (len(clipGroups)-1) # quieter as we go on

    # determine when to play
    count = len(group)
    clipStepMs = roundInt(1.0 * exhaleMs / (count+1))
    playableCount = min(count, a.MAX_AUDIO_CLIPS_PER_CLUSTER)
    clipPlayStepMs = roundInt(1.0 * exhaleMs / (playableCount+1))
    groupStartMs = breatheStartMs + a.BREATH_DUR * i + (a.BREATH_DUR-exhaleMs)
    for j, clip in enumerate(group):
        clipMs = groupStartMs + j * clipStepMs
        # these will actually play audio
        if j < playableCount:
            nprogress = 1.0 * j / playableCount
            volume = lerp(a.VOLUME_RANGE, 1.0-nprogress) * volumeMultiplier
            clipMs = groupStartMs + j * clipPlayStepMs
            playDur = min(a.CLIP_DUR, clip.props["audioDur"])
            fadeOut = roundInt(playDur * 0.8)
            fadeIn = playDur - fadeOut
            clip.queuePlay(clipMs, {
                "start": clip.props["audioStart"],
                "dur": playDur,
                "volume": volume,
                "fadeOut": fadeOut,
                "fadeIn": fadeIn,
                "pan": clip.props["pan"],
                "reverb": clip.props["reverb"],
                "matchDb": clip.props["matchDb"]
            })
        clipDur = clip.props["renderDur"]
        leftMs = roundInt(clipDur * 0.25)
        rightMs = clipDur - leftMs
        clip.queueTween(clipMs, leftMs, ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin"))
        clip.queueTween(clipMs+leftMs, rightMs, ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin"))

# blur container
blurStartMs = roundInt(startMs + a.BLUR_START * breatheMs)
blurDur = roundInt(breatheMs - a.BLUR_START * breatheMs)
blurEndMs = blurStartMs + blurDur
container.queueTween(blurStartMs, blurDur, ("blur", 0.0, a.BLUR_AMOUNT, "cubicInOut"))

# sort frames
container.vector.sortFrames()

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrBreathe(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global startMs
    global breatheStartMs
    global blurStartMs
    global blurEndMs
    global endMs
    global cx
    global cy

    customProps = None
    alpha = 1.0

    # initial transition of scale and position
    if startMs <= ms < breatheStartMs:
        ntransition = norm(ms, (startMs, breatheStartMs))
        ntransition = ease(ntransition, "cubicInOut")
        w = lerp((clip.props["width"], clip.getState("tw")), ntransition)
        h = lerp((clip.props["height"], clip.getState("th")), ntransition)
        x = lerp((clip.props["x"], clip.getState("tx")), ntransition)
        y = lerp((clip.props["y"], clip.getState("ty")), ntransition)
        customProps = {
            "pos": [x, y],
            "size": [w, h]
        }

    elif ms >= breatheStartMs:
        offsetMs = clip.getState("breathOffset")
        nprogress = norm(ms, (breatheStartMs+offsetMs, endMs+offsetMs), limit=True)
        fbreathIndex = nprogress * a.BREATH_COUNT
        breathIndex = min(floorInt(fbreathIndex), a.BREATH_COUNT-1)
        bnprogress = lim(fbreathIndex-breathIndex)

        # determine distance from center
        d = clip.getState("distanceFromCenter")
        d0 = d * (a.BREATH_STEP**breathIndex)
        dmid = d * (a.BREATH_STEP**(breathIndex+4))
        d1 = d * (a.BREATH_STEP**(breathIndex+1))
        distanceFromCenter = lerp((d0, dmid), ease((bnprogress/0.5), "cubicInOut")) if bnprogress <= 0.5 else lerp((dmid, d1), ease(((bnprogress-0.5)/0.5), "cubicInOut"))

        # determine angle from center
        angleToRotate = clip.getState("angleToRotate")
        angle = clip.getState("angleFromCenter") + angleToRotate * nprogress
        angle = angle % 360.0

        # set position
        x, y = translatePoint(cx, cy, distanceFromCenter, angle)
        w = clip.getState("tw")
        h = clip.getState("th")
        customProps = {
            "pos": [x, y],
            "size": [w, h]
        }

    # fade out
    if ms > blurStartMs:
        nalpha = norm(ms, (blurStartMs, blurEndMs), limit=True)
        alpha = ease(1.0-nalpha, "cubicInOut")

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

processComposition(a, clips, durationMs, sampler, stepTime, startTime,
    customClipToArrFunction=clipToNpArrBreathe,
    containsAlphaClips=True
    # container=container
)
