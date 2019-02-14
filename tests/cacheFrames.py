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

container = Clip({
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "cache": True
})
xc = int(a.WIDTH / 2)
yc = int(a.HEIGHT / 2)
clips = [
    Clip({"index": 0, "x": xc-100, "y": yc-100, "width": 100, "height": 100, "filename": "media/sample/LivingSt1958.mp4", "start": 2000, "dur": 1000}),
    Clip({"index": 1, "x": xc, "y": yc-100, "width": 100, "height": 100, "filename": "media/sample/LivingSt1958.mp4", "start": 4000, "dur": 1000}),
    Clip({"index": 2, "x": xc-100, "y": yc, "width": 50, "height": 50, "filename": "media/sample/LivingSt1958.mp4", "start": 20000, "dur": 1000}),
    Clip({"index": 3, "x": xc, "y": yc, "width": 100, "height": 100, "filename": "media/sample/dolbycanyon.mp4", "start": 2000, "dur": 1000})
]
for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

ms = 0
scale = 1.0
dur = 1000
for z in range(3):
    container.queueTween(ms, dur, ("scale", scale, scale+1.0, "sinIn"))
    scale += 1.0
    ms += dur
clips[0].queueTween(0, dur, ("scale", 1.0, 0.5, "sinIn"))

durationMs = ms
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
        "clips": clips,
        "ms": ms,
        "width": a.WIDTH,
        "height": a.HEIGHT,
        "overwrite": True,
        "gpu": True
    })

loadVideoPixelDataFromFrames(videoFrames, clips, a.FPS, a.CACHE_FILE)

processFrames([videoFrames[0]], threads=1)
print("Done.")
