# -*- coding: utf-8 -*-

# Instructions:
# 1. Place clips in a grid, sorting vertically by pitch and horizontally by volume
# 2. Play clips from left-to-right
# 3. Play clips from right-to-left
# 4. Play clips from top-to-bottom
# 5. Play clips from bottom-to-top
# 6. Do steps 4 and 5 simultaneously
# 7. Do steps 2 and 3 simultaneously
# 8. Do steps 6 and 7 simultaneously

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
from lib.clip import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-pand', dest="PAN_DURATION", default=12.0, type=float, help="Pan duration in seconds")
parser.add_argument('-paused', dest="PAUSE_DURATION", default=2.0, type=float, help="Pause duration in seconds")
parser.add_argument('-grid', dest="GRID", default="192x108", help="Grid dimensions")
parser.add_argument('-vgrid', dest="VISIBLE_GRID", default="96x54", help="Grid dimensions")
parser.add_argument('-fadem', dest="FADE_MULTIPLIER", default=3, type=int, help="e.g. 3 = fade in/out 3x the duration of the clip")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

GRID_COLS, GRID_ROWS = tuple([int(d) for d in a.GRID.split("x")])
VGRID_COLS, VGRID_ROWS = tuple([int(d) for d in a.VISIBLE_GRID.split("x")])
COUNT = GRID_COLS * GRID_ROWS
VCOUNT = VGRID_COLS * VGRID_ROWS
VWIDTH = a.WIDTH
VHEIGHT = a.HEIGHT
WIDTH = roundInt(VWIDTH * (1.0 * GRID_COLS / VGRID_COLS))
HEIGHT = roundInt(VHEIGHT * (1.0 * GRID_ROWS / VGRID_ROWS))
VOFFSET_X = -(WIDTH - VWIDTH) / 2
VOFFSET_Y = -(HEIGHT - VHEIGHT) / 2
VOFFSET_NX = -1.0 * VOFFSET_X / WIDTH
VOFFSET_NY = -1.0 * VOFFSET_Y / HEIGHT
FRAMES_PER_PAN = roundInt(a.FPS * a.PAN_DURATION)
FRAMES_PER_PAUSE = roundInt(a.FPS * a.PAUSE_DURATION)
FADE_IN_OUT_SECONDS = 6.0
FRAMES_PER_FADE = roundInt(a.FPS * FADE_IN_OUT_SECONDS)
MIN_ALPHA = 0.2

totalDuration = (a.PAN_DURATION + a.PAUSE_DURATION) * 7 + FADE_IN_OUT_SECONDS * 2
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

# Add dir to filenames
samples = prependAll(samples, ("filename", a.VIDEO_DIRECTORY))

# 1. Place clips in a grid, sorting vertically by pitch and horizontally by volume
samples = sortMatrix(samples, sortY=("hz", "asc"), sortX=("power", "asc"), rowCount=GRID_COLS)
samples = addIndices(samples)
samples = addGridPositions(samples, GRID_COLS, WIDTH, HEIGHT, offsetX=VOFFSET_X, offsetY=VOFFSET_Y)

# Pre-process pixel data for videos
if a.CACHE_VIDEO:
    samples = loadVideoPixelData(samples, a.FPS, filename=a.CACHE_FILE, width=a.WIDTH, height=a.HEIGHT)

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

# create clips, viewport, and container
clips = samplesToClips(samples)
clips = updateClipStates(clips, [("played", False)])
currentFrame = 1

def getAlphaMultiplier(clip):
    global a
    offset = VOFFSET_NY
    alpha = 0.0
    n = 1.0 * clip.props["row"] / (GRID_ROWS-1)
    if n >= offset and n <= (1.0-offset):
        n = norm(n, (offset, 1.0-offset))
        alpha = easeInOut(n)
    return alpha

def getPan(clip):
    global a
    return lerp((-1.0, 1.0), 1.0 * clip.props["col"] / (GRID_COLS-1))

def getVolume(clip, key1, denom1, key2, denom2, offset1=0.0):
    global a
    n1 = 1.0 * clip.props[key1] / (denom1-1)
    volume1 = easeInOut(n1)
    if offset1 > 0.0 and (n1 < offset1 or n1 > (1.0-offset1)):
        volume1 = 0.0
    volume2 = easeInOut(1.0 * clip.props[key2] / (denom2-1))
    return volume1 * volume2 * a.VOLUME

