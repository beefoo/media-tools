# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import random
import subprocess
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-step', dest="STEP_MS", default=2000, help="Step duration")
parser.add_argument('-man', dest="MANIFEST_FILE", default="tmp/combine_test.txt", help="Path to manifest file")
parser.add_argument('-pyn', dest="PYTHON_NAME", default="python3", help="Python name for subprocess")
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["WIDTH"] = 640
aa["HEIGHT"] = 480
aa["OUTPUT_FRAME"] = "tmp/combine_test_frames/frame.%s.png"
aa["CACHE_DIR"] = "tmp/combine_test_cache/"
aa["CACHE_KEY"] = "combine_test"
aa["VIDEO_ONLY"] = True
aa["OVERWRITE"] = True

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

def getSamples(a, offset, x, y, w, h):
    return [
        {"index": 0, "filename": "media/sample/LivingSt1958.mp4", "start": 1000, "dur": 2000, "width": w, "height": h, "x": x, "y": y, "initialOffset": offset, "brightness": a.BRIGHTNESS_RANGE[0]},
        {"index": 1, "filename": "media/sample/LivingSt1958.mp4", "start": 3000, "dur": 1000, "width": w, "height": h, "x": x+a.WIDTH*0.5, "y": y, "initialOffset": offset, "brightness": a.BRIGHTNESS_RANGE[0]},
        {"index": 2, "filename": "media/sample/LivingSt1958.mp4", "start": 10000, "dur": 2500, "width": w, "height": h, "x": x, "y": y+a.HEIGHT*0.5, "initialOffset": offset, "brightness": a.BRIGHTNESS_RANGE[0]},
        {"index": 3, "filename": "media/sample/LivingSt1958.mp4", "start": 20000, "dur": 1500, "width": w, "height": h, "x": x+a.WIDTH*0.5, "y": y+a.HEIGHT*0.5, "initialOffset": offset, "brightness": a.BRIGHTNESS_RANGE[0]}
    ]

def playClips(a, clips):
    for i, clip in enumerate(clips):
        clipMs = a.PAD_START + i * a.STEP_MS
        clip.queuePlay(clipMs, {
            "start": clip.props["start"],
            "dur": clip.props["dur"]
        })
        clipDur = clip.props["dur"]
        leftMs = roundInt(clipDur * 0.2)
        rightMs = clipDur - leftMs
        clip.queueTween(clipMs, leftMs, [
            ("brightness", a.BRIGHTNESS_RANGE[0], a.BRIGHTNESS_RANGE[1], "sin")
        ])
        clip.queueTween(clipMs+leftMs, rightMs, [
            ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
        ])

def makeComposition(a):
    if not os.path.isfile(a.OUTPUT_FILE) or a.OVERWRITE:
        initialOffset = getInitialOffset(a)
        clipW = a.WIDTH * 0.25
        clipH = a.HEIGHT * 0.25
        clipX = a.WIDTH * 0.125
        clipY = a.HEIGHT * 0.125
        samples = getSamples(a, initialOffset, clipX, clipY, clipW, clipH)
        clips = samplesToClips(samples)
        playClips(a, clips)
        durationMs = a.PAD_START + len(clips) * a.STEP_MS
        processComposition(a, clips, durationMs)


aa["OUTPUT_FILE"] = "output/combine_test_01.mp4"
makeComposition(a)

aa["OUTPUT_FILE"] = "output/combine_test_02.mp4"
aa["PAD_START"] = 2000
aa["PAD_END"] = 4000
makeComposition(a)

aa["OUTPUT_FILE"] = "output/combine_test_03.mp4"
aa["PAD_START"] = 2500
aa["PAD_END"] = 4500
makeComposition(a)

aa["OUTPUT_FILE"] = "output/combine_test_04.mp4"
aa["PAD_START"] = 3000
aa["PAD_END"] = 3000
makeComposition(a)

with open(a.MANIFEST_FILE, 'w') as f:
    f.write("file 'combine_test_01.mp4'\n")
    f.write("file 'combine_test_02.mp4'\n")
    f.write("file 'combine_test_03.mp4'\n")
    f.write("file 'combine_test_04.mp4'\n")

# Compile features into media file
command = [a.PYTHON_NAME, "combine_media.py", '-in', a.MANIFEST_FILE, '-out', "output/combine_media_test.mp4"]
print(" ".join(command))
finished = subprocess.check_call(command)
