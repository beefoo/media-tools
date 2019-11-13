# -*- coding: utf-8 -*-

import argparse
import os
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from pprint import pprint
import sys

from lib.audio_mixer import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addTextArguments(parser)
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/manifest.csv", help="Input csv instruction file")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/movie_frames/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/movie.mp4", help="Output media file")
parser.add_argument('-fps', dest="FPS", default=24, type=int, help="Output video frames per second")
parser.add_argument('-groupby', dest="GROUP_BY", default="comp", help="Group instructions by")
parser.add_argument('-threads', dest="THREADS", default=6, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
parser.add_argument('-ao', dest="AUDIO_ONLY", action="store_true", help="Render audio only?")
parser.add_argument('-vo', dest="VIDEO_ONLY", action="store_true", help="Render video only?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just view statistics")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
a = parser.parse_args()
aa = vars(a)

fieldNames, instructions = readCsv(a.INPUT_FILE)
instructionCount = len(instructions)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

if len(instructions) <= 0:
    print("No instructions in %s" % a.INPUT_FILE)
    sys.exit()

# Infer group order from instructions
groupNames = []
for i in instructions:
    if i[a.GROUP_BY] not in groupNames:
        groupNames.append(i[a.GROUP_BY])
byGroup = groupList(instructions, a.GROUP_BY)
groupLookup = createLookup(byGroup, a.GROUP_BY)

frameStart = 0
for group in groupNames:
    groupData = groupLookup[group]
    frameCount = -1
    # Q/A frame count
    for item in groupData['items']:
        itemFrames = getFilenames(item['frames'])
        itemFrameCount = len(itemFrames)
        if frameCount < 0:
            frameCount = itemFrameCount
        elif frameCount != itemFrameCount:
            print("%s framecount (%s) differs from %s (%s)" % (groupData['items'][0]['frames'], frameCount, item['frames'], itemFrameCount))
    groupLookup[group]['frameStart'] = frameStart
    groupLookup[group]['frameCount'] = frameCount
    groupLookup[group]['durMs'] = frameToMs(frameCount, a.FPS)
    groupLookup[group]['startMs'] = frameToMs(frameStart, a.FPS)
    groupLookup[group]['endMs'] = frameToMs(frameStart+frameCount, a.FPS)
    print("%s: %s -> %s" % (group, formatSeconds(groupLookup[group]['startMs']/1000.0), formatSeconds(groupLookup[group]['endMs']/1000.0)))
    frameStart += frameCount

totalFrames = frameStart
durationMs = groupLookup[groupNames[-1]]['endMs']

if a.PROBE:
    sys.exit()

def getGroupByTime(ms):
    global groupLookup
    global groupNames

    group = groupLookup[groupNames[-1]]
    for groupName in groupNames:
        groupData = groupLookup[groupName]
        if ms < groupData['endMs']:
            group = groupData
            break

    return group

audioFilename = replaceFileExtension(a.OUTPUT_FILE, ".mp3")

# Do audio
if not a.VIDEO_ONLY and (a.OVERWRITE or not os.path.isfile(audioFilename)):

    audioInstructions = []

    for i, step in enumerate(instructions):
        startMs = timecodeToMs(step["start"])
        stepGroup = getGroupByTime(startMs)
        fadeIn = roundInt(step['fade'] * 1000)
        nextStep = instructions[i+1] if i < instructionCount-1 else None
        fadeOut = roundInt(nextStep['fade'] * 1000) if nextStep is not None else 0

        groupStartMs = startMs - stepGroup['startMs']
        durMs = timecodeToMs(nextStep["start"]) - startMs if nextStep is not None else stepGroup['durMs'] - groupStartMs
        groupEndMs = groupStartMs + durMs

        # only fade in if there's enough time in the beginning
        fadeIn = min(groupStartMs, fadeIn)

        # only fade out if there's enough time in the end
        fadeOut = min(stepGroup['durMs']-groupEndMs, fadeOut)
        fadeOut = max(fadeOut, 0)

        # adjust start and duration based on fade
        groupStartMs -= roundInt(fadeIn * 0.5)
        startMs -= roundInt(fadeIn * 0.5)
        durMs += roundInt(fadeIn * 0.5)
        durMs += roundInt(fadeOut * 0.5)

        audioInstructions.append({
            "ms": startMs,
            "filename": step["audio"],
            "start": groupStartMs,
            "dur": durMs,
            "fadeIn": fadeIn,
            "fadeOut": fadeOut
        })

    mixAudio(audioInstructions, durationMs, audioFilename)

# Do video
if a.AUDIO_ONLY:
    sys.exit()

lastFrame = a.OUTPUT_FRAME % zeroPad(totalFrames, totalFrames)

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

elif os.path.isfile(lastFrame):
    print("Frames already present, exiting.")
    sys.exit()

progress = 0
def doFrame(f):
    global progress
    global frameCount

    progress += 1
    printProgress(progress, frameCount)

for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    videoFrames.append({
        "frame": frame,
        "filename": a.OUTPUT_FRAME % zeroPad(frame, totalFrames),
        "ms": ms
    })

pool = ThreadPool(a.THREADS)
pool.map(doFrame, videoFrames)
pool.close()
pool.join()

if a.VIDEO_ONLY:
    audioFilename = False

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFilename)
