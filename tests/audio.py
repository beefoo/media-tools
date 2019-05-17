# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sample/LivingSt1958.mp4", help="Input file")
parser.add_argument('-dur', dest="CLIP_DURATION", default=6000, type=int, help="Clip duration")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/audio_test.mp3", help="Output media file")
a = parser.parse_args()

instructions = [{
    "ms": 1000,
    "filename": a.INPUT_FILE,
    "start": 2000,
    "dur": a.CLIP_DURATION,
    "volume": 1.0,
    "fadeIn": 100,
    "fadeOut": 100,
    "matchDb": -16,
    "reverb": 80
}]

mixAudio(instructions, a.CLIP_DURATION + 2000, a.OUTPUT_FILE, sfx=True, sampleWidth=4, sampleRate=48000, channels=2, fxPad=3000, masterDb=0.0)
print("Done.")
