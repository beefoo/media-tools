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
from lib.audio_utils import *
from lib.collection_utils import *
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
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/floyd_viz.mp4", help="Path to output file")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display details?")
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

frames = [frames[0]]

def processFrame(frame):
    global a
    global states

    baseImage = Image.new(mode="RGB", size=(frame["width"], frame["height"]), color=(0, 0, 0))
    print("Processing %s..." % frame["filename"])

    for state in states:
        maskImg = state["mask"]
        maskW, maskH = (state["width"], state["height"])
        item = state["item"]

        # retrieve image at an offset time
        msOffset = roundInt(item["offset"] * item["duration"])
        itemMs = (frame["ms"] + msOffset) % item["duration"]
        ntime = 1.0 * itemMs / item["duration"]
        ntime = lerp((item["nstart"], item["nend"]), ntime)
        itemImg = getVideoClipImageFromFile(item["filepath"], nt=ntime)

        # crop the image based on mask
        itemW, itemH = itemImg.size
        itemScale = item["scale"]
        itemOffsetX = item["offsetx"]
        itemOffsetY = item["offsety"]
        if itemScale > 1.0:
            itemTargetW, itemTargetH = (roundInt(itemW * itemScale), roundInt(itemH * itemScale))
            itemImg = itemImg.resize((itemTargetW, itemTargetH))
            itemOffsetX -= roundInt((itemTargetW-itemW) * 0.5)
            itemOffsetY -= roundInt((itemTargetH-itemH) * 0.5)
        croppedImg = fillImage(itemImg, maskW, maskH)

        # mask and paste the image
        itemBaseImage = Image.new(mode="RGB", size=(frame["width"], frame["height"]), color=(0, 0, 0))
        itemBaseImage.paste(croppedImg, (state["x"]+itemOffsetX, state["y"]+itemOffsetY))
        baseImage = Image.composite(baseImage, itemBaseImage, maskImg)

    baseImage.save(frame["filename"])
    print("Saved %s." % frame["filename"])
    return True

print("Starting frame processing...")
pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(processFrame, frames)
pool.close()
pool.join()
