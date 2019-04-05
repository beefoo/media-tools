# -*- coding: utf-8 -*-

# Given a list of audio samples, create adjusted video samples based on scene detection

import argparse
import os
import numpy as np
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.cv_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if we should update input file")
parser.add_argument('-sname', dest="START_NAME", default="vstart", help="Name of the new start column")
parser.add_argument('-dname', dest="DUR_NAME", default="vdur", help="Name of the new duration column")
parser.add_argument('-mdur', dest="MIN_DUR", default=256, type=int, help="Minimum duration for video sample")
parser.add_argument('-tdur', dest="TARGET_DUR", default=1200, type=int, help="Target duration for video sample")
parser.add_argument('-vdur', dest="VAR_DUR", default=400, type=int, help="Amount of variance we should diff from the duration to reduce uniformity")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="FPS for analyzing video")
parser.add_argument('-width', dest="FRAME_WIDTH", default=320, type=int, help="Frame width for analysis")
parser.add_argument('-height', dest="FRAME_HEIGHT", default=240, type=int, help="Frame height for analysis")
parser.add_argument('-threads', dest="THREADS", default=1, type=int, help="Number of concurrent threads")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
a = parser.parse_args()

FIELDS_TO_ADD = [a.START_NAME, a.DUR_NAME]
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
samples = addIndices(samples, keyName="index")
samples = prependAll(samples, ("filename", a.MEDIA_DIRECTORY, "filepath"))

# add fields
for field in FIELDS_TO_ADD:
    if field not in fieldNames:
        fieldNames.append(field)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

samples = analyzeAndAdjustVideoSamples(samples, a.START_NAME, a.DUR_NAME, a.MIN_DUR, a.TARGET_DUR, a.VAR_DUR, a.FRAME_WIDTH, a.FRAME_HEIGHT, a.FPS, a.THREADS, a.OVERWRITE)
samples = sorted(samples, key=lambda s: s["index"])

writeCsv(OUTPUT_FILE, samples, headings=fieldNames)
