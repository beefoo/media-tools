# -*- coding: utf-8 -*-

# Instructions
# 1. Breathe in, the clips expand and play backwards
# 2. Breathe out, the clips release and play forwards
# 3. Play similar-sounding clips on each breadth
# 4. Use real breathing data if possible

import argparse
import inspect
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
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-mcount', dest="MULTIPLY_COUNT", default=5, type=int, help="Amount of times to multiply")
parser.add_argument('-interval', dest="INTERVAL", default=4000, type=int, help="Starting interval duration in ms")
parser.add_argument('-counts', dest="COUNTS", default=4, type=int, help="Amount of times to play each interval before multiplying")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

startTime = logTime()

# Get sample data
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
stepTime = logTime(startTime, "Read samples")
if a.COUNT > 0:
    if a.COUNT <= sampleCount:
        samples = sortBy(samples, ("flatness", "asc")) # get samples with least flatness
        samples = samples[:a.COUNT]
        sampleCount = a.COUNT
    else:
        print("Warning: %s samples requested, but only %s found" % (a.COUNT, sampleCount))
samples = prependAll(samples, ("filename", a.VIDEO_DIRECTORY))
samples = addIndices(samples)
samples = sortBy(samples, [("power", "desc", 0.5), ("flatness", "asc")])

# create clips
clips = samplesToClips(samples)
currentFrame = 1
totalTime = a.INTERVAL * a.COUNTS * a.MULTIPLY_COUNT
clipIndex = 0

print("Target time: %s" % formatSeconds(totalTime/1000.0))

for i in range(a.MULTIPLY_COUNT):
    clipsToAdd = 1
    offset = 0
    if i > 0:
        clipsToAdd = 2 ** (i-1)
        offset = 2 ** (-i)
    offsetMs = offset * a.INTERVAL
    stepMs = offsetMs * 2
    startMs = a.INTERVAL * a.COUNTS * i

    for j in range(clipsToAdd):
        clip = clips[clipIndex]
        clipIndex += 1
        fadeDur = max(100, roundInt(clip.dur * 0.5))
        fadeDur = min(clip.dur, fadeDur)
        ms = startMs + offsetMs + j * stepMs
        while ms < totalTime:
            clip.queuePlay(ms, {"volume": 1.0, "fadeOut": fadeDur, "reverb": a.REVERB})
            ms += a.INTERVAL

# get audio sequence
audioSequence = clipsToSequence(clips)
stepTime = logTime(stepTime, "Processed clip sequence")

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
