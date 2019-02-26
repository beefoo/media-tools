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

from lib.clip import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)

va = vars(a)
va["OUTPUT_FRAME"] = "tmp/gpuFrames_frames/frame.%s.jpg"
va["OUTPUT_FILE"] = "output/gpuFramesTest.mp4"
va["CACHE_DIR"] = "tmp/gpuFrames_cache/"
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

FILENAME = "media/sample/LivingSt1958.mp4"
DUR = 10000
HALF_DUR = int(DUR/2)
QUARTER_DUR = int(HALF_DUR/2)

container = Clip({
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "cache": True
})

CLIP_W = 320
CLIP_H = 240
HALF_W = CLIP_W/2
HALF_H = CLIP_H/2
clip = Clip({
    "filename": FILENAME,
    "start": 10000,
    "dur": HALF_DUR,
    "index": 0,
    "width": CLIP_W,
    "height": CLIP_H,
    "x": a.WIDTH * 0.5 - CLIP_W * 0.5,
    "y": a.HEIGHT * 0.5 - CLIP_H * 0.5
})
clip.vector.setParent(container.vector)

container.queueTween(0, HALF_DUR, ("scale", 1.0, 4.0, "sin"))
container.queueTween(HALF_DUR, HALF_DUR, ("scale", 4.0, 1.0, "sin"))

clip.queueTween(0, QUARTER_DUR, [("translateX", 0, -HALF_W), ("translateY", 0, -HALF_H), ("scale", 1.0, 0.5, "sin"), ("alpha", 1.0, 0.5, "sin")])
clip.queueTween(QUARTER_DUR, HALF_DUR, [("translateX", -HALF_W, HALF_W), ("translateY", -HALF_H, HALF_H)])
clip.queueTween(QUARTER_DUR+HALF_DUR, QUARTER_DUR, [("translateX", HALF_W, 0), ("translateY", HALF_H, 0), ("scale", 0.5, 1.0, "sin"), ("alpha", 0.5, 1.0, "sin")])

clips = [clip]

durationMs = DUR
print("Total time: %s" % formatSeconds(durationMs/1000.0))

# adjust frames if audio is longer than video
totalFrames = msToFrame(durationMs, a.FPS)

# get frame sequence
videoFrames = []
print("Making video frame sequence...")
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    videoFrames.append({
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "ms": ms,
        "width": a.WIDTH,
        "height": a.HEIGHT,
        "overwrite": True
    })

clipsPixelData = loadVideoPixelDataFromFrames(videoFrames, clips, a.WIDTH, a.HEIGHT, a.FPS, a.CACHE_DIR, a.CACHE_FILE, verifyData=True, cache=True)

processFrames(videoFrames, clips, clipsPixelData, threads=2)
compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames))
print("Done.")
