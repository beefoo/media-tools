# -*- coding: utf-8 -*-

# LAYER PIECE
#
# 1. Layer sounds horizontally
# 2. Each layer is a frequency band
# 3. Stretch the lower frequencies

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
parser.add_argument('-in', dest="INPUT_FILE", default="../tmp/samples.csv", help="Input file")
parser.add_argument('-ss', dest="EXCERPT_START", type=float, default=-1, help="Excerpt start in seconds")
parser.add_argument('-sd', dest="EXCERPT_DUR", type=float, default=-1, help="Excerpt duration in seconds")
parser.add_argument('-dir', dest="VIDEO_DIRECTORY", default="../media/sample/", help="Input file")
parser.add_argument('-cols', dest="COLUMNS", default=48, type=int, help="Number of columns in the matrix")
parser.add_argument('-aspect', dest="ASPECT_RATIO", default="16:9", help="Aspect ratio of each cell")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
parser.add_argument('-pps', dest="PIXELS_PER_SECOND", default=30, type=int, help="Base number of pixels to move the composition per second")
parser.add_argument('-frames', dest="SAVE_FRAMES", default=0, type=int, help="Save frames?")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="../tmp/layers/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/layers.mp4", help="Output media file")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing frames?")
parser.add_argument('-ao', dest="AUDIO_ONLY", default=0, type=int, help="Render audio only?")
parser.add_argument('-vo', dest="VIDEO_ONLY", default=0, type=int, help="Render video only?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
EXCERPT_START = args.EXCERPT_START
EXCERPT_DUR = args.EXCERPT_DUR
VIDEO_DIRECTORY = args.VIDEO_DIRECTORY
COLUMNS = args.COLUMNS
ASPECT_W, ASPECT_H = tuple([int(p) for p in args.ASPECT_RATIO.split(":")])
ASPECT_RATIO = 1.0 * ASPECT_W / ASPECT_H
WIDTH = args.WIDTH
HEIGHT = args.HEIGHT
FPS = args.FPS
PIXELS_PER_SECOND = args.PIXELS_PER_SECOND
SAVE_FRAMES = args.SAVE_FRAMES > 0
OUTPUT_FRAME = args.OUTPUT_FRAME
OUTPUT_FILE = args.OUTPUT_FILE
THREADS = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
OVERWRITE = args.OVERWRITE > 0
AUDIO_OUTPUT_FILE = OUTPUT_FILE.replace(".mp4", ".mp3")

makeDirectories([OUTPUT_FRAME, OUTPUT_FILE])

# get unique video files
fieldNames, samples = readCsv(INPUT_FILE)
sampleCount = len(samples)
print("Loaded %s samples" % sampleCount)
