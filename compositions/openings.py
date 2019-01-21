# -*- coding: utf-8 -*-

# Opening:
#  Play all the opening scenes of films in a loop

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

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-mcount', dest="DIVIDE_COUNT", default=7, type=int, help="Amount of times to divide")
parser.add_argument('-interval', dest="INTERVAL", default=8192, type=int, help="Starting interval duration in ms")
parser.add_argument('-counts', dest="COUNTS", default=2, type=int, help="Amount of times to play each interval before multiplying")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

VOLUME_RANGE = (1.0, 0.333)

# Get sample data
startTime = logTime()
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
stepTime = logTime(startTime, "Read samples")

# clusterCount = ceilInt(math.log(sampleCount, 2))
beatsPerMeasure = 2 ** a.DIVIDE_COUNT
clusterCount = a.DIVIDE_COUNT
beats = [None for i in range(beatsPerMeasure)]

samples = prependAll(samples, ("filename", a.VIDEO_DIRECTORY))
samples = addIndices(samples)
samples, centers = addClustersToList(samples, "tsne", "tsne2", clusterCount)

# sort clusters by median clarity
clusters = []
for i in range(clusterCount):
    mclarity = np.median([s["clarity"] for s in samples if s["cluster"]==i])
    clusters.append((i, mclarity))
clusters = sorted(clusters, key=lambda c: c[1], reverse=True)
clusters = [c[0] for c in clusters]

# create clips
clips = samplesToClips(samples)
currentFrame = 1
totalTime = a.INTERVAL * a.COUNTS * a.DIVIDE_COUNT

print("Target time: %s" % formatSeconds(totalTime/1000.0))

for i in range(a.DIVIDE_COUNT):
    clipsToAdd = 1
    offset = 0
    if i > 0:
        clipsToAdd = 2 ** (i-1)
        offset = 2 ** (-i)
    offsetMs = offset * a.INTERVAL
    stepMs = offsetMs * 2
    startMs = a.INTERVAL * a.COUNTS * i
    dlerp = (1.0 * (i+1) / a.DIVIDE_COUNT)
    volume = lerp(VOLUME_RANGE, dlerp)
    print("Divide step %s: %sms" % (i, offsetMs))

    clusterIndex = clusters[i % clusterCount]
    clusterClips = [c for c in clips if c.props["cluster"]==clusterIndex]
    center = centers[clusterIndex]
    clusterClipCount = len(clusterClips)
    clusterClips = sorted(clusterClips, key=lambda c: distance(c.props['tsne'], c.props['tsne2'], center[0], center[1]))

    for j in range(clipsToAdd):
        intervalMs = offsetMs + j * stepMs
        ms = startMs + intervalMs

        lerpAmt = 1.0 * intervalMs / a.INTERVAL
        clipIndex = j % clusterClipCount
        clip = clusterClips[clipIndex]
        # print("%s: power(%s) hz(%s) clarity(%s)" % (lerpAmt, clip.props["power"], clip.props["hz"], clip.props["clarity"]))
        beatIndex = int((offset+j*(offset*2)) * beatsPerMeasure)
        beats[beatIndex] = clip

        fadeInDur = getClipFadeDur(clip.dur)
        fadeOutDur = getClipFadeDur(clip.dur, 0.25)
        pan = lerp((-1, 1), lerpAmt)

        while ms < totalTime:
            clip.queuePlay(ms, {
                "volume": volume,
                "fadeOut": fadeOutDur,
                "fadeIn": fadeInDur,
                "pan": pan,
                "reverb": a.REVERB,
                "matchDb": a.MATCH_DB
            })
            ms += a.INTERVAL

# get audio sequence
audioSequence = clipsToSequence(clips)
stepTime = logTime(stepTime, "Processed clip sequence")
print("%s clips in sequence" % len(unique([(c["filename"], c["start"]) for c in audioSequence])))

videoDurationMs = frameToMs(currentFrame, a.FPS)
audioDurationMs = getAudioSequenceDuration(audioSequence)
durationMs = max(videoDurationMs, audioDurationMs) + a.PAD_END
print("Video time: %s" % formatSeconds(videoDurationMs/1000.0))
print("Audio time: %s" % formatSeconds(audioDurationMs/1000.0))
print("Total time: %s" % formatSeconds(durationMs/1000.0))

if not a.VIDEO_ONLY and (not os.path.isfile(a.AUDIO_OUTPUT_FILE) or a.OVERWRITE):
    mixAudio(audioSequence, durationMs, a.AUDIO_OUTPUT_FILE)
    stepTime = logTime(stepTime, "Mix audio")

logTime(startTime, "Total execution time")
