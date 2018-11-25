# -*- coding: utf-8 -*-

# Instructions:
# 1. Place all scenes in a grid
# 2. Pan down if the grid goes off-screen
# 3. Duration is the longer of: (1) the length of the longest scene or (2) the time it takes to pan down
# 4. Loop shorter scenes

# python -W ignore grid.py -cols 4 -width 640 -height 480 -pps 60

import argparse
import csv
import inspect
import json
import math
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
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
parser.add_argument('-in', dest="INPUT_FILE", default="../tmp/scenes.csv", help="Input file")
parser.add_argument('-dir', dest="VIDEO_DIRECTORY", default="../media/sample/", help="Input file")
parser.add_argument('-cols', dest="COLUMNS", default=8, type=int, help="Number of columns in the matrix")
parser.add_argument('-aspect', dest="ASPECT_RATIO", default="16:9", help="Aspect ratio of each cell")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
parser.add_argument('-pps', dest="PIXELS_PER_SECOND", default=30, type=int, help="Numper of pixels to move the composition per second (if necessary)")
parser.add_argument('-frames', dest="SAVE_FRAMES", default=0, type=int, help="Save frames?")
parser.add_argument('-loop', dest="LOOP", default=1, type=int, help="Loop around to the beginning frame?")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="../tmp/grid/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/grid.mp4", help="Output media file")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing frames?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
VIDEO_DIRECTORY = args.VIDEO_DIRECTORY
COLUMNS = args.COLUMNS
ASPECT_W, ASPECT_H = tuple([int(p) for p in args.ASPECT_RATIO.split(":")])
ASPECT_RATIO = 1.0 * ASPECT_W / ASPECT_H
WIDTH = args.WIDTH
HEIGHT = args.HEIGHT
FPS = args.FPS
PIXELS_PER_SECOND = args.PIXELS_PER_SECOND
SAVE_FRAMES = args.SAVE_FRAMES > 0
LOOP = args.LOOP > 0
OUTPUT_FRAME = args.OUTPUT_FRAME
OUTPUT_FILE = args.OUTPUT_FILE
THREADS = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
OVERWRITE = args.OVERWRITE > 0
AUDIO_OUTPUT_FILE = OUTPUT_FILE.replace(".mp4", ".mp3")

makeDirectories([OUTPUT_FRAME, OUTPUT_FILE])

# Calculate the cell width and height
cellW = 1.0 * WIDTH / COLUMNS
cellH = cellW / ASPECT_RATIO

# get unique video files
print("Reading and resizing clips...")
fieldNames, scenes = readCsv(INPUT_FILE)
sceneCount = len(scenes)
print("%s scenes found" % sceneCount)
rowCount = ceilInt(1.0*sceneCount/COLUMNS)
rowsPerScreen = 1.0 * HEIGHT / cellH
print("%s rows with %s rows per screen" % (rowCount, roundInt(rowsPerScreen)))

# see if we need to move the composition over time
totalHeight = roundInt(rowCount * cellH)
isMoving = totalHeight > HEIGHT

# if we are moving and we want to loop, duplicate scenes
if isMoving and LOOP:
    # add empty scenes to fill gaps
    remainder = sceneCount % COLUMNS
    if remainder > 0:
        scenes += [None for s in range(remainder)]
    # add scenes in the beginning to the end
    rowsToAdd = int(rowsPerScreen)
    scenesToAdd = [s.copy() for s in scenes[:(rowsToAdd * COLUMNS)]]
    scenes += scenesToAdd
    # re-calculate height
    sceneCount = len(scenes)
    rowCount = ceilInt(1.0*sceneCount/COLUMNS)
    totalHeight = roundInt(rowCount * cellH)
    print("%s scenes with looping" % sceneCount)

# calculate target duration based on the longest scene
targetDuration = max([s["dur"] for s in scenes if s])

# if moving, see if that duration is longer than longest scene
movePixels = 0
if isMoving:
    print("Will be moving")
    movePixels = totalHeight - HEIGHT
    moveDuration = roundInt(1.0 * movePixels / PIXELS_PER_SECOND * 1000)
    targetDuration = moveDuration

