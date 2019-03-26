# -*- coding: utf-8 -*-

import argparse
import inspect
from moviepy.editor import VideoFileClip
import numpy as np
import os
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.clip import *
from lib.composition_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["OUTPUT_FRAME"] = "tmp/frame_stack_frames/frame.%s.png"
aa["OUTPUT_FILE"] = "output/frame_stack_test.mp4"
aa["CACHE_DIR"] = "tmp/frame_stack_cache/"
aa["CACHE_KEY"] = "frame_stack_test"
aa["VIDEO_ONLY"] = True
aa["OVERWRITE"] = True
aa["PAD_END"] = 0
aa["FRAME_ALPHA"] = 0.01
aa["BLEND_CLIPS"] = True

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

INPUT_FILE = "media/sample/LivingSt1958.mp4"

startTime = logTime()
stepTime = startTime
clipW = 240
clipH = 180
cx = a.WIDTH * 0.5
cy = a.HEIGHT * 0.5
radius = cy * 0.5
moveDurMs = 1000

clip = Clip({
    "index": 0,
    "filename": INPUT_FILE,
    "start": 12000,
    "dur": 2000,
    "x": cx-radius,
    "y": cy-radius,
    "width": clipW,
    "height": clipH,
    "origin": [0.5, 0.5]
})

ms = 0
clip.queueTween(ms, moveDurMs, ("translateX", 0, radius, "sin"))
ms += moveDurMs
clip.queueTween(ms, moveDurMs, ("translateY", 0, radius, "sin"))
ms += moveDurMs
clip.queueTween(ms, moveDurMs, ("translateX", radius, 0, "sin"))
ms += moveDurMs
clip.queueTween(ms, moveDurMs, ("translateY", radius, 0, "sin"))
ms += moveDurMs
clip.queueTween(0, moveDurMs*2, [("rotation", 0, 180, "linear")])
clip.queueTween(moveDurMs*2, moveDurMs*2, [("rotation", 180, 0, "linear")])

durationMs = moveDurMs*4
clips = [clip]

processComposition(a, clips, durationMs, sampler=None, stepTime=stepTime, startTime=startTime, containsAlphaClips=True)
