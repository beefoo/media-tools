# -*- coding: utf-8 -*-

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
parser.add_argument('-sdir', dest="SAMPLE_DATA_DIR", default="tmp/", help="Directory of sample data")
parser.add_argument('-buf', dest="WINDOW_SIZE", default=1024, type=int, help="Max number of samples in window at any given time")
parser.add_argument('-vfilter', dest="FILTER_VIDEOS", default="samples>500&medianPower>0.5", help="Query string to filter videos by")
parser.add_argument('-filter', dest="FILTER", default="power>0&octave>=0&hz>20", help="Query string to filter samples by")
parser.add_argument('-sort', dest="SORT", default="power=desc=0.5&clarity=desc", help="Query string to sort samples by")
parser.add_argument('-ptl', dest="PERCENTILE", default=0.25, type=float, help="Top percentile of samples to select from each film")
parser.add_argument('-lim', dest="LIMIT", default=400, type=int, help="Limit number of samples per film")
parser.add_argument('-beatms', dest="BEAT_MS", default=1024, type=int, help="Milliseconds per beat")
parser.add_argument('-stepb', dest="STEP_BEATS", default=16, type=int, help="Beats per step")
parser.add_argument('-beats', dest="BEAT_DIVISIONS", default=3, type=int, help="Number of times to divide beat, e.g. 1 = 1/2 notes, 2 = 1/4 notes, 3 = 1/8th notes, 4 = 1/16 notes")
parser.add_argument('-loops', dest="CLIP_LOOPS", default=8, type=int, help="Number of times a clip should loop")
parser.add_argument('-clusters', dest="CLUSTERS", default=16, type=int, help="Number of clusters to divide the window of samples into")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.2,1.0", help="Volume range")
parser.add_argument('-steps', dest="STEPS", default=-1, type=int, help="Number of steps to render, -1 for all")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

VECTOR_FILE = "media/downloads/wnd10m.gdas.1986-01-29-18.6.json"

# parse number sequences
VOLUME_RANGE = [float(v) for v in a.VOLUME_RANGE.strip().split(",")]
UNIT_MS = roundInt(2 ** (-a.BEAT_DIVISIONS) * a.BEAT_MS)
STEP_MS = a.BEAT_MS * a.STEP_BEATS
print("Smallest unit: %ss" % UNIT_MS)
print("%ss per step" % roundInt(STEP_MS/1000.0))

# Get video data
startTime = logTime()
_, videos = readCsv(a.INPUT_FILE)

# Filter videos
videos = filterByQueryString(videos, a.FILTER_VIDEOS)
videoCount = len(videos)
print("%s videos after filtering" % videoCount)

# Sort videos such that films with the greatest volume will be in the middle
videos = sortBy(videos, ("medianPower", "asc"))
maxPower = max([v["medianPower"] for v in videos])
videos = addIndices(videos)
videos = sorted(videos, key=lambda v: v["medianPower"] if v["index"] % 2 == 0 else -v["medianPower"]+maxPower*2)
currentVideoIndex = 0

# from matplotlib import pyplot as plt
# plt.plot(range(len(videos)), [v["medianPower"] for v in videos])
# plt.show()

def fillQueue(q, size):
    global a
    global currentVideoIndex
    global videos
    global videoCount

    if currentVideoIndex >= videoCount:
        return q

    while len(q) < size and currentVideoIndex < videoCount:
        v = videos[currentVideoIndex]
        currentVideoIndex += 1
        # read samples
        sampleDataFilename = a.SAMPLE_DATA_DIR + v["filename"] + ".csv"
        _, samples = readCsv(sampleDataFilename)
        # filter, sort, and limit
        samples = filterByQueryString(samples, a.FILTER)
        samples = prependAll(samples, ("filename", a.VIDEO_DIRECTORY))
        # add a log of hz
        for i, s in enumerate(samples):
            samples[i]["hzLog"] = math.log(s["hz"])
        samples = sortByQueryString(samples, a.SORT)
        sampleCount = len(samples)
        targetLen = min(a.LIMIT, roundInt(sampleCount * a.PERCENTILE))
        if targetLen <= 0:
            samples = []
        else:
            samples = samples[:targetLen]
        # add samples to queue
        q += samples

    return q