targetFrames = int(targetDuration / 1000.0 * FPS)
print("Total duration: %s" % formatSeconds(targetDuration/1000))
print("%s frames" % targetFrames)

# assign positions to scenes
for i, scene in enumerate(scenes):
    if not scene:
        continue
    scenes[i]["y"] = int(i / COLUMNS) * cellH
    scenes[i]["x"] = int(i % COLUMNS) * cellW

params = []
padZeros = len(str(targetFrames))

for frame in range(targetFrames):
    progress = 1.0 * frame / (targetFrames-1)
    second = 1.0 * frame / FPS
    offsetY = progress * movePixels

    clips = []
    for scene in scenes:
        if not scene:
            continue
        y = scene["y"] - offsetY
        # skip if we are off screen
        if y >= HEIGHT or y <= -cellH:
            continue
        sceneStart = scene["start"] / 1000.0
        sceneDur = scene["dur"] / 1000.0
        remainder = second % sceneDur
        t = sceneStart + remainder
        clips.append({
            "filename": VIDEO_DIRECTORY + scene["filename"],
            "t": t,
            "x": scene["x"],
            "y": y,
            "w": cellW,
            "h": cellH
        })

    filename = OUTPUT_FRAME % str(frame+1).zfill(padZeros)
    params.append({
        "filename": filename,
        "saveFrame": True,
        "clips": clips,
        "width": WIDTH,
        "height": HEIGHT,
        "overwrite": OVERWRITE
    })

# add alpha via sound data
print("Analyzing sound...")
timecodes = []
for i, p in enumerate(params):
    for j, c in enumerate(p["clips"]):
        timecodes.append({
            "index": (i, j),
            "filename": c["filename"],
            "t": c["t"]
        })
powerData = gePowerFromTimecodes(timecodes, method="mean")
alphaRange = (0.1, 1.0)
for i, p in enumerate(params):
    for j, c in enumerate(p["clips"]):
        params[i]["clips"][j]["alpha"] = lerp(alphaRange, powerData[(i, j)])

print("Generating frames...")

if (THREADS > 1):
    pool = ThreadPool(THREADS)
    results = pool.map(clipsToFrame, params)
    pool.close()
    pool.join()
else:
    for i, p in enumerate(params):
        clipsToFrame(p)
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*i/(targetFrames-1)*100,1))
        sys.stdout.flush()

# create instructions for the audio track
if not os.path.isfile(AUDIO_OUTPUT_FILE) or OVERWRITE:
    instructions = []
    halfH = HEIGHT * 0.5
    lowerBounds = halfH - halfH * 0.5
    upperBounds = halfH + halfH * 0.5
    for scene in scenes:
        if not scene:
            continue
        sceneDur = scene["dur"] / 1000.0
        elapsed = 0.0
        pan = (scene["x"] + cellW * 0.5) / WIDTH * 2.0 - 1.0
        sceneY = scene["y"] + cellH * 0.5
        while elapsed < targetDuration:
            progress = elapsed / targetDuration
            y = lerp((sceneY, sceneY-movePixels), progress)
            if lowerBounds < y < upperBounds:
                volume = norm(y, (lowerBounds, upperBounds)) * 2.0
                if volume > 1.0:
                    volume = abs(volume - 2.0)
                instructions.append({
                    "ms": roundInt(elapsed*1000),
                    "filename": VIDEO_DIRECTORY + scene["filename"],
                    "start": scene["start"],
                    "dur": scene["dur"],
                    "pan": pan,
                    "volume": volume
                })
            elapsed += sceneDur
    mixAudio(instructions, targetDuration, AUDIO_OUTPUT_FILE)
else:
    print("%s already exists, skipping..." % AUDIO_OUTPUT_FILE)

compileFrames(OUTPUT_FRAME, FPS, OUTPUT_FILE, padZeros, audioFile=AUDIO_OUTPUT_FILE)
