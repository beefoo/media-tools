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
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="16x16", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=4096, type=int, help="Duration of beat")
parser.add_argument('-beat0', dest="MIN_BEAT_MS", default=8, type=int, help="Minimum duration of beat")
parser.add_argument('-kfd', dest="KEYS_FOR_DISTANCE", default="tsne,tsne2", help="Keys for determining distance between clips")
parser.add_argument('-cscale', dest="CLIP_SCALE_AMOUNT", default=1.1, type=float, help="Amount to scale clip when playing")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=-1, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=-1, type=int, help="Ensure the middle x audio files play")
parser.add_argument('-msc', dest="MAX_SIMULTANEOUS_CLIPS", default=8, type=int, help="Max number of clips to play at the same time")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
DISTANCE_KEY_X, DISTANCE_KEY_Y = tuple([v for v in a.KEYS_FOR_DISTANCE.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW

samples = sorted(samples, key=lambda s: (s["distanceFromCenter"], -s["clarity"]))

# set clip alpha to zero by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = 0.0

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# queue the middle four
playedIndicesSet = set([])
queuedIndices = [(c.props["index"], 0.0) for c in clips[:4]]
queuedIndicesSet = set([i[0] for i in queuedIndices])
clips = sorted(clips, key=lambda c: c.props["index"])

ms = a.PAD_START
scaleXs = [ms]
scaleYs = [fromScale]
currentScale = fromScale
while len(queuedIndices) > 0:

    # play the next clip in queue
    queuedIndicesCount = len(queuedIndicesSet)

    # determine volume and beat step based on number of clips in the queue
    divide = max(1.0, math.sqrt(queuedIndicesCount / 4.0))
    msStep = roundInt(1.0 * a.BEAT_MS * 2.0**(-divide))
    msStep = lim(msStep, (a.MIN_BEAT_MS, a.BEAT_MS))
    nvolume = lim(1.0 / divide)
    volume = lerp(a.VOLUME_RANGE, nvolume)

    numberOfClipsToDequeue = floorInt(math.sqrt(queuedIndicesCount)) if queuedIndicesCount > 4 else 1
    clipsToPlay = []
    for i in range(numberOfClipsToDequeue):
        if len(queuedIndices) <= 0:
            break
        nextIndex, _ = queuedIndices.pop(0)
        clip = clips[nextIndex]
        clipsToPlay.append(clip)
        # remove from queue and put in played
        queuedIndicesSet.remove(nextIndex)
        playedIndicesSet.add(nextIndex)

    # for each clip to play
    newScale = None
    for i, clip in enumerate(clipsToPlay):
        # play clip
        if i < a.MAX_SIMULTANEOUS_CLIPS:
            clip.queuePlay(ms, {
                "dur": clip.props["audioDur"],
                "volume": volume * (0.9 ** i), # simulaneous clips at slightly different volume
                "fadeOut": clip.props["fadeOut"],
                "fadeIn": clip.props["fadeIn"],
                "pan": clip.props["pan"],
                "reverb": clip.props["reverb"]
            })
        leftMs = roundInt(clip.dur * 0.25)
        rightMs = clip.dur - leftMs
        clip.queueTween(ms, leftMs, [
            ("alpha", 0, a.ALPHA_RANGE[1], "sin")
            # ("scale", 1.0, a.CLIP_SCALE_AMOUNT, "sin")
        ])
        clip.queueTween(ms+leftMs, rightMs, [
            ("alpha", a.ALPHA_RANGE[1], a.ALPHA_RANGE[0], "sin")
            # ("scale", a.CLIP_SCALE_AMOUNT, 1.0, "sin")
        ])

        stepsFromCenter = ceilInt(max(abs(cCol-clip.props["col"]), abs(cRow-clip.props["row"])))
        stepGridW = (stepsFromCenter+1) * 2
        newScaleTest = max(1.0, 1.0 * gridW / stepGridW)
        newScale = newScaleTest if newScale is None or newScaleTest < newScale else newScale

        # after playing, add the neighbors not played or queued
        neighbors = clip.getGridNeighbors(clips, gridW, gridH)
        # sort neighbors by grid distance
        neighbors = sorted(neighbors, key=lambda n: distance(clip.props[DISTANCE_KEY_X], clip.props[DISTANCE_KEY_Y], n.props[DISTANCE_KEY_X], n.props[DISTANCE_KEY_Y]))
        for n in neighbors:
            nindex = n.props["index"]
            # already played; skip
            if nindex in playedIndicesSet:
                continue
            sortValue = distance(clip.props[DISTANCE_KEY_X], clip.props[DISTANCE_KEY_Y], n.props[DISTANCE_KEY_X], n.props[DISTANCE_KEY_Y])
            # already queued, check if this distance is closer than current entry
            if nindex in queuedIndicesSet:
                for j, entry in enumerate(queuedIndices):
                    entryIndex, entrySortValue = entry
                    if entryIndex==nindex:
                        if sortValue < entrySortValue:
                            queuedIndices[j] = (entryIndex, sortValue)
                        break
            # otherwise, add to queue
            else:
                queuedIndices.append((nindex, sortValue))
                queuedIndicesSet.add(nindex)

    # sort indices by distance from clip that invoked it
    queuedIndices = sorted(queuedIndices, key=lambda k: k[1])

    # scale container if necessary
    if newScale is not None and newScale < currentScale:
        currentScale = newScale
        scaleXs.append(ms)
        scaleYs.append(currentScale)

    # increment ms
    ms += msStep

# tween container zoom between first two keyframes
container.queueTween(scaleXs[0], scaleXs[1]-scaleXs[0], ("scale", scaleYs[0], scaleYs[1], "cubicIn"))

# tween container zoom from second to last keyframe
container.queueTween(scaleXs[1], scaleXs[-1]-scaleXs[1], ("scale", scaleYs[1], scaleYs[-1], "cubicOut"))

# See how well the data maps to the tweened data
# container.vector.plotKeyframes("scale", additionalPlots=[([x/1000.0 for x in scaleXs], scaleYs)])
# sys.exit()

stepTime = logTime(stepTime, "Create plays/tweens")

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

processComposition(a, clips, ms, sampler, stepTime, startTime)