def getClipsFromGroups(startMs, groups, dur, vectorMap):
    global a
    clips = []

    groupCount = len(groups)
    groupDur = roundInt(1.0 * dur / (groupCount-1)) if groupCount > 1 else dur
    intervalDur = roundInt(1.0 * dur / groupCount)

    # Each group is a sample cluster
    for i, group in enumerate(groups):
        groupStartMs = startMs + i * intervalDur
        # TODO: Drop cluster samples at respective pitch-power location

        # When a cluster is dropped, play each sample in order of position (top to bottom, left to right)
        for j, s in enumerate(group):
            if s["nx"] > 0 or s["ny"] > 0:
                group[j]["playOrder"] = math.hypot(s["nx"], s["ny"])
            else:
                group[j]["playOrder"] = 0
        group = addNormalizedValues(group, "playOrder", "nplay")

        group = addNormalizedValues(group, "clarity", "nclarity")
        for s in group:
            # round ms to nearest beat unit
            sampleStart = roundInt(roundToNearest(groupStartMs + s["nplay"] * groupDur, UNIT_MS))

            # clip duration is twice the sample duration, 1 second minimum
            sampleDur = min(s["dur"] * 2, 1000)
            fadeInDur = getClipFadeDur(s["dur"])
            fadeOutDur = getClipFadeDur(sampleDur, 0.5) # fade out half the clip

            # start volume is based on clarity
            startVolume = lerp(VOLUME_RANGE, s["nclarity"])

            # loop duration is ceiling of nearest beat unit
            loopDur = roundInt(ceilToNearest(sampleDur, UNIT_MS))

            # create clip
            copy = s.copy()
            copy["dur"] = sampleDur
            clip = Clip(copy)

            for k in range(a.CLIP_LOOPS):
                loopStart = sampleStart + k * loopDur
                progress = 1.0 * k / a.CLIP_LOOPS
                loopVolume = (1.0 - progress) * startVolume

                # TODO: change pan based on movement of clip
                pan = lerp((-1, 1), s["nx"])

                # play clip
                clip.queuePlay(loopStart, {
                    "volume": loopVolume,
                    "fadeOut": fadeOutDur,
                    "fadeIn": fadeInDur,
                    "pan": pan,
                    "reverb": a.REVERB
                })

            clips.append(clip)

    return clips

def getSampleGroups(window, groupCount):
    global a

    # If the sample count in window, just return the remainder as a single group
    minSize = a.WINDOW_SIZE / groupCount
    if len(window) < minSize:
        return ([], [window[:]])

    # add normalized values
    window = addNormalizedValues(window, "power", "nx")
    window = addNormalizedValues(window, "hzLog", "ny")
    for i, s in enumerate(window):
        # invert ny
        window[i]["ny"] = 1.0 - s["ny"]

    # Cluster the samples by power and pitch
    window, centers = addClustersToList(window, "power", "hzLog", groupCount)
    # plotList(window, "power", "hzLog", highlight="cluster")
    centers = [(i, pos) for i, pos in enumerate(centers)]
    centers = sorted(centers, key=lambda c: c[1][1]) # sort by hz
    count = len(centers)

    # Add the groups with lowest, highest, and median pitch
    clusterIndices = [centers[0][0], centers[-1][0], centers[int(count/2)][0]]
    sampleGroups = []
    for i in clusterIndices:
        sampleGroups.append([s for s in window if s["cluster"] == i])

    # Remove samples from window
    clusterIndices = set(clusterIndices)
    newWindow = [s for s in window if s["cluster"] not in clusterIndices]

    return (newWindow, sampleGroups)

vData = nx = ny = None
def getVectorMap(step):
    global vData
    global nx
    global ny

    if vData is None:
        print("Reading vector data %s" % VECTOR_FILE)
        with open(VECTOR_FILE) as f:
            d = json.load(f)
            nx = d["nx"]
            ny = d["ny"]
            vData = np.array(d["data"])
            vData = vData.reshape((ny, nx, 2))
            print("Loaded data: %s x %s x %s" % (ny, nx, 2))

    return vData

window = []
queue = []
queue = fillQueue(queue, a.WINDOW_SIZE)
step = 0
clips = []

activeFields = []

# Each step in this loop is considered a "unit" which consists of some number of measures
while True:
    ms = step * STEP_MS
    vm = getVectorMap(step)
    # Retrieve samples from queue
    sampleCountNeeded = a.WINDOW_SIZE - len(window)
    samplesToAdd, queue = dequeue(queue, sampleCountNeeded)
    window += samplesToAdd
    # plotList(window, "power", "hzLog")

    window, sampleGroups = getSampleGroups(window, a.CLUSTERS)
    # plotList([item for sublist in clipsGroups for item in sublist], "power", "hzLog", highlight="cluster")

    clips += getClipsFromGroups(ms, sampleGroups, STEP_MS, vm)

    # Attempt to fill queue with more samples
    queue = fillQueue(queue, a.WINDOW_SIZE)

    step += 1

    if len(queue) < 1:
        break

    if a.STEPS > 0 and step >= a.STEPS:
        break

# get audio sequence
audioSequence = clipsToSequence(clips)
stepTime = logTime(startTime, "Processed audio clip sequence")

# plotAudioSequence(audioSequence)
# sys.exit()

currentFrame = 1

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
