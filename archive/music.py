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
parser.add_argument('-buf', dest="BUFFER_SIZE", default=512, type=int, help="Max number of samples in buffer at any given time")
parser.add_argument('-unit', dest="SAMPLE_UNIT", default=64, type=int, help="Rate at which to add/remove samples to/from buffer")
parser.add_argument('-vfilter', dest="FILTER_VIDEOS", default="samples>500&medianPower>0.5", help="Query string to filter videos by")
parser.add_argument('-filter', dest="FILTER", default="power>0&octave>=0", help="Query string to filter samples by")
parser.add_argument('-sort', dest="SORT", default="power=desc=0.5&clarity=desc", help="Query string to sort samples by")
parser.add_argument('-ptl', dest="PERCENTILE", default=0.2, type=float, help="Top percentile of samples to select from each film")
parser.add_argument('-lim', dest="LIMIT", default=100, type=int, help="Limit number of samples per film")
parser.add_argument('-beatms', dest="BEAT_MS", default=256, type=int, help="Milliseconds per beat")
parser.add_argument('-beats', dest="BEATS_PER_MEASURE", default=8, type=int, help="Number of beats per measure")
parser.add_argument('-seq', dest="NUMBER_SEQUENCE", default="3,5,7", help="Three-number sequence for determining pulse duration")
a = parser.parse_args()
parseVideoArgs(a)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CACHE_FILE])

# parse number sequences
PLAY_DUR_SEQUENCE = [int(n) for n in a.NUMBER_SEQUENCE.split(",")]
REST_DUR_SEQUENCE = piDigits()
PLAY_SEQ_LEN = len(PLAY_DUR_SEQUENCE)
REST_SEQ_LEN = len(REST_DUR_SEQUENCE)
VOLUME_RANGE = (0.0, 1.0)

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

def fillQueue(q):
    global a
    global currentVideoIndex
    global videos
    global videoCount

    if currentVideoIndex >= videoCount:
        return q

    while len(q) < a.SAMPLE_UNIT and currentVideoIndex < videoCount:
        v = videos[currentVideoIndex]
        currentVideoIndex += 1
        # read samples
        sampleDataFilename = a.SAMPLE_DATA_DIR + v["filename"] + ".csv"
        _, samples = readCsv(sampleDataFilename)
        # filter, sort, and limit
        samples = filterByQueryString(samples, a.FILTER)
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

def addToBuffer(samples, buf, size):
    bufSize = len(buf)
    sampleCount = len(samples)
    totalSize = bufSize + sampleCount
    delta = totalSize - size

    buf += samples
    if delta > 0:
        buf = buf[delta:]

    return buf

def removeFromBuffer(sampleCount, buf):
    bufSize = len(buf)
    if bufSize > sampleCount:
        return buf[sampleCount:]
    else:
        return []

def getMeasureMs(m):
    global a
    return m * a.BEATS_PER_MEASURE * a.BEAT_MS

def getPulse(startMs, count, playMeasures, restMeasures, beatsPerMeasure, beatMs, samples, step=None):
    seq = []
    restMs = getMeasureMs(restMeasures)
    playMs = getMeasureMs(playMeasures)
    msPerCount = restMs + playMs
    beatsPerCount = int(playMs / beatMs)

    # Populate beats with samples
    beats = [None for b in range(beatsPerMeasure)]
    divisions = int(math.log(beatsPerMeasure, 2))
    sampleIndex = 0
    sampleLen = len(samples)
    for i in range(divisions):
        add = 1
        offset = 0
        if i > 0:
            add = 2 ** (i-1)
            offset = int(2 ** (-i) * beatsPerMeasure)
        for j in range(add):
            beatIndex = offset + offset * 2 * j
            if sampleIndex < sampleLen:
                beats[beatIndex] = samples[sampleIndex]
                sampleIndex += 1

    # Each step is a set of rest measures followed by a set of play measures
    for i in range(count):
        countMs = startMs + i * msPerCount + restMs
        # Each step is a beat in a set of play measures
        for j in range(beatsPerCount):
            progress = 1.0 * j / (beatsPerCount-1) if beatsPerCount > 1 else 0.0
            beatIndex = j % beatsPerMeasure
            beat = beats[beatIndex]
            if beat is not None:
                ms = countMs + j * beatMs
                volume = lerp(VOLUME_RANGE, easeInOut(progress))
                fadeInDur = getClipFadeDur(beat["dur"])
                fadeOutDur = getClipFadeDur(beat["dur"], 0.25)
                pan = 0
                if step is not None:
                    pan = lerp((-1, 1), progress)
                    if (step+i) % 2 > 0:
                        pan = lerp((-1, 1), 1.0-progress)
                seq.append({
                    "ms": ms,
                    "filename": a.MEDIA_DIRECTORY + beat["filename"],
                    "start": beat["start"],
                    "dur": beat["dur"],
                    "volume": volume,
                    "fadeOut": fadeOutDur,
                    "fadeIn": fadeInDur,
                    "pan": pan,
                    "reverb": a.REVERB,
                    "matchDb": a.MATCH_DB
                })
    return seq

