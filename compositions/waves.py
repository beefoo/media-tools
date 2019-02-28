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
parser.add_argument('-beatms', dest="BEAT_MS", default=1024, type=int, help="Milliseconds per beat")
parser.add_argument('-margin', dest="CLIP_MARGIN", default=0.5, type=float, help="Margin between clips in pixels")
parser.add_argument('-beats', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide beat, e.g. 1 = 1/2 notes, 2 = 1/4 notes, 3 = 1/8th notes, 4 = 1/16 notes")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-alphar', dest="ALPHA_RANGE", default="0.33,1.0", help="Alpha range")
parser.add_argument('-translate', dest="TRANSLATE_AMOUNT", default=0.8, type=float, help="Amount to translate clip as a percentage of minimum dimension")
parser.add_argument('-scale', dest="SCALE_AMOUNT", default=1.33, type=float, help="Amount to scale clip")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="16x16", help="End size of grid")
parser.add_argument('-steps', dest="STEPS", default=16, type=int, help="Number of waves/beats")
parser.add_argument('-wd', dest="WAVE_DUR", default=8000, type=int, help="Wave duration in milliseconds")
parser.add_argument('-bd', dest="BEAT_DUR", default=6000, type=int, help="Beat duration in milliseconds")
parser.add_argument('-mcd', dest="MIN_CLIP_DUR", default=1500, type=int, help="Minumum clip duration")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=2048, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=128, type=int, help="Ensure the middle x audio files play")
parser.add_argument('-center', dest="CENTER", default="0.5,0.5", help="Center position")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
VOLUME_RANGE = tuple([float(v) for v in a.VOLUME_RANGE.strip().split(",")])
ALPHA_RANGE =  tuple([float(v) for v in a.ALPHA_RANGE.strip().split(",")])
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
END_GRID_W, END_GRID_H = tuple([int(v) for v in a.END_GRID.strip().split("x")])
ZOOM_DUR = a.STEPS * a.BEAT_DUR
ZOOM_EASE = "cubicIn"

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime = initGridComposition(a, GRID_W, GRID_H, stepTime)

cCol, cRow = ((GRID_W-1) * 0.5, (GRID_H-1) * 0.5)
for i, s in enumerate(samples):
    # play in order: center first, clockwise
    samples[i]["distanceFromCenter"] = distance(cCol, cRow, s["col"], s["row"])
    samples[i]["angleFromCenter"] = angleBetween(cCol, cRow, s["col"], s["row"])
    # make clip longer if necessary
    samples[i]["audioDur"] = s["dur"]
    samples[i]["dur"] = s["dur"] if s["dur"] > a.MIN_CLIP_DUR else int(math.ceil(1.0 * a.MIN_CLIP_DUR / s["dur"]) * s["dur"])
    # calculate translate distance
    translateDistance = min(s["width"], s["height"]) * a.TRANSLATE_AMOUNT
    samples[i]["translateAmount"] = translatePoint(0, 0, translateDistance, samples[i]["angleFromCenter"])
    # randomized volume multiplier
    samples[i]["volumeMultiplier"] = pseudoRandom(a.RANDOM_SEED+i, range=(0.33, 1.0))

samples = sorted(samples, key=lambda s: (s["distanceFromCenter"], s["angleFromCenter"]))
samples = addIndices(samples, "playOrder")
samples = addNormalizedValues(samples, "playOrder", "nPlayOrder")
samples = addNormalizedValues(samples, "power", "nPower")
samples = addNormalizedValues(samples, "distanceFromCenter", "nDistanceFromCenter")

# add audio clip properties
for i, s in enumerate(samples):
    audioDur = s["audioDur"]
    samples[i].update({
        "zindex": sampleCount-i,
        "volume": lerp(VOLUME_RANGE, (1.0 - s["nDistanceFromCenter"]) * s["volumeMultiplier"]),
        "fadeOut": getClipFadeDur(audioDur, percentage=0.5, maxDur=-1),
        "fadeIn": getClipFadeDur(audioDur),
        "pan": lerp((-1.0, 1.0), s["nx"]),
        "reverb": a.REVERB
    })

