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

from lib.math_utils import *
from lib.video_utils import *

WIDTH = 1000
HEIGHT = 1000
CX = WIDTH/2
CY = HEIGHT/2
VIDEO = "../media/sample/LivingSt1958.mp4"
OUTPUT_FILE = "../output/rotate_test.png"
COUNT = 24
GPU = True
clipW = 100
clipH = 50

video = VideoFileClip(VIDEO, audio=False)
duration = video.duration
timeStep = int(duration / (COUNT+1) * 1000)

framePixelData = []
for i in range(COUNT):
    im = getVideoClipImage(video, duration, {
        "t": i * timeStep,
        "width": clipW,
        "height": clipH
    })
    framePixelData.append(np.array(im))

angle = 0
clips = []
for i in range(COUNT):
    angle = 360.0 * (1.0/COUNT) * i
    cx, cy = translatePoint(CX, CY, HEIGHT/3, angle)
    # bx, by, bw, bh = bboxRotate(cx, cy, clipW, clipH, angle)
    t = i * timeStep
    clip = Clip({
        "filename": VIDEO,
        "x": cx,
        "y": cy,
        "origin": (0.5, 0.5),
        "width": clipW,
        "height": clipH,
        "start": t,
        "dur": 1,
        "framePixelData": framePixelData
    })
    clip.queuePlay(1)
    blur = lerp((0, 4.0), 1.0 * i / (COUNT-1))
    clip.queueTween(1, tweens=[
        ("rotation", angle, angle),
        ("blur", blur, blur)
    ])
    clips.append(clip)

clips = clipsToDicts(clips, 1)

for i, clip in enumerate(clips):
    clips[i]["tn"] = clip["t"] / (duration*1000.0)

clipsToFrame({
    "clips": clips,
    "filename": OUTPUT_FILE,
    "width": WIDTH,
    "height": HEIGHT,
    "gpu": GPU,
    "overwrite": True
})
