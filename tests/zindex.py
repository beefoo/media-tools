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
a = parser.parse_args()

clips = []
clips.append({"width": 100, "height": 100, "x": 0, "y": 0, "framePixelData": [[[[255,0,0]]]]})
clips.append({"width": 100, "height": 100, "x": 50, "y": 0, "framePixelData": [[[[0,255,0]]]]})
clips.append({"width": 100, "height": 100, "x": 0, "y": 50, "framePixelData": [[[[0,0,255]]]]})
clips.append({"width": 100, "height": 100, "x": 50, "y": 50, "framePixelData": [[[[255,255,0]]]]})

clipsToFrame({
    "filename": "output/zindexTest.png",
    "width": 150,
    "height": 150,
    "overwrite": True,
    "gpu": True,
    "clips": clips
})
clips = list(reversed(clips))
clipsToFrame({
    "filename": "output/zindexTest2.png",
    "width": 150,
    "height": 150,
    "overwrite": True,
    "gpu": True,
    "clips": clips
})

print("Done.")
