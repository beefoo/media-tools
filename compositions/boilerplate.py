# -*- coding: utf-8 -*-

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
a = parser.parse_args()
parseVideoArgs(a)

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# get unique video files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
print("Loaded %s samples" % sampleCount)
