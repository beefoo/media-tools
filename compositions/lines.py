# -*- coding: utf-8 -*-

# Instructions:
# 1. Place clips in a grid, sorting vertically by frequency and horizontally by power
# 2. Play clips from left-to-right
# 3. Play clips from right-to-left
# 4. Play clips from top-to-bottom
# 5. Play clips from bottom-to-top
# 6. Play clips from left-to-right and right-to-left, simultaneously
# 7. Play clips from top-to-bottom and bottom-to-top, simultaneously
# 8. Play clips from left-to-right and top-to-bottom, simultaneously
# 9. Play clips from right-to-left and bottom-to-top, simultaneously
# 10. Play clips from left-to-right and bottom-to-top, simultaneously
# 11. Play clips from right-to-left and top-to-bottom, simultaneously
# 12. Play clips from left-to-right, right-to-left, top-to-bottom, bottom-to-top, simultaneously

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-pand', dest="PAN_DURATION", default=3.0, type=float, help="Pan duration in seconds")
parser.add_argument('-paused', dest="PAUSE_DURATION", default=3.0, type=float, help="Pause duration in seconds")
parser.add_argument('-faded', dest="FADE_DURATION", default=1.0, type=float, help="Clip fade out duration in seconds")
parser.add_argument('-grid', dest="GRID", default="192x108", help="Grid dimensions")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

GRID_COLS, GRID_ROWS = tuple([int(d) for d in a.GRID.split("x")])
COUNT = GRID_COLS * GRID_ROWS
FRAMES_PER_PAN = roundInt(a.FPS * a.PAN_DURATION)
FRAMES_PER_PAUSE = roundInt(a.FPS * a.PAUSE_DURATION)
ALPHA_STEP_PER_SECOND = 1.0 / a.FADE_DURATION
ALPHA_STEP_PER_FRAME = ALPHA_STEP_PER_SECOND / a.FPS

totalDuration = (a.FADE_DURATION + a.PAUSE_DURATION) * 11
totalFrames = roundInt(totalDuration * a.FPS)

# get unique video files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
print("Loaded %s samples" % sampleCount)

if sampleCount < COUNT:
    print("Not enough samples; have %s, need %s" % (sampleCount, COUNT))
    sys.exit()

# remove flat samples
if sampleCount > COUNT:
    samples = sortBy(samples, ("flatness", "asc"))
    samples = samples[:COUNT]

# 1. Place clips in a grid, sorting vertically by frequency and horizontally by power
samples = sortMatrix(samples, sortY=("hz", "asc"), sortX=("power", "asc"), rowCount=GRID_COLS)
samples = addIndices(samples)
samples = addGridPositions(samples, GRID_COLS, a.WIDTH, a.HEIGHT)

# add sorter keys within each row and column by duration; this will determine the order at which clips will play
unit = 1.0 / GRID_ROWS
for row in range(GRID_ROWS):
    base = 1.0 * row / GRID_ROWS
    rowSamples = samples[row*GRID_COLS:(row+1)*GRID_COLS]
    rowSamples = sorted(rowSamples, key=lambda k: k["dur"], reverse=True)
    for i, s in enumerate(rowSamples):
        samples[s["index"]]["rowSort"] = base + 1.0 * i / (GRID_COLS-1) * unit
unit = 1.0 / GRID_COLS
for col in range(GRID_COLS):
    base = 1.0 * col / GRID_COLS
    colSamples = [s for s in samples if s["col"]==col]
    colSamples = sorted(colSamples, key=lambda k: k["dur"], reverse=True)
    for i, s in enumerate(colSamples):
        samples[s["index"]]["colSort"] = base + 1.0 * i / (GRID_ROWS-1) * unit

# row = samples[-GRID_COLS:]
# pprint([c["rowSort"] for c in row])
# sys.exit()

audioSequence = []
videoFrames = []
currentFrame = 1
samples = updateAll(samples, ("played", False))
samples = updateAll(samples, ("alpha", 0.0))

def clipsToFrameData(frame, clips):
    global a
    global totalFrames
    return {
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "clips": clips,
        "width": a.WIDTH,
        "height": a.HEIGHT
    }

def frameToAudioInstruction(frame, sample):
    global a
    pan = lerp((-1.0, 1.0), 1.0 * (sample["x"] + sample["w"] * 0.5) / a.WIDTH)
    return {
        "filename": a.VIDEO_DIRECTORY + sample["filename"],
        "ms": frameToMs(frame, a.FPS),
        "start": sample["start"],
        "dur": sample["dur"],
        "pan": pan
    }

def sampleToClipData(sample):
    global a
    return {
        "filename": a.VIDEO_DIRECTORY + sample["filename"],
        "x": sample["x"],
        "y": sample["y"],
        "w": sample["w"],
        "h": sample["h"],
        "alpha": sample["alpha"]
    }

# 2. Play clips from left-to-right
for frame in range(FRAMES_PER_PAN):
    panProgress = 1.0 * frame / (FRAMES_PER_PAN-1.0)
    clips = []
    for i, s in enumerate(samples):
        if panProgress >= s["colSort"] and not s["played"]:
            audioSequence.append(frameToAudioInstruction(currentFrame+frame, s))
            samples[s["index"]]["played"] = True
            samples[s["index"]]["alpha"] = 1.0
        alpha = samples[s["index"]]["alpha"]
        if alpha > 0.0:
            clips.append(sampleToClipData(samples[s["index"]]))
            samples[s["index"]]["alpha"] = max(0.0, alpha - ALPHA_STEP_PER_FRAME)
    videoFrames.append(clipsToFrameData(currentFrame+frame, clips))

currentFrame += FRAMES_PER_PAN
samples = updateAll(samples, ("played", False))

def doPause():
    global videoFrames
    global samples
    global currentFrame

    for frame in range(FRAMES_PER_PAUSE):
        pauseProgress = 1.0 * frame / (FRAMES_PER_PAUSE-1.0)
        clips = []
        for i, s in enumerate(samples):
            if s["alpha"] > 0.0:
                clips.append(sampleToClipData(s))
                samples[s["index"]]["alpha"] = max(0.0, s["alpha"] - ALPHA_STEP_PER_FRAME)
        videoFrames.append(clipsToFrameData(currentFrame+frame, clips))

doPause()
currentFrame += FRAMES_PER_PAUSE

videoDurationMs = frameToMs(currentFrame, a.FPS)
audioDurationMs = getAudioSequenceDuration(audioSequence)
durationMs = max(videoDurationMs, audioDurationMs)
print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
print("Total time: %s" % formatSeconds(durationMs/1000.0))

if not a.VIDEO_ONLY:
    mixAudio(audioSequence, audioDurationMs, a.AUDIO_OUTPUT_FILE)

if not a.AUDIO_ONLY:
    processFrames(videoFrames, threads=a.THREADS)

if not a.AUDIO_ONLY:
    audioFile = a.AUDIO_OUTPUT_FILE if not a.VIDEO_ONLY else False
    compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(currentFrame), audioFile=audioFile)
