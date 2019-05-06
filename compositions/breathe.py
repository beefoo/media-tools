# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
from operator import itemgetter
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.cache_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.8", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=132000, type=int, help="Target duration in ms")
parser.add_argument('-props', dest="CLUSTER_PROPS", default="tsne,tsne2", help="X and Y properties for clustering")
parser.add_argument('-clusters', dest="CLUSTERS", default=64, type=int, help="Number of clusters to play")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["PAD_END"] = 6000
aa["THREADS"] = 1 # enforce one thread since we need to process frames sequentially
aa["FRAME_ALPHA"] = 0.01 # decrease to make "trails" longer

PROP1, PROP2 = tuple([p for p in a.CLUSTER_PROPS.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# add clusters
print("Calculating clusters...")
samples, clusterCenters = addClustersToList(samples, PROP1, PROP2, nClusters=a.CLUSTERS)
stepTime = logTime(stepTime, "Calculated clusters")

# set clip brightness to min by default
for i, s in enumerate(samples):
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

fromScale = 1.0 * gridW / startGridW
toScale = 1.0 * gridW / endGridW
if fromScale != toScale:
    container.queueTween(a.PAD_START, a.DURATION_MS, ("scale", fromScale, toScale, "quadInOut"))

startMs = a.PAD_START
endMs = startMs + a.DURATION_MS
durationMs = endMs

# sort frames
container.vector.sortFrames()

stepTime = logTime(stepTime, "Calculated sequence")

# custom clip to numpy array function to override default tweening logic
def clipToNpArrBreathe(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    customProps = None

    # customProps = {
    #     "pos": [x, y]
    # }

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(props["alpha"] * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

processComposition(a, clips, durationMs, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrBreathe, containsAlphaClips=True, isSequential=True, container=container)
