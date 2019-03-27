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
aa["OUTPUT_FRAME"] = "tmp/rotate_blur_frames/frame.%s.png"
aa["OUTPUT_FILE"] = "output/rotate_blur_test.mp4"
aa["CACHE_DIR"] = "tmp/rotate_blur_cache/"
aa["CACHE_KEY"] = "rotate_blur_test"
aa["VIDEO_ONLY"] = True
aa["OVERWRITE"] = True
aa["PAD_END"] = 0

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

CX = a.WIDTH/2
CY = a.HEIGHT/2
INPUT_FILE = "media/sample/LivingSt1958.mp4"
COUNT = 32
HALF = COUNT/2
CLIP_W = 128
CLIP_H = 96
RADIUS_INNER = CLIP_H
RADIUS_OUTER = CLIP_H * 2
TARGET_DURATION = 8000
FPS = 30

startTime = logTime()
stepTime = startTime
video = VideoFileClip(INPUT_FILE, audio=False)
duration = video.duration
timeStep = int(duration / (COUNT+1) * 1000)
durationMs = min([timeStep, TARGET_DURATION])
clipDurMs = min([timeStep, 1000, TARGET_DURATION])

samples = []
for i in range(COUNT):
    radius = RADIUS_INNER if i < HALF else RADIUS_OUTER
    n = 1.0 * i / HALF if i < HALF else 1.0 * (i-HALF) / HALF
    angle = n * 360.0
    x, y = translatePoint(CX, CY, radius, angle)
    samples.append({
        "index": i,
        "filename": INPUT_FILE,
        "start": i*durationMs,
        "dur": clipDurMs,
        "x": x,
        "y": y,
        "width": CLIP_W,
        "height": CLIP_H,
        "origin": [0.5, 0.5]
    })

clips = samplesToClips(samples)
for i, clip in enumerate(clips):
    rotations = i % 3 + 1
    clip.queueTween(0, durationMs, [("rotation", 0, rotations*360, "sin")])
    blurDur = int(durationMs/rotations)
    halfBlurDur = blurDur/2
    blurRadius = 2.0
    for j in range(rotations):
        clip.queueTween(j*blurDur, halfBlurDur, [("blur", 0, blurRadius*(j+1), "sin"), ("brightness", 1.0, 0.5, "sin")])
        clip.queueTween(j*blurDur+halfBlurDur, halfBlurDur, [("blur", blurRadius*(j+1), 0, "sin"), ("brightness", 0.5, 1.0, "sin")])

processComposition(a, clips, durationMs, sampler=None, stepTime=stepTime, startTime=startTime, containsAlphaClips=True)
