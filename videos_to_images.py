# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import sys

from lib.audio_utils import *
from lib.collection_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input media dir")
parser.add_argument('-out', dest="OUTPUT_DIR", default="tmp/video_images/", help="Output dir")
parser.add_argument('-time', dest="PERCENT_TIME", default=0.5, type=float, help="Time to make into image as a percentage of video/clip duration")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing images?")
parser.add_argument('-clips', dest="CHECK_FOR_CLIPS", action="store_true", help="Check for video clips?")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rows = prependAll(rows, ("filename", a.MEDIA_DIRECTORY, "filepath"))

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

def makeImage(row):
    global a
    print("Processing %s" % row["filename"])
    outFilename = a.OUTPUT_DIR + replaceFileExtension(row["filename"], ".jpg")

    if os.path.isfile(outFilename) and not a.OVERWRITE:
        return outFilename

    ntime = a.PERCENT_TIME

    if a.CHECK_FOR_CLIPS:
        start = 0
        end = 0
        videoDur = int(getDurationFromFile(row["filepath"], accurate=True) * 1000)
        if "start" in row:
            start = parseTimeMs(row["start"])
        if "end" in row:
            end = parseTimeMs(row["end"])
        if end <= 0:
            end = videoDur
        nstart = 1.0 * start / videoDur
        nend = 1.0 * end / videoDur
        ntime = lerp((nstart, nend), ntime)

    image = getVideoClipImageFromFile(row["filepath"], ntime)
    image.save(outFilename)

    return outFilename

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(makeImage, rows)
pool.close()
pool.join()