def doFade(frameStart, fromAlpha, toAlpha, fadeDur):
    global a
    global clips
    ms = frameToMs(frameStart, a.FPS)
    for i, clip in enumerate(clips):
        alphaMultiplier = getAlphaMultiplier(clip)
        clip.queueTween(ms, dur=roundInt(fadeDur*1000), tweens=("alpha", alphaMultiplier*fromAlpha, alphaMultiplier*toAlpha, "sin"))

def doLine(frameStart, propKey, volumeProps, reverse=False):
    global a
    global clips
    for frame in range(FRAMES_PER_PAN):
        panProgress = 1.0 * frame / (FRAMES_PER_PAN-1.0)
        if reverse:
            panProgress = 1.0 - panProgress
        ms = frameToMs(frameStart+frame, a.FPS)
        for i, clip in enumerate(clips):
            value = clip.props[propKey]
            if (not reverse and panProgress >= value or reverse and panProgress <= value) and not clip.state["played"]:
                key1, denom1, key2, denom2, offset1 = volumeProps
                volume = getVolume(clip, key1, denom1, key2, denom2, offset1)
                pan = getPan(clip)
                alphaMultiplier = getAlphaMultiplier(clip)
                fadeDur = a.FADE_MULTIPLIER * clip.dur
                fadeInDur = min(100, fadeDur/10)
                clip.setState("played", True)
                clip.queueTween(ms, dur=fadeInDur, tweens=("alpha", alphaMultiplier*MIN_ALPHA, alphaMultiplier, "sin"))
                clip.queueTween(ms+fadeInDur, dur=fadeDur-fadeInDur, tweens=("alpha", alphaMultiplier, alphaMultiplier*MIN_ALPHA, "sin"))
                clip.queuePlay(ms, {"volume": volume, "pan": pan})
    clips = updateClipStates(clips, [("played", False)])

# Slowly fade clips in to partial opacity
doFade(currentFrame, 0.0, MIN_ALPHA, FADE_IN_OUT_SECONDS)
currentFrame += FRAMES_PER_FADE

# 2. Play clips from left-to-right
doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY))
currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE

# # 3. Play clips from right-to-left
# doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY), reverse=True)
# currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE
#
# # 4. Play clips from top-to-bottom
# doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX))
# currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE

# 5. Play clips from bottom-to-top
doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX), reverse=True)
currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE

# # 6. Do steps 4 and 5 simultaneously
# doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX))
# doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX), reverse=True)
# currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE
#
# # 7. Do steps 2 and 3 simultaneously
# doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY))
# doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY), reverse=True)
# currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE
#
# # 8. Do steps 6 and 7 simultaneously
# doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY))
# doLine(currentFrame, "colSort", ("row", GRID_ROWS, "col", GRID_COLS, VOFFSET_NY), reverse=True)
# doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX))
# doLine(currentFrame, "rowSort", ("col", GRID_COLS, "row", GRID_ROWS, VOFFSET_NX), reverse=True)
# currentFrame += FRAMES_PER_PAN + FRAMES_PER_PAUSE

# Slowly fade clips out
doFade(currentFrame, MIN_ALPHA, 0.0, FADE_IN_OUT_SECONDS)
currentFrame += FRAMES_PER_FADE

# get audio sequence
audioSequence = []
for clip in clips:
    for play in clip.plays:
        start, end, params = play
        p = {
            "filename": clip.filename,
            "ms": start,
            "start": clip.start,
            "dur": clip.dur,
            "fadeOut": clip.dur
        }
        p.update(params)
        audioSequence.append(p)

videoDurationMs = frameToMs(currentFrame, a.FPS)
audioDurationMs = getAudioSequenceDuration(audioSequence)
durationMs = max(videoDurationMs, audioDurationMs)
print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
print("Total time: %s" % formatSeconds(durationMs/1000.0))

# adjust frames if audio is longer than video
totalFrames = msToFrame(durationMs, a.FPS) if durationMs > videoDurationMs else currentFrame
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
        "gpu": a.USE_GPU
    })

# sys.exit()

if not a.VIDEO_ONLY and (not os.path.isfile(a.AUDIO_OUTPUT_FILE) or a.OVERWRITE):
    mixAudio(audioSequence, durationMs, a.AUDIO_OUTPUT_FILE)

if not a.AUDIO_ONLY:
    processFrames(videoFrames, threads=a.THREADS)

if not a.AUDIO_ONLY:
    audioFile = a.AUDIO_OUTPUT_FILE if not a.VIDEO_ONLY else False
    compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile)
