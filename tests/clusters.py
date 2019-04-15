# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="128x128", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.2,6.0", help="Volume range")
parser.add_argument('-lim', dest="LIMIT", default=4096, type=int, help="Limit number of clips; -1 if all")
parser.add_argument('-lsort', dest="LIMIT_SORT", default="power=desc=0.8&clarity=desc", help="Sort string if/before reducing clip size")
parser.add_argument('-props', dest="PROPS", default="tsne,tsne2", help="X and Y properties")
parser.add_argument('-clusters', dest="CLUSTERS", default=128, type=int, help="Number of clusters?")
parser.add_argument('-runs', dest="RUNS", default=20, type=int, help="Number of times to run k-means to determine best centroids")
parser.add_argument('-overlap', dest="OVERLAP", default=128, type=int, help="Overlap clips in milliseconds")
parser.add_argument('-overlapp', dest="OVERLAP_PERCENT", default=0.5, type=float, help="Overlap clips in percentage of clip duration")
parser.add_argument('-play', dest="PLAY_CLUSTERS", default=16, type=int, help="Play this many clusters")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["OUTPUT_FRAME"] = "tmp/cluster_frames/frame.%s.png"
aa["OUTPUT_FILE"] = "output/cluster_test.mp4"
aa["CACHE_DIR"] = "tmp/cluster_cache/"
aa["CACHE_KEY"] = "cluster_test"
aa["DEBUG"] = True
aa["OVERWRITE"] = True

PROP1, PROP2 = tuple([p for p in a.PROPS.strip().split(",")])
SIZE = 4

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)
stepTime = logTime(stepTime, "Read samples")

print("Calculating K-means...")
xy = np.array([(s[PROP1], s[PROP2]) for s in samples])
y_kmeans, centers = getKMeansClusters(xy, nClusters=a.CLUSTERS, nRuns=a.RUNS, nJobs=a.THREADS)
stepTime = logTime(stepTime, "Calculated K-means")

samples = addNormalizedValues(samples, PROP1, "nx")
samples = addNormalizedValues(samples, PROP2, "ny")

# Add cluster to samples
for i, s in enumerate(samples):
    samples[i]["cluster"] = y_kmeans[i]
    samples[i]["x"] = lerp((SIZE*0.5, a.WIDTH-SIZE*0.5), s["nx"])
    samples[i]["y"] = lerp((SIZE*0.5, a.HEIGHT-SIZE*0.5), s["ny"])
    samples[i]["width"] = SIZE
    samples[i]["height"] = SIZE
    samples[i]["brightness"] = a.BRIGHTNESS_RANGE[0]

xRange = (xy[:,0].min(), xy[:,0].max())
yRange = (xy[:,1].min(), xy[:,1].max())
ncenters = np.zeros(centers.shape, dtype=centers.dtype)
ncenters[:,0] = norm(centers[:,0], xRange)
ncenters[:,1] = norm(centers[:,1], yRange)

clusters = groupList(samples, "cluster")
for i, c in enumerate(clusters):
    ncenter = ncenters[c["cluster"]]
    cx = lerp((SIZE*0.5, a.WIDTH-SIZE*0.5), ncenter[0])
    cy = lerp((SIZE*0.5, a.HEIGHT-SIZE*0.5), ncenter[1])
    clusters[i]["cx"] = cx
    clusters[i]["cy"] = cy
    clusters[i]["nDistanceFromCenter"] = distance(0.5, 0.5, ncenter[0], ncenter[1])
    csamples = sorted(c["items"], key=lambda s: s["stsne"])
    clusters[i]["std"] = np.std([distance(cx, cy, s["x"], s["y"]) for s in csamples])
    clusters[i]["medianHz"] = np.median([s["hz"] for s in csamples])
    clusters[i]["clips"] = samplesToClips(csamples)
stepTime = logTime(stepTime, "Samples to clips")

# choose clusters
clusters = sortBy(clusters, [
    ("nDistanceFromCenter", "desc", 0.25), # prefer clusters at the edge
    ("std", "asc") # prefer clusters closer together
], targetLen=a.PLAY_CLUSTERS)
clusters = sorted(clusters, key=lambda c: c["medianHz"])
count = len(clusters)

clips = []
ms = a.PAD_START
for i in range(count):
    # alternate between lower and higher hz
    cluster = clusters.pop(-1) if i % 2 > 0 else clusters.pop(0)
    ccount = len(cluster["clips"])
    for j, clip in enumerate(cluster["clips"]):
        nclip = 1.0 * j / (ccount-1)
        volume = lerp(a.VOLUME_RANGE, easeSinInOutBell(nclip))
        clip.queuePlay(ms, {
            "start": clip.props["audioStart"],
            "dur": clip.props["audioDur"],
            "volume": volume,
            "fadeOut": clip.props["fadeOut"],
            "fadeIn": clip.props["fadeIn"],
            "pan": 0.0,
            "reverb": clip.props["reverb"],
            "matchDb": clip.props["matchDb"]
        })
        leftMs = roundInt(clip.props["renderDur"] * 0.2)
        rightMs = clip.props["renderDur"] - leftMs
        clip.queueTween(ms, leftMs, [
            ("brightness", 0, a.BRIGHTNESS_RANGE[1], "sin")
        ])
        clip.queueTween(ms+leftMs, rightMs, [
            ("brightness", a.BRIGHTNESS_RANGE[1], a.BRIGHTNESS_RANGE[0], "sin")
        ])
        delta = min(a.OVERLAP, roundInt(clip.props["audioDur"] * a.OVERLAP_PERCENT))
        ms += delta
        clips.append(clip)
stepTime = logTime(stepTime, "Created sequence")

for i, c in enumrate(clips):
    c.setProp("index", i)

processComposition(a, clips, ms, sampler, stepTime, startTime)
