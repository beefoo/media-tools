# -*- coding: utf-8 -*-

import argparse
import inspect
from matplotlib import pyplot as plt
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from floydlib import *
from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="", help="Input video csv file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="", help="Path to videos folder")
parser.add_argument('-masks', dest="INPUT_MASKS", default="", help="Path to png masks folder")
parser.add_argument('-layout', dest="INPUT_LAYOUT", default="", help="Path to layout svg file")
parser.add_argument('-frames', dest="OUTPUT_FRAME", default="tmp/floyd_frames/frame.%s.png", help="Path to frames directory")
parser.add_argument('-width', dest="WIDTH", default=3840, type=int, help="Output width")
parser.add_argument('-height', dest="HEIGHT", default=2160, type=int, help="Output height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Frames per second")
parser.add_argument('-dur', dest="DURATION", default=60.0, type=float, help="Output duration in seconds")
parser.add_argument('-mdb', dest="MATCH_DB", default=-16.0, type=float, help="Each track should match this decibel level")
parser.add_argument('-awindow', dest="AUDIO_WINDOW_SIZE", default=20, type=int, help="This many tracks to play at once")
parser.add_argument('-db', dest="MASTER_DB", default=0.0, type=float, help="Apply +/- db to final master track")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/floyd_viz.mp4", help="Path to output file")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display details?")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Spit out just one frame?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames / audio?")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rows = prependAll(rows, ("filename", a.MEDIA_DIRECTORY, "filepath"))

for i, row in enumerate(rows):
    videoDur = int(row["duration"] * 1000)
    start = parseTimeMs(row["start"])
    end = parseTimeMs(row["end"])
    if end <= 0:
        end = videoDur
    nstart = 1.0 * start / videoDur
    nend = 1.0 * end / videoDur
    rows[i]["start"] = start
    rows[i]["end"] = end
    rows[i]["nstart"] = nstart
    rows[i]["nend"] = nend
    rows[i]["clipDuration"] = end - start
    rows[i]["duration"] = videoDur

# Make sure output dirs exist
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

durationMs = int(a.DURATION*1000)
totalFrames = msToFrame(durationMs, a.FPS)
totalFrames = int(ceilToNearest(totalFrames, a.FPS))
print("Total frames: %s" % totalFrames)
durationMs = frameToMs(totalFrames, a.FPS)

frames = []
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    frames.append({
        "frame": frame,
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "ms": ms,
        "width": a.WIDTH,
        "height": a.HEIGHT
    })

# read svg layout file
layout = parseLayoutFile(a.INPUT_LAYOUT)
layoutLookup = createLookup(layout, "id")

# read mask and video files
maskFiles = getFilenames(a.INPUT_MASKS)
states = []
print("Loading masks...")
for fn in maskFiles:
    id = getBasename(fn)
    if id not in layoutLookup:
        print("Could not find %s in layout" % id)
        continue
    stateLayout = layoutLookup[id]
    items = [item for item in rows if item["state"]==id]
    if len(items) < 1:
        print("Could not find items for %s" % id)
        continue
    baseImage = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(255, 255, 255))
    image = Image.open(fn)
    width, height = image.size
    baseImage.paste(image, (roundInt(stateLayout["x"]), roundInt(stateLayout["y"])))
    baseImage = baseImage.convert("L")
    items = sorted(items, key=lambda item: item["priority"])
    states.append({
        "mask": baseImage,
        "x": roundInt(stateLayout["x"]),
        "y": roundInt(stateLayout["y"]),
        "width": width,
        "height": height,
        "item": items[0]
    })

if a.DEBUG:
    frames = [frames[0]]

