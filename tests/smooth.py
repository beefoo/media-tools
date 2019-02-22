# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
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
va["OUTPUT_FRAME"] = "tmp/smoothtest/frame.%s.png"
va["OUTPUT_FILE"] = "output/smoothtest.mp4"
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

FILENAME = "media/sample/LivingSt1958.mp4"
WIDTH = 800
HEIGHT = 600
DURATION = 8000
MOVE_AMOUNT = 10
CLIP_W = 100.5
CLIP_H = 50.5

clip = Clip({
    "index": 0,
    "filename": FILENAME,
    "start": 10000,
    "dur": DURATION,
    "width": CLIP_W,
    "height": CLIP_H,
    "x": WIDTH * 0.5 - (CLIP_W * 0.5) - MOVE_AMOUNT * 0.5,
    "y": HEIGHT * 0.5 - (CLIP_H * 0.5) - MOVE_AMOUNT * 0.5
})

halfDur = int(DURATION/2)
clip.queueTween(0, halfDur, [("translateX", 0.0, MOVE_AMOUNT), ("translateY", 0.0, MOVE_AMOUNT)])
clip.queueTween(halfDur, halfDur, [("translateX", MOVE_AMOUNT, 1.0), ("translateY", MOVE_AMOUNT, 1.0)])

durationMs = DURATION
print("Total time: %s" % formatSeconds(durationMs/1000.0))

# adjust frames if audio is longer than video
totalFrames = msToFrame(durationMs, a.FPS)

# get frame sequence
clips = [clip]
videoFrames = []
print("Making video frame sequence...")
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    videoFrames.append({
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "clips": clips,
        "ms": ms,
        "width": WIDTH,
        "height": HEIGHT,
        "overwrite": True,
        "gpu": True
    })

loadVideoPixelDataFromFrames(videoFrames, clips, a.FPS, a.CACHE_DIR, verifyData=True)

processFrames(videoFrames, threads=1)
compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames))
print("Done.")
