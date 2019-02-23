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
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-beatms', dest="BEAT_MS", default=1024, type=int, help="Milliseconds per beat")
parser.add_argument('-margin', dest="CLIP_MARGIN", default=0.5, type=float, help="Margin between clips in pixels")
parser.add_argument('-beats', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide beat, e.g. 1 = 1/2 notes, 2 = 1/4 notes, 3 = 1/8th notes, 4 = 1/16 notes")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-alphar', dest="ALPHA_RANGE", default="0.2,1.0", help="Alpha range")
parser.add_argument('-translate', dest="TRANSLATE_AMOUNT", default=0.8, type=float, help="Amount to translate clip as a percentage of minimum dimension")
parser.add_argument('-scale', dest="SCALE_AMOUNT", default=1.33, type=float, help="Amount to scale clip")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="6x6", help="End size of grid")
parser.add_argument('-zd', dest="ZOOM_DUR", default=500, type=int, help="Zoom duration in milliseconds")
parser.add_argument('-wd', dest="WAVE_DUR", default=8000, type=int, help="Wave duration in milliseconds")
parser.add_argument('-bd', dest="BEAT_DUR", default=6000, type=int, help="Beat duration in milliseconds")
parser.add_argument('-mcd', dest="MIN_CLIP_DUR", default=2000, type=int, help="Minumum clip duration")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=2048, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-keep', dest="KEEP_FIRST_AUDIO_CLIPS", default=64, type=int, help="Ensure the middle x audio files play")
parser.add_argument('-center', dest="CENTER", default="0.5,0.5", help="Center position")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

# parse arguments
VOLUME_RANGE = tuple([float(v) for v in a.VOLUME_RANGE.strip().split(",")])
ALPHA_RANGE =  tuple([float(v) for v in a.ALPHA_RANGE.strip().split(",")])
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
END_GRID_W, END_GRID_H = tuple([int(v) for v in a.END_GRID.strip().split("x")])

# Get video data
startTime = logTime()
stepTime = startTime
_, samples = readCsv(a.INPUT_FILE)
stepTime = logTime(stepTime, "Read CSV")
sampleCount = len(samples)

gridCount = GRID_W * GRID_H
if gridCount > sampleCount:
    print("Not enough samples (%s) for the grid you want (%s x %s = %s). Exiting." % (sampleCount, GRID_W, GRID_H, gridCount))
    sys.exit()
elif gridCount < sampleCount:
    print("Too many samples (%s), limiting to %s" % (sampleCount, gridCount))
    samples = samples[:gridCount]
    sampleCount = gridCount

# Sort by grid
samples = sorted(samples, key=lambda s: (s["gridY"], s["gridX"]))
samples = addIndices(samples)
samples = prependAll(samples, ("filename", a.MEDIA_DIRECTORY))
samples = addGridPositions(samples, GRID_W, a.WIDTH, a.HEIGHT, marginX=a.CLIP_MARGIN, marginY=(a.CLIP_MARGIN*(1.0*a.HEIGHT/a.WIDTH)))

cCol, cRow = ((GRID_W-1) * 0.5, (GRID_H-1) * 0.5)
for i, s in enumerate(samples):
    # play in order: center first, clockwise
    samples[i]["distanceFromCenter"] = distance(cCol, cRow, s["col"], s["row"])
    samples[i]["angleFromCenter"] = angleBetween(cCol, cRow, s["col"], s["row"])
    # make clip longer if necessary
    samples[i]["audioDur"] = s["dur"]
    samples[i]["dur"] = max(s["dur"], a.MIN_CLIP_DUR)
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

if a.DEBUG:
    for i, s in enumerate(samples):
        pixels = np.array([[getRandomColor(i)]])
        samples[i]["framePixelData"] = [pixels]

# show a viz of which frames are playing
if a.DEBUG:
    for i, s in enumerate(samples):
        samples[i]["alpha"] = 1.0 if s["playAudio"] else 0.2
    clipsToFrame({ "filename": a.OUTPUT_FRAME % "playTest", "clips": samples, "width": a.WIDTH, "height": a.HEIGHT, "overwrite": True, "debug": True })

