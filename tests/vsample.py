# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.cv_utils import *
from lib.math_utils import *
from lib.io_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-dur', dest="DURATION_MS", default=8000, type=int, help="Target duration in ms")
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="12x12", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="12x12", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-sname', dest="START_NAME", default="vstart", help="Name of the new start column")
parser.add_argument('-dname', dest="DUR_NAME", default="vdur", help="Name of the new duration column")
parser.add_argument('-mdur', dest="MIN_DUR", default=200, type=int, help="Minimum duration for video sample")
parser.add_argument('-tdur', dest="TARGET_DUR", default=1200, type=int, help="Target duration for video sample")
parser.add_argument('-vdur', dest="VAR_DUR", default=400, type=int, help="Amount of variance we should diff from the duration to reduce uniformity")
parser.add_argument('-fwidth', dest="FRAME_WIDTH", default=320, type=int, help="Frame width for analysis")
parser.add_argument('-fheight', dest="FRAME_HEIGHT", default=240, type=int, help="Frame height for analysis")
addVideoArgs(parser)
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["WIDTH"] = 640
aa["HEIGHT"] = 480
aa["OUTPUT_FRAME"] = "tmp/vsample_frames/frame.%s.png"
aa["OUTPUT_FILE"] = "output/vsample_test.mp4"
aa["CACHE_DIR"] = "tmp/vsample_cache/"
aa["CACHE_KEY"] = "vsample"
aa["VIDEO_ONLY"] = True
aa["OVERWRITE"] = True
aa["PAD_END"] = 0

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_DIR])

startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

for i, s in enumerate(samples):
    samples[i]["filepath"] = s["filename"]

# samples = [s for s in samples if s["col"]==4 and s["row"]==5]
# samples = [s for s in samples if s["col"]==1 and s["row"]==3]
# samples = [s for s in samples if s["col"]==1 and s["row"]==2]
# samples = [s for s in samples if s["col"]==9 and s["row"]==1]
# samples = [s for s in samples if s["col"]==8 and s["row"]==1]
# samples = [s for s in samples if s["col"]==7 and s["row"]==1]
# samples = [s for s in samples if s["col"]==7 and s["row"]==0]
# samples = [samples[0]]
samples = analyzeAndAdjustVideoSamples(samples, a.START_NAME, a.DUR_NAME, a.MIN_DUR, a.TARGET_DUR, a.VAR_DUR, a.FRAME_WIDTH, a.FRAME_HEIGHT, a.FPS, a.THREADS, a.OVERWRITE)
# sys.exit()
for i, s in enumerate(samples):
    samples[i]["start"] = s["vstart"]
    samples[i]["dur"] = s["vdur"]
clips = samplesToClips(samples)

processComposition(a, clips, a.DURATION_MS, sampler=None, stepTime=stepTime, startTime=startTime)
