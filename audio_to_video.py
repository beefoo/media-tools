# -*- coding: utf-8 -*-

# Attempt to convert audio to video by visualizing audio

import argparse
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
import librosa
import os
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sample/bird.wav", help="Input file pattern; can be an audio file, a .csv file, or a glob string")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/", help="Input dir")
parser.add_argument('-width', dest="WIDTH", default=480, type=int, help="Video width")
parser.add_argument('-height', dest="HEIGHT", default=320, type=int, help="Video height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/%s.mp4", help="Video output file pattern")
parser.add_argument('-threads', dest="THREADS", default=1, type=int, help="Amount of parallel processes")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
a = parser.parse_args()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

# Read files
fieldNames, files, fileCount = getFilesFromString(a)

# Check for valid audio
if "duration" in fieldNames and "hasAudio" in fieldNames:
    files = filterWhere(files, [("duration", 0, ">"), ("hasAudio", 0, ">")])
    fileCount = len(files)
    print("Found %s rows after filtering" % fileCount)