# start with everything with minimum alpha
for i, s in enumerate(samples):
    samples[i]["alpha"] = ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

container = Clip({
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "cache": True
})
for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

ms = a.PAD_START
cols = GRID_W
fromWidth = 1.0 * a.WIDTH / cols * GRID_W
while True:
    zoomSteps = max(1, roundInt(1.0 * cols ** 0.5)) # zoom more steps when we're zoomed out
    cols -= (zoomSteps * 2)
    lastStep = False
    if cols <= END_GRID_W:
        cols = END_GRID_W
        lastStep = True

    waveDur = a.WAVE_DUR
    halfBeatDur = roundInt(a.BEAT_DUR * 0.5)

    # play bass

    visibleClips = [clip for clip in clips if clip.vector.isVisible(a.WIDTH, a.HEIGHT)]
    visibleClipCount = len(visibleClips)

    # play and render waves
    for i, clip in enumerate(visibleClips):
        nprogress = 1.0 * i / visibleClipCount
        clipStartMs = ms + roundInt(waveDur * nprogress)

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

    ms += halfBeatDur

    # play snare

    toWidth = 1.0 * a.WIDTH / cols * GRID_W
    fromScale = container.vector.getScaleFromWidth(fromWidth)
    toScale = container.vector.getScaleFromWidth(toWidth)
    container.queueTween(ms, a.ZOOM_DUR, ("scale", fromScale, toScale, "sin"), sortFrames=False)
    container.vector.setTransform(scale=(toScale, toScale)) # temporarily set scale so we can calculate clip visibility for playing audio
    fromWidth = toWidth

    ms += halfBeatDur

    if lastStep:
        break

# sort frames
container.vector.sortFrames()
for clip in clips:
    clip.vector.sortFrames()

container.vector.setTransform(scale=(1.0, 1.0)) # reset scale
stepTime = logTime(stepTime, "Created video clip sequence")

# get audio sequence
audioSequence = clipsToSequence(clips)
stepTime = logTime(stepTime, "Processed audio clip sequence")

# plotAudioSequence(audioSequence)
# sys.exit()

videoDurationMs = ms
audioDurationMs = getAudioSequenceDuration(audioSequence)
durationMs = max(videoDurationMs, audioDurationMs) + a.PAD_END
print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
print("Total time: %s" % formatSeconds(durationMs/1000.0))

# adjust frames if audio is longer than video
totalFrames = msToFrame(durationMs, a.FPS) if durationMs > videoDurationMs else msToFrame(videoDurationMs, a.FPS)
print("Total frames: %s" % totalFrames)

# get frame sequence
videoFrames = []
print("Making video frame sequence...")
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    videoFrames.append({
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "clips": clips,
        "ms": ms,
        "width": a.WIDTH,
        "height": a.HEIGHT,
        "overwrite": a.OVERWRITE,
        "gpu": a.USE_GPU,
        "debug": a.DEBUG
    })
stepTime = logTime(stepTime, "Processed video frame sequence")

if a.CACHE_VIDEO:
    loadVideoPixelDataFromFrames(videoFrames, clips, a.FPS, a.CACHE_DIR, a.CACHE_FILE, a.VERIFY_CACHE)

if not a.VIDEO_ONLY and (not os.path.isfile(a.AUDIO_OUTPUT_FILE) or a.OVERWRITE):
    mixAudio(audioSequence, durationMs, a.AUDIO_OUTPUT_FILE)
    stepTime = logTime(stepTime, "Mix audio")

if not a.AUDIO_ONLY:
    processFrames(videoFrames, threads=a.THREADS)
    stepTime = logTime(stepTime, "Process video")

if not a.AUDIO_ONLY:
    audioFile = a.AUDIO_OUTPUT_FILE if not a.VIDEO_ONLY else False
    compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile)

logTime(startTime, "Total execution time")
