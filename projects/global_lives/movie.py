# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.composition_utils import *
from lib.math_utils import *
from lib.io_utils import *
from lib.video_utils import *
from gllib import *

parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-co', dest="COLLECTION_FILE", default="projects/global_lives/data/ia_globallives_collections.csv", help="Input collection csv file")
parser.add_argument('-celld', dest="CELL_DURATION", default=3.0, type=float, help="Cell duration in minutes")
parser.add_argument('-ppf', dest="PIXELS_PER_FRAME", default=1.0, type=float, help="Number of pixels to move per frame")
parser.add_argument('-textfdur', dest="TEXT_FADE_DUR", default=1000, type=int, help="Duration text should fade in milliseconds")
parser.add_argument('-textfdel', dest="TEXT_FADE_DELAY", default=500, type=int, help="Duration text should delay fade in milliseconds")
parser.add_argument('-clipsmo', dest="CLIPS_MOVE_OFFSET", default=-1000, type=int, help="Offset the clips should start moving in in milliseconds")
parser.add_argument('-clockh', dest="CLOCK_LABEL_HEIGHT", default=0.1, type=float, help="Clock label height as a percent of height")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["ASPECT_RATIO"] = 1.0 * a.WIDTH / a.HEIGHT
aa["CLOCK_LABEL_HEIGHT"] = roundInt(a.CLOCK_LABEL_HEIGHT * a.HEIGHT)
aa["CLIP_AREA_HEIGHT"] = a.HEIGHT - a.CLOCK_LABEL_HEIGHT

startTime = logTime()
stepTime = startTime

# Read and initialize data
vFieldNames, videos = readCsv(a.INPUT_FILE)
cFieldNames, collections = readCsv(a.COLLECTION_FILE)
collections = [c for c in collections if c["active"] > 0]
collections = sorted(collections, key=lambda c: -c["lat"])
collectionCount = len(collections)
print("%s collections" % collectionCount)
videos = prependAll(videos, ("filename", a.MEDIA_DIRECTORY))
collections = addIndices(collections, "row")

# break videos up into cells per collection
cellsPerCollection = roundInt(24.0 * 60.0 / a.CELL_DURATION)
print("Cells per collection: %s" % cellsPerCollection)
collections = addCellsToCollections(collections, videos, cellsPerCollection)
# collectionToImg(collections, "output/global_lives.png", cellsPerCollection)

# calculate cell size and composition size and duration
cellH = int(1.0 * a.CLIP_AREA_HEIGHT / collectionCount)
cellW = roundInt(cellH * a.ASPECT_RATIO)
totalW = cellW * cellsPerCollection
totalXDelta = totalW + a.WIDTH
print("%s total pixel movement" % formatNumber(totalXDelta))
totalMoveFrames = roundInt(totalXDelta / a.PIXELS_PER_FRAME)
totalMoveMs = frameToMs(totalMoveFrames, a.FPS)
print("Total movement duration: %s" % formatSeconds(totalMoveMs/1000.0))

# calculate text durations
textDurationMs = a.TEXT_FADE_DELAY * collectionCount + max(a.TEXT_FADE_DUR - a.TEXT_FADE_DELAY, 0)
moveStartMs = textDurationMs + a.CLIPS_MOVE_OFFSET
durationMs = moveStartMs + totalMoveMs + moveStartMs
print("Total duration: %s" % formatSeconds(durationMs/1000.0))
sys.exit()

# create samples
# add index
# create clips

# custom clip to numpy array function to override default tweening logic
def clipToNpArrGL(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    x = y = w = h = tn = alpha = 0

    # determine position and size here

    customProps = {
        "pos": [x, y],
        "size": [w, h]
    }

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(alpha * precisionMultiplier),
        roundInt(tn * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

def preProcessGL(im, ms):
    # Add text here
    return im

# processComposition(a, clips, durationMs, stepTime=stepTime, startTime=startTime, customClipToArrFunction=clipToNpArrGL, preProcessingFunction=preProcessGL, renderOnTheFly=True)
