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
parser.add_argument('-grid', dest="GRID", default="16x16", help="Size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="256x256", help="End size of grid")
parser.add_argument('-beat', dest="BEAT_MS", default=4096, type=int, help="Duration of beat")
parser.add_argument('-beat0', dest="MIN_BEAT_MS", default=8, type=int, help="Minimum duration of beat")
parser.add_argument('-kfd', dest="KEYS_FOR_DISTANCE", default="tsne,tsne2", help="Keys for determining distance between clips")
parser.add_argument('-cscale', dest="CLIP_SCALE_AMOUNT", default=1.1, type=float, help="Amount to scale clip when playing")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=8192, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=1024, type=int, help="Ensure the middle x audio files play")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
START_GRID_W, START_GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
END_GRID_W, END_GRID_H = tuple([int(v) for v in a.END_GRID.strip().split("x")])
GRID_W, GRID_H = (max(START_GRID_W, END_GRID_W), max(START_GRID_H, END_GRID_H))
DISTANCE_KEY_X, DISTANCE_KEY_Y = tuple([v for v in a.KEYS_FOR_DISTANCE.strip().split(",")])

fromScale = 1.0 * GRID_W / START_GRID_W
toScale = 1.0 * GRID_W / END_GRID_W

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow = initGridComposition(a, GRID_W, GRID_H, stepTime)

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
queuedIndices = [c.props["index"] for c in clips[:4]]
queuedIndicesSet = set(queuedIndices)
clips = sorted(clips, key=lambda c: c.props["index"])

# initialize container scale
container.vector.setTransform(scale=(fromScale, fromScale))
container.vector.addKeyFrame("scale", 0, fromScale, "sin")

ms = a.PAD_START
ys = []
while len(queuedIndices) > 0:

    # play the next clip in queue
    queuedIndicesCount = len(queuedIndicesSet)
    # ys.append(queuedIndicesCount)

    # determine volume and beat step based on number of clips in the queue
    divide = max(1.0, math.sqrt(queuedIndicesCount / 4.0))
    msStep = roundInt(1.0 * a.BEAT_MS * 2.0**(-divide))
    # msStep = roundInt(1.0 * a.BEAT_MS / divide)
    ys.append(msStep)
    msStep = lim(msStep, (a.MIN_BEAT_MS, a.BEAT_MS))
    nvolume = lim(1.0 / divide)
    volume = lerp(a.VOLUME_RANGE, nvolume)

    numberOfClipsToDequeue = floorInt(math.sqrt(queuedIndicesCount)) if queuedIndicesCount > 4 else 1
    clipsToPlay = []
    for i in range(numberOfClipsToDequeue):
        nextIndex = queuedIndices.pop(0)
        clip = clips[nextIndex]
        clipsToPlay.append(clip)
        # remove from queue and put in played
        queuedIndicesSet.remove(nextIndex)
        playedIndicesSet.add(nextIndex)

    # for each clip to play
    newScale = None
    for clip in clipsToPlay:
        # play clip
        if clip.props["playAudio"]:
            clip.queuePlay(ms, {
                "dur": clip.props["audioDur"],
                "volume": volume,
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

        # check to see if clip is fully visible
        isClipFullyVisible = clip.vector.isFullyVisible(a.WIDTH, a.HEIGHT, alphaCheck=False)
        # if not, scale the container out
        if not isClipFullyVisible:
            stepsFromCenter = ceilInt(max(abs(cCol-clip.props["col"]), abs(cRow-clip.props["row"])))
            stepGridW = stepsFromCenter * 2
            ngridW = norm(stepGridW, (START_GRID_W, END_GRID_W))
            newScaleTest = lerp((fromScale, toScale), ngridW)
            newScale = newScaleTest if newScale is None or newScaleTest < newScale else newScale

        # after playing, add the neighbors not played or queued
        neighbors = clip.getGridNeighbors(clips, GRID_W, GRID_H)
        # sort neighbors by grid distance
        neighbors = sorted(neighbors, key=lambda n: distance(clip.props[DISTANCE_KEY_X], clip.props[DISTANCE_KEY_Y], n.props[DISTANCE_KEY_X], n.props[DISTANCE_KEY_Y]))
        for n in neighbors:
            nindex = n.props["index"]
            if nindex not in queuedIndicesSet and nindex not in playedIndicesSet:
                queuedIndices.append(nindex)
                queuedIndicesSet.add(nindex)

    # scale container if necessary
    if newScale is not None:
        container.vector.setTransform(scale=(newScale, newScale))
        container.vector.addKeyFrame("scale", ms, newScale, "sin")

    # increment ms
    ms += msStep

# import matplotlib.pyplot as plt
# plt.hist(ys, bins=200)
# # plt.bar(np.arange(len(ys)), ys)
# plt.show()
# sys.exit()

stepTime = logTime(stepTime, "Create plays/tweens")

container.vector.setTransform(scale=(1.0, 1.0))
# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

processComposition(a, clips, ms, sampler, stepTime, startTime)
