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
parser.add_argument('-margin', dest="CLIP_MARGIN", default=1, type=int, help="Margin between clips in pixels")
parser.add_argument('-beats', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide beat, e.g. 1 = 1/2 notes, 2 = 1/4 notes, 3 = 1/8th notes, 4 = 1/16 notes")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.2,1.0", help="Volume range")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-zoom0', dest="ZOOM_START", default=1.0, type=float, help="Zoom start level; 1.0 = completely zoomed in, 0.0 = completely zoomed out")
parser.add_argument('-zoom1', dest="ZOOM_END", default=0.0, type=float, help="Zoom start level; 1.0 = completely zoomed in, 0.0 = completely zoomed out")
parser.add_argument('-zd', dest="ZOOM_DUR", default=500, type=int, help="Zoom duration in milliseconds")
parser.add_argument('-wd', dest="WAVE_DUR", default=2000, type=int, help="Wave duration in milliseconds")
parser.add_argument('-mcd', dest="MIN_CLIP_DUR", default=2000, type=int, help="Minumum clip duration")
parser.add_argument('-maxa', dest="MAX_AUDIO_CLIPS", default=4096, type=int, help="Maximum number of audio clips to play")
parser.add_argument('-center', dest="CENTER", default="0.5,0.5", help="Center position")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

# parse arguments
VOLUME_RANGE = [float(v) for v in a.VOLUME_RANGE.strip().split(",")]
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
UNIT_MS = roundInt(2 ** (-a.BEAT_DIVISIONS) * a.BEAT_MS)
print("Smallest unit: %ss" % UNIT_MS)
ZOOM_STEPS = int(min(GRID_W, GRID_H) / 2) - 1
ZOOM_START = int(1.0 * a.ZOOM_START * (ZOOM_STEPS-1))
ZOOM_END = int(1.0 * a.ZOOM_END * (ZOOM_STEPS-1))
CENTER_NX, CENTER_NY = tuple([float(v) for v in a.CENTER.strip().split(",")])
CENTER_IX, CENTER_IY = (int(CENTER_NX * (GRID_W-1)), int(CENTER_NY * (GRID_H-1)))
CENTER_X, CENTER_Y = (int(CENTER_NX * (a.WIDTH-1)), int(CENTER_NY * (a.HEIGHT-1)))
FRAMES_PER_ZOOM = int(a.ZOOM_DUR / 1000.0 * a.FPS)
FRAMES_PER_WAVE = int(a.WAVE_DUR / 1000.0 * a.FPS)

# Get video data
startTime = logTime()
_, samples = readCsv(a.INPUT_FILE)
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
samples = addGridPositions(samples, GRID_W, a.WIDTH, a.HEIGHT, marginX=a.CLIP_MARGIN, marginY=a.CLIP_MARGIN)

cCol, cRow = (GRID_W * 0.5, GRID_H * 0.5)
for i, s in enumerate(samples):
    # play in order: center first, clockwise
    samples[i]["distanceFromCenter"] = distance(cCol, cRow, s["col"], s["row"])
    samples[i]["angleFromCenter"] = angleBetween(cCol, cRow, s["col"], s["row"])
    # make clip longer if necessary
    samples[i]["fadeOut"] = a.MIN_CLIP_DUR if s["dur"] < a.MIN_CLIP_DUR else getClipFadeDur(s["dur"], percentage=0.5)
    samples[i]["dur"] = max(s["dur"], a.MIN_CLIP_DUR)
samples = sorted(samples, key=lambda s: (s["distanceFromCenter"], s["angleFromCenter"]))
samples = addIndices(samples, "playOrder")
samples = addNormalizedValues(samples, "playOrder", "nPlayOrder")
samples = addNormalizedValues(samples, "power", "nPower")
samples = addNormalizedValues(samples, "distanceFromCenter", "nDistanceFromCenter")

# limit the number of clips playing
if sampleCount > a.MAX_AUDIO_CLIPS:
    samples = limitAudioClips(samples, a.MAX_AUDIO_CLIPS, "nDistanceFromCenter", keepFirst=64, invert=True, seed=(a.RANDOM_SEED+2))

if a.DEBUG:
    for i, s in enumerate(samples):
        pixels = np.array([[getRandomColor(i)]])
        samples[i]["framePixelData"] = [pixels]

# show a viz of which frames are playing
if a.DEBUG:
    for i, s in enumerate(samples):
        samples[i]["alpha"] = 1.0 if s["playAudio"] else 0.2
    clipsToFrame({ "filename": a.OUTPUT_FRAME % "playTest", "clips": samples, "width": a.WIDTH, "height": a.HEIGHT, "overwrite": True, "debug": True })

clips = samplesToClips(samples)
stepTime = logTime(startTime, "Samples to clips")
# clips = np.array(clips)
# clips = np.reshape(clips, (GRID_H, GRID_W))

container = Clip({
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "cache": True
})
for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

ms = 0
cols = GRID_W
fromWidth = 1.0 * a.WIDTH / cols * GRID_W
halfWaveDur = roundInt(a.WAVE_DUR * 0.5)
while cols >= 2:

    # play bass

    # play and render waves
    for i, clip in enumerate(clips):
        clipStartMs = ms + roundInt(a.WAVE_DUR * clip.props["nPlayOrder"])

    ms += halfWaveDur

    zoomSteps = max(1, roundInt(1.0 * cols ** 0.25)) # play more zoom steps when we're zoomed
    zoomDivisionIncrement = getDivisionIncrement(zoomSteps)
    zoomDivisionMs = roundInt(1.0 * halfWaveDur * zoomDivisionIncrement)
    zoomDur = min(a.ZOOM_DUR, zoomDivisionMs)
    for z in range(zoomSteps):
        cols -= 2
        if cols < 2:
            break

        # play snare

        # zoom container
        offset = getOffset(zoomSteps, z)
        offsetMs = roundInt(offset * halfWaveDur)
        zoomStartMs = ms + offsetMs
        toWidth = 1.0 * a.WIDTH / cols * GRID_W
        container.queueTween(zoomStartMs, zoomDur, ("scale", container.vector.getScaleFromWidth(fromWidth), container.vector.getScaleFromWidth(toWidth), "sin"))
        fromWidth = toWidth

    ms += halfWaveDur

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
    loadVideoPixelDataFromFrames(videoFrames, clips, a.FPS, a.CACHE_FILE)

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
