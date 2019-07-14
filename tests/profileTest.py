# -*- coding: utf-8 -*-

# python3 -m cProfile -s cumtime tests/profileTest.py

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
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)

va = vars(a)
va["OUTPUT_FRAME"] = "tmp/profile_frames/frame.%s.png"
va["CACHE_DIR"] = "tmp/profile_cache/"
va["CACHE_KEY"] = "profile"
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

FILENAME = "media/sample/LivingSt1958.mp4"
CLIPS = 256
COLS = int(math.sqrt(CLIPS))
ROWS = ceilInt(1.0 * CLIPS / COLS)
DURATION_MS = int(getDurationFromFile(FILENAME, accurate=True) * 1000)
OUT_DUR_MS = 2000
MAX_CLIP_DUR_MS = 1000

container = Clip({
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "cache": True
})

startTime = logTime()
stepTime = startTime

samples = []
clipDur = min(MAX_CLIP_DUR_MS, int(1.0 * DURATION_MS / CLIPS))
for i in range(CLIPS):
    samples.append({
        "filename": FILENAME,
        "start": int(i * clipDur),
        "dur": clipDur
    })

samples = addGridPositions(samples, COLS, a.WIDTH, a.HEIGHT)
samples = addIndices(samples)

stepTime = logTime(stepTime, "Init samples")

clips = samplesToClips(samples)

stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

container.queueTween(0, OUT_DUR_MS, ("scale", 1.0, 4.0, "sin"))

durationMs = OUT_DUR_MS
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
        "overwrite": True
    })

stepTime = logTime(stepTime, "Make sequence")

clipsPixelData = loadVideoPixelDataFromFrames(videoFrames, clips, a.WIDTH, a.HEIGHT, a.FPS, a.CACHE_DIR, a.CACHE_KEY, verifyData=True)
stepTime = logTime(stepTime, "Load pixel data")

processFrames([videoFrames[0]], clips, clipsPixelData, threads=1)
stepTime = logTime(stepTime, "Process frame")

print("Done.")