def processFrame(frame):
    global a
    global states

    if os.path.isfile(frame["filename"]):
        return True

    baseImage = Image.new(mode="RGB", size=(frame["width"], frame["height"]), color=(0, 0, 0))
    print("Processing %s..." % frame["filename"])

    for state in states:
        maskImg = state["mask"]
        maskW, maskH = (state["width"], state["height"])
        item = state["item"]

        # retrieve image at an offset time
        msOffset = roundInt(1.0 * item["offset"] * item["clipDuration"])
        itemMs = (frame["ms"] + msOffset) % item["clipDuration"]
        ntime = 1.0 * itemMs / item["clipDuration"]
        ntime = lerp((item["nstart"], item["nend"]), ntime)
        itemImg = getVideoClipImageFromFile(item["filepath"], nt=ntime)

        # crop the image based on mask
        itemW, itemH = itemImg.size
        if item["scale"] > 1.0:
            scaledW = roundInt(itemW * item["scale"])
            scaledH = roundInt(itemH * item["scale"])
            scaledImg = itemImg.resize((scaledW, scaledH))
            x = roundInt((scaledW-itemW)*item["anchorX"])
            y = roundInt((scaledH-itemH)*item["anchorY"])
            itemImg = scaledImg.crop((x, y, x+itemW, y+itemH))
        croppedImg = fillImage(itemImg, maskW, maskH, anchorX=item["anchorX"], anchorY=item["anchorY"])

        # mask and paste the image
        itemBaseImage = Image.new(mode="RGB", size=(frame["width"], frame["height"]), color=(0, 0, 0))
        itemBaseImage.paste(croppedImg, (state["x"], state["y"]))
        baseImage = Image.composite(baseImage, itemBaseImage, maskImg)

    baseImage.save(frame["filename"])
    print("Saved %s." % frame["filename"])
    return True

print("Starting frame processing...")
pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(processFrame, frames)
pool.close()
pool.join()

print("Finished processing frames")

if a.DEBUG:
    sys.exit()

audioFilename = replaceFileExtension(a.OUTPUT_FILE, ".mp3")
if not os.path.isfile(audioFilename) or a.OVERWRITE:
    stateCount = len(states)
    steps = stateCount
    stepDurationMs = roundInt(1.0 * durationMs / steps)
    instructions = []
    for i in range(steps):
        stepMs = roundInt(1.0 * durationMs / steps * i)
        stepEndMs = stepMs + stepDurationMs
        stepStates = []
        if i < stateCount-a.AUDIO_WINDOW_SIZE:
            stepStates = states[i:i+a.AUDIO_WINDOW_SIZE]
        else:
            leftover = a.AUDIO_WINDOW_SIZE - (stateCount-i)
            stepStates = states[i:] + states[:leftover]
            if len(stepStates) != a.AUDIO_WINDOW_SIZE:
                print("Window size error: %s" % len(stepStates))
                sys.exit()

        for j, state in enumerate(stepStates):
            item = state["item"]
            # items in the center are the loudest
            nvolume = 1.0 * j / (a.AUDIO_WINDOW_SIZE - 1)
            nvolume = ease(nvolume, invert=True)
            nvolume = lerp((0.25, 1.0), nvolume)
            # determine item start ms
            msOffset = roundInt(item["offset"] * item["clipDuration"])
            itemMs = (stepMs + msOffset) % item["clipDuration"] + item["start"]
            # loop audio for duration of step
            playedMs = 0
            ms = stepMs
            while playedMs < stepDurationMs:
                dur = item["clipDuration"] - itemMs
                dur = min(dur, stepDurationMs-playedMs)
                if dur < 1:
                    break
                instruction = {
                    "ms": roundInt(ms),
                    "filename": item["filepath"],
                    "start": itemMs,
                    "dur": dur,
                    "matchDb": a.MATCH_DB,
                    "volume": nvolume
                }
                instructions.append(instruction)
                playedMs += dur
                ms += dur
                itemMs = (ms + msOffset) % item["clipDuration"] + item["start"]

    mixAudio(instructions, durationMs, audioFilename, masterDb=a.MASTER_DB)
else:
    print("%s already exists." % audioFilename)

print("Compiling frames and encoding...")
compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFilename)
print("Done.")
