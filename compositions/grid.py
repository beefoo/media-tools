# -*- coding: utf-8 -*-

# Instructions:
# 1. Place clips in a grid, sorting vertically by frequency and horizontally by power
# 2. Play clips from left-to-right
# 3. Play clips from right-to-left
# 4. Play clips from top-to-bottom
# 5. Play clips from bottom-to-top
# 6. Play clips from left-to-right and right-to-left, simultaneously
# 7. Play clips from top-to-bottom and bottom-to-top, simultaneously
# 8. Play clips from left-to-right and top-to-bottom, simultaneously
# 9. Play clips from right-to-left and bottom-to-top, simultaneously
# 10. Play clips from left-to-right and bottom-to-top, simultaneously
# 11. Play clips from right-to-left and top-to-bottom, simultaneously
# 12. Play clips from left-to-right, right-to-left, top-to-bottom, bottom-to-top, simultaneously

import argparse
import inspect
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-pdur', dest="PAN_DURATION", default=3.0, type=float, help="Pan duration in seconds")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

PAN_DUR_X = a.PAN_DURATION
PAN_DUR_Y = a.PAN_DURATION / a.ASPECT_RATIO

# get unique video files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
print("Loaded %s samples" % sampleCount)