def playUnit(msI, msII, msIII, buf, step):
    global a

    # Group samples by notes
    noteGroups = groupList(buf, "note")

    # Sort by group size
    noteGroups = sorted(noteGroups, key=lambda g: g["count"], reverse=True)

    # Determine groups
    groupI = noteGroups[0]["items"] if len(noteGroups) > 0 else []
    groupII = noteGroups[1]["items"] if len(noteGroups) > 1 else []
    # Group I is high power, high clarity
    if len(groupI) > a.BEATS_PER_MEASURE:
        groupI = sortBy(groupI, [("power", "desc", 0.5), ("clarity", "desc")], a.BEATS_PER_MEASURE)
    # Group II is high clarity, low pitch
    if len(groupII) > a.BEATS_PER_MEASURE:
        groupII = sortBy(groupII, [("clarity", "desc", 0.5), ("hz", "asc")], a.BEATS_PER_MEASURE)
    # Group III is low clarity, short duration
    groupIII = sortBy(buf, [("clarity", "asc", 0.5), ("dur", "asc")], a.BEATS_PER_MEASURE * 2)

    # determine duration
    measureMs = a.BEATS_PER_MEASURE * a.BEAT_MS
    groupIIIMeasures, groupIIMeasures, groupIMeasures = tuple(PLAY_DUR_SEQUENCE)
    groupIIMeasuresRest = REST_DUR_SEQUENCE[msII % REST_SEQ_LEN]
    groupIIIMeasuresRest = REST_DUR_SEQUENCE[(msIII+1) % REST_SEQ_LEN]
    groupIDur = getMeasureMs(groupIMeasures)
    groupIIMeasureDelta = (msII - msI) / measureMs
    groupIICount = roundInt((groupIMeasures-groupIIMeasureDelta) / (groupIIMeasures + groupIIMeasuresRest))
    groupIIDur = getMeasureMs((groupIIMeasures + groupIIMeasuresRest) * groupIICount)
    groupIIIMeasureDelta = (msIII - msI) / measureMs
    groupIIICount = roundInt((groupIMeasures-groupIIIMeasureDelta) / (groupIIIMeasures + groupIIIMeasuresRest))
    groupIIIDur = getMeasureMs((groupIIIMeasures + groupIIIMeasuresRest) * groupIIICount)

    seq = []
    seq += getPulse(msI, 1, groupIMeasures, 0, a.BEATS_PER_MEASURE, a.BEAT_MS, groupI, step)
    seq += getPulse(msII, groupIICount, groupIIMeasures, groupIIMeasuresRest, a.BEATS_PER_MEASURE, a.BEAT_MS, groupII, step+1)
    seq += getPulse(msIII, groupIIICount, groupIIIMeasures, groupIIIMeasuresRest, a.BEATS_PER_MEASURE * 2, a.BEAT_MS/2, groupIII)

    return (msI + groupIDur, msII + groupIIDur, msIII + groupIIIDur, seq)

buffer = []
queue = []
queue = fillQueue(queue)
msI = 0
msII = 0
msIII = 0
audioSequence = []
step = 0

# Each step in this loop is considered a "unit" which consists of some number of measures
while True:
    # Retrieve samples from queue
    samplesToAdd, queue = dequeue(queue, a.SAMPLE_UNIT)

    # add samples to buffer
    if len(samplesToAdd) > 0:
        buffer = addToBuffer(samplesToAdd, buffer, a.BUFFER_SIZE)

    # if no more samples, start removing samples from buffer
    else:
        buffer = removeFromBuffer(a.SAMPLE_UNIT, buffer)
        # buffer is empty, we're done
        if len(buffer) <= 0:
            break

    msI, msII, msIII, unitSequence = playUnit(msI, msII, msIII, buffer, step)
    # print(len(unitSequence))
    audioSequence += unitSequence

    # Attempt to fill queue with more samples
    queue = fillQueue(queue)

    step += 1

    if len(buffer) >= a.BUFFER_SIZE:
        break

# plotAudioSequence(audioSequence)
# sys.exit()

stepTime = logTime(startTime, "Processed audio clip sequence")

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
