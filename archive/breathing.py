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

parser.add_argument('-data', dest="DATA_FILE", default="../media/downloads/m002.csv", help="Path to data file generated from breathing_data.py")
parser.add_argument('-bcount', dest="BREADTH_COUNT", default=4, type=int, help="Number of breadths")
parser.add_argument('-lim', dest="LIMIT_DATA", default=120, type=int, help="Limit data in seconds, -1 if no limit")
parser.add_argument('-cpb', dest="CLIPS_PER_BREADTH", default=64, type=int, help="Number of clips to play per breadth")
parser.add_argument('-rvb', dest="REVERB", default=80, type=int, help="Reverberence (0-100)")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

STRETCH_RANGE = (1.0, 2.5)
VOLUME_RANGE = (0.9, 0.2)

REDUCE_DATA = a.LIMIT_DATA * 1000
startTime = logTime()

# Read data
breathingFields, breathingData = readCsv(a.DATA_FILE, encoding=False)
stepTime = logTime(startTime, "Read breathing data")

# Get sample data
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)
stepTime = logTime(stepTime, "Read samples")
if a.COUNT > 0:
    if a.COUNT <= sampleCount:
        samples = sortBy(samples, ("clarity", "desc")) # get samples with most clarity
        samples = samples[:a.COUNT]
        sampleCount = a.COUNT
    else:
        print("Warning: %s samples requested, but only %s found" % (a.COUNT, sampleCount))
samples = prependAll(samples, ("filename", a.MEDIA_DIRECTORY))
samples = addIndices(samples)

if REDUCE_DATA > 0:
    breathingData = breathingData[:REDUCE_DATA]

# Find peaks
minima, maxima = findPeaks([d["resp"] for d in breathingData], distance=2200, height=0.0) # require at least 2.2 seconds between peaks
breadthCount = min(len(minima), len(maxima)) - 1 # subtract one because we skip the first minima
print("Found %s peaks" % breadthCount)
stepTime = logTime(stepTime, "Find peaks")

if breadthCount < a.BREADTH_COUNT:
    print("Warning: Not enough data! Found %s, but need %s breadths" % (breadthCount, a.BREADTH_COUNT))

# create clips, viewport, and container
clips = samplesToClips(samples)
currentFrame = 1
startMs = minima[1]

for i, ms0 in enumerate(minima):
    # Start at second minima
    if i < 1:
        continue

    if i >= a.BREADTH_COUNT:
        break

    # Find the next maxima
    peakms = findNextValue(maxima, ms0)
    if peakms is None:
        print("Could not find maxima after %s" % formatSeconds(ms0/1000.0))
        break

    # Find next minima
    if i >= len(minima)-2:
        print("Could not find minima after %s" % formatSeconds(ms0/1000.0))
        break
    ms1 = minima[i+1]

    breadthDuration = ms1 - ms0
    breadthData = breathingData[ms0:ms1]
    print("Breadth %s duration: %sms" % (i+1, breadthDuration))

    inhaleDuration = peakms - ms0
    exhaleDuration = ms1 - peakms

    # Pick a random clip and find its neighbors
    rseed = i + a.RANDOM_SEED
    clipIndex = pseudoRandom(rseed, range=(0, sampleCount-1), isInt=True)
    clip = clips[clipIndex]
    neighbors = clip.getNeighbors(clips, a.CLIPS_PER_BREADTH-1, "tsne", "tsne2", "index")
    breadthClips = [clip] + neighbors
    m = 0.9
    inhaleStep = roundInt(m * inhaleDuration / a.CLIPS_PER_BREADTH)
    exhaleStep = roundInt(m * exhaleDuration / a.CLIPS_PER_BREADTH)

    for j, c in enumerate(breadthClips):
        count = a.CLIPS_PER_BREADTH-1
        progress = 1.0*j/count
        # 1. Breathe in, the clips expand and play backwards
        start = inhaleStep * (count-j) + ms0 - startMs
        volume = lerp(VOLUME_RANGE, progress) # correlelates to distance to selected clip
        pan = lerp((-1.0, 1.0), c.props["tsne"]) # TODO: correlates to x position
        fadeDur = roundInt(clip.dur * 0.5) # half length of clip
        stretch = lim(1.0 * inhaleDuration / clip.dur * (1.0-progress), STRETCH_RANGE)
        c.queuePlay(start, {"volume": volume, "pan": pan, "stretch": stretch, "fadeIn": fadeDur, "reverse": True, "reverb": a.REVERB})

        # 2. Breathe out, the clips release and play forwards
        start = exhaleStep * j + peakms - startMs
        stretch = lim(1.0 * exhaleDuration / clip.dur * progress, STRETCH_RANGE)
        c.queuePlay(start, {"volume": volume, "pan": pan, "stretch": stretch, "fadeOut": fadeDur, "reverb": a.REVERB})

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
