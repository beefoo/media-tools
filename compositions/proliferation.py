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
parser.add_argument('-zdur', dest="ZOOM_DUR", default=120, type=int, help="Duration of zoom in seconds")
parser.add_argument('-kfd', dest="KEYS_FOR_DISTANCE", default="tsne,tsne2", help="Keys for determining distance between clips")
parser.add_argument('-cscale', dest="CLIP_SCALE_AMOUNT", default=1.1, type=float, help="Amount to scale clip when playing")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=-1, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=-1, type=int, help="Ensure the middle x audio files play")
parser.add_argument('-msc', dest="MAX_SIMULTANEOUS_CLIPS", default=64, type=int, help="Max number of clips to play at the same time")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
DISTANCE_KEY_X, DISTANCE_KEY_Y = tuple([v for v in a.KEYS_FOR_DISTANCE.strip().split(",")])
ZOOM_DUR_MS = a.ZOOM_DUR * 1000

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW

START_RINGS = int(startGridW / 2)
END_RINGS = int(endGridW / 2)

# samples = sorted(samples, key=lambda s: (s["distanceFromCenter"], -s["clarity"]))

# set clip alpha to zero by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = 0.0
    samples[i]["ring"] = getRing(s["col"], s["row"], cCol, cRow)

# determine the point to compare all clips to for similarity
firstRing = [s for s in samples if s["ring"]==1]
centerSimilarityX = np.mean([s[DISTANCE_KEY_X] for s in firstRing])
centerSimilarityY = np.mean([s[DISTANCE_KEY_Y] for s in firstRing])

# set play sort key
for i, s in enumerate(samples):
    samples[i]["playOrder"] = distance(s[DISTANCE_KEY_X], s[DISTANCE_KEY_Y], centerSimilarityX, centerSimilarityY)

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

# queue the middle four
playedIndicesSet = set([])
queuedIndices = [(c.props["index"], (0, 0.0)) for c in clips[:4]]
queuedIndicesSet = set([i[0] for i in queuedIndices])
clips = sorted(clips, key=lambda c: c.props["playOrder"])

ms = a.PAD_START

scaleXs = [ms]
scaleYs = [fromScale]
msPerStep = roundInt(1.0 * ZOOM_DUR_MS / END_RINGS)
for step in range(END_RINGS):
    ring = step + 1
    ringStartMs = ms + step * msPerStep
    ringClips = [c for c in clips if c.props["ring"] == ring]
    ringClipCount = len(ringClips)
    ringClipPlayCount = ringClipCount

    ringScale = 1.0 * gridW / (ring*2)
    if ringScale < fromScale:
        scaleXs.append(ringStartMs)
        scaleYs.append(ringScale)

    # limit how many clips play audio
    playIndices = [c.props["index"] for c in ringClips]
    if ringClipPlayCount > a.MAX_SIMULTANEOUS_CLIPS:
        ringClipPlayCount = a.MAX_SIMULTANEOUS_CLIPS
        random.seed(a.RANDOM_SEED+step)
        random.shuffle(playIndices)
        playIndices = playIndices[:a.MAX_SIMULTANEOUS_CLIPS]
    playIndicesSet = set(playIndices)

    ringClipMs = 1.0 * msPerStep / ringClipCount

    # determine volume based on number of clips in the queue
    divide = max(1.0, math.sqrt(ringClipPlayCount / 4.0))
    nvolume = lim(1.0 / divide)
    volume = lerp(a.VOLUME_RANGE, nvolume)

    for j, clip in enumerate(ringClips):
        clipMs = ringStartMs + j * ringClipMs
        if clip.props["index"] in playIndicesSet:
            clip.queuePlay(clipMs, {
                "dur": clip.props["audioDur"],
                "volume": volume,
                "fadeOut": clip.props["fadeOut"],
                "fadeIn": clip.props["fadeIn"],
                "pan": clip.props["pan"],
                "reverb": clip.props["reverb"]
            })
        leftMs = roundInt(clip.dur * 0.2)
        rightMs = clip.dur - leftMs
        clip.queueTween(clipMs, leftMs, [
            ("alpha", 0, a.ALPHA_RANGE[1], "sin")
        ])
        clip.queueTween(clipMs+leftMs, rightMs, [
            ("alpha", a.ALPHA_RANGE[1], a.ALPHA_RANGE[0], "sin")
        ])
ms = ms + ZOOM_DUR_MS

# tween container zoom
pivot = 0.5
tweenPivotMs = lerp((scaleXs[0], scaleXs[1]), pivot)
tweenPivotScale = lerp((scaleYs[0], scaleYs[1]), pivot)
container.queueTween(scaleXs[0], tweenPivotMs-scaleXs[0], ("scale", scaleYs[0], tweenPivotScale, "quadIn"))
container.queueTween(tweenPivotMs, scaleXs[-1]-tweenPivotMs, ("scale", tweenPivotScale, scaleYs[-1], "quartOut"))

# See how well the data maps to the tweened data
# container.vector.plotKeyframes("scale", additionalPlots=[([x/1000.0 for x in scaleXs], scaleYs)])
# sys.exit()

stepTime = logTime(stepTime, "Create plays/tweens")

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

processComposition(a, clips, ms, sampler, stepTime, startTime)
