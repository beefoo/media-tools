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

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sample/sonata.mp3", help="Input file")
parser.add_argument('-start', dest="CLIP_START", default=0, type=int, help="Clip start in ms")
parser.add_argument('-dur', dest="CLIP_DUR", default=-1, type=int, help="Clip duration in ms, -1 for whole clip")
parser.add_argument('-stretch', dest="STRETCH_AMOUNTS", default="1,1.5,2,4,8,16", help="Amounts to stretch (1 = no stretch)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/stretch_test.mp3", help="Output media file")
a = parser.parse_args()

# Parse arguments
filename = a.INPUT_FILE
clipStart = a.CLIP_START
clipDur = a.CLIP_DUR
stretchAmounts = [float(amt) for amt in a.STRETCH_AMOUNTS.split(",")]

fformat = filename.split(".")[-1]
audio = getAudio(a.INPUT_FILE)
audioDuration = len(audio)
if clipDur <= 0:
    clipDur = audioDuration

totalDuration = sum([amt*clipDur for amt in stretchAmounts])
instructions = []

ms = 0
for amt in stretchAmounts:
    instructions.append({
        "ms": roundInt(ms),
        "filename": a.INPUT_FILE,
        "start": clipStart,
        "dur": clipDur,
        "stretch": amt
    })
    ms += amt * clipDur

makeDirectories(a.OUTPUT_FILE)
mixAudio(instructions, totalDuration, a.OUTPUT_FILE)