stepTime = logTime(stepTime, "Calculate clip properties")

# limit the number of clips playing
if sampleCount > a.MAX_AUDIO_CLIPS:
    samples = limitAudioClips(samples, a.MAX_AUDIO_CLIPS, "nDistanceFromCenter", keepFirst=a.KEEP_FIRST_AUDIO_CLIPS, invert=True, seed=(a.RANDOM_SEED+2))
    stepTime = logTime(stepTime, "Calculate which audio clips are playing")

# show a viz of which frames are playing
if a.DEBUG:
    for i, s in enumerate(samples):
        samples[i]["alpha"] = 1.0 if s["playAudio"] else 0.2
    clipsToFrame({ "filename": a.OUTPUT_FRAME % "playTest", "width": a.WIDTH, "height": a.HEIGHT, "overwrite": True, "debug": True },
        samplesToClips(samples), loadVidoPixelDataDebug(len(samples)))

# start with everything with minimum alpha
for i, s in enumerate(samples):
    samples[i]["alpha"] = ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

ms = a.PAD_START
fromScale = 1.0
toScale = 1.0 * GRID_W / END_GRID_W
container.queueTween(ms, ZOOM_DUR, ("scale", fromScale, toScale, ZOOM_EASE))

for step in range(a.STEPS):
    nstep = 1.0 * step / a.STEPS

     # temporarily set scale so we can calculate clip visibility for playing audio
    nzoom = ease(nstep, ZOOM_EASE)
    currentScale = lerp((fromScale, toScale), nzoom)
    container.vector.setTransform(scale=(currentScale, currentScale))

    # play kick
    sampler.queuePlay(ms, "kick", index=step, params={
        "volume": 1.5
    })

    visibleClips = [clip for clip in clips if clip.vector.isVisible(a.WIDTH, a.HEIGHT)]
    visibleClipCount = len(visibleClips)

    # play and render waves
    for i, clip in enumerate(visibleClips):
        nprogress = 1.0 * i / visibleClipCount
        clipStartMs = ms + roundInt(a.WAVE_DUR * nprogress)

        # play clip
        if clip.props["playAudio"]:
            clip.queuePlay(clipStartMs, {
                "dur": clip.props["audioDur"],
                "volume": clip.props["volume"],
                "fadeOut": clip.props["fadeOut"],
                "fadeIn": clip.props["fadeIn"],
                "pan": clip.props["pan"],
                "reverb": clip.props["reverb"]
            })

        # move the clip outward then back inward, alpha up then down
        alphaFrom = lerp(ALPHA_RANGE, ease(1.0 - clip.props["nDistanceFromCenter"]))
        alphaTo = ALPHA_RANGE[0]
        renderDur = clip.props["dur"]
        halfLeft = int(renderDur / 2)
        halfRight = (renderDur - halfLeft) * 2
        tx, ty = clip.props["translateAmount"]
        clip.queueTween(clipStartMs, halfLeft, [
            ("translateX", 0, tx, "sin"),
            ("translateY", 0, ty, "sin"),
            ("alpha", alphaTo, alphaFrom, "sin"),
            ("scale", 1.0, a.SCALE_AMOUNT, "sin")
        ])
        clip.queueTween(clipStartMs+halfLeft, halfRight, [
            ("translateX", tx, 0, "sin"),
            ("translateY", ty, 0, "sin"),
            ("alpha", alphaFrom, alphaTo, "sin"),
            ("scale", a.SCALE_AMOUNT, 1.0, "sin")
        ])

    # ms += halfBeatDur
    # play snare
    # sampler.queuePlay(ms, "snare", index=step)

    ms += a.BEAT_DUR

ms += max(0, a.WAVE_DUR-a.BEAT_DUR) # add the remainder from the wave

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

# reset scale
container.vector.setTransform(scale=(1.0, 1.0))
stepTime = logTime(stepTime, "Created video clip sequence")

processComposition(a, clips, ms, sampler, stepTime, startTime)
