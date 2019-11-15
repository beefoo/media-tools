# -*- coding: utf-8 -*-

import argparse
import os
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from PIL import Image, ImageDraw
from pprint import pprint
import shutil
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
parser.add_argument('-toffset', dest="TEXT_OFFSET", default=1000, type=int, help="Start text fade in this much time after the frame fades in")
parser.add_argument('-tfade', dest="TEXT_FADE", default=500, type=int, help="Fade in/out text duration")
parser.add_argument('-tstyle', dest="TEXT_STYLE", default="h3", help="Text style: p, h1, h2, h3")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just view statistics")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
parser.add_argument('-debug', dest="DEBUG", default=-1, type=int, help="Debug frame")
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
hasError = False
for group in groupNames:
    groupData = groupLookup[group]
    frameCount = -1
    # Q/A frame count
    for item in groupData['items']:
        itemFrames = getFilenames(item['frames'] % '*')
        itemFrameCount = len(itemFrames)
        if frameCount < 0:
            frameCount = itemFrameCount
        elif frameCount != itemFrameCount:
            print("%s framecount (%s) differs from %s (%s)" % (groupData['items'][0]['frames'], frameCount, item['frames'], itemFrameCount))
            hasError = True
        # Check for audio file
        if not os.path.isfile(item['audio']):
            print("Error: could not find audio file %s" % item['audio'])
            hasError = True
    groupLookup[group]['frameStart'] = frameStart
    groupLookup[group]['frameCount'] = frameCount
    groupLookup[group]['durMs'] = frameToMs(frameCount, a.FPS)
    groupLookup[group]['startMs'] = frameToMs(frameStart, a.FPS)
    groupLookup[group]['endMs'] = frameToMs(frameStart+frameCount, a.FPS)
    print("%s: %s -> %s" % (group, formatSeconds(groupLookup[group]['startMs']/1000.0), formatSeconds(groupLookup[group]['endMs']/1000.0)))
    frameStart += frameCount

totalFrames = frameStart
durationMs = groupLookup[groupNames[-1]]['endMs']

if a.PROBE or hasError:
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

# Determine fade start/stop for each step
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

    instructions[i]['ms'] = startMs
    instructions[i]['durMs'] = durMs
    instructions[i]['endMs'] = startMs + durMs
    instructions[i]['fadeInStartMs'] = groupStartMs
    instructions[i]['fadeInEndMs'] = groupStartMs + fadeIn
    instructions[i]['fadeInDurMs'] = fadeIn
    instructions[i]['fadeOutStartMs'] = groupEndMs - fadeOut
    instructions[i]['fadeOutEndMs'] = groupEndMs
    instructions[i]['fadeOutDurMs'] = fadeOut

    if 'text' in step and len(step['text']) > 0:
        textFadeDurMs = min(a.TEXT_FADE, roundInt((durMs - fadeIn - fadeOut - a.TEXT_OFFSET) * 0.5))
        textFadeInStartMs = instructions[i]['fadeInEndMs'] + a.TEXT_OFFSET
        textFadeInEndMs = textFadeInStartMs + textFadeDurMs
        textFadeOutEndMs = textFadeInStartMs + roundInt(step['textdur'] * 1000)
        textFadeOutStartMs = textFadeOutEndMs - textFadeDurMs
        instructions[i]['textFadeDurMs'] = textFadeDurMs
        instructions[i]['textFadeInStartMs'] = textFadeInStartMs
        instructions[i]['textFadeInEndMs'] = textFadeInEndMs
        instructions[i]['textFadeOutStartMs'] = textFadeOutStartMs
        instructions[i]['textFadeOutEndMs'] = textFadeOutEndMs

audioFilename = replaceFileExtension(a.OUTPUT_FILE, ".mp3")

# Do audio
if not a.VIDEO_ONLY and (a.OVERWRITE or not os.path.isfile(audioFilename)) and a.DEBUG < 0:

    audioInstructions = []

    for i, step in enumerate(instructions):
        audioInstructions.append({
            "ms": step['ms'],
            "filename": step["audio"],
            "start": step['fadeInStartMs'],
            "dur": step['durMs'],
            "fadeIn": step['fadeInDurMs'],
            "fadeOut": step['fadeOutDurMs']
        })

    mixAudio(audioInstructions, durationMs, audioFilename)

# Do video
if a.AUDIO_ONLY:
    sys.exit()

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

tprops = getTextProperties(a)
_, lineHeight, _ = getLineSize(tprops[a.TEXT_STYLE]['font'], 'A')

def getFrameFromTime(step, ms, image=False):
    global groupLookup

    progressMs = ms - step['ms']
    stepMs = step['fadeInStartMs'] + progressMs
    frame = msToFrame(stepMs, a.FPS) + 1

    groupData = groupLookup[step[a.GROUP_BY]]
    frame = min(frame, groupData['frameCount'])
    frameFilename = step['frames'] % zeroPad(frame, groupData['frameCount'])

    frameImage = None
    if image:
        frameImage = Image.open(frameImage)

    # determine alpha
    alpha = 1.0
    if step['fadeInDurMs'] > 0 and progressMs < step['fadeInDurMs']:
        alpha = 1.0 * progressMs / step['fadeInDurMs']
    elif step['fadeOutDurMs'] > 0 and ms > step['fadeOutStartMs']:
        alpha = norm(ms, (step['fadeOutStartMs'], step['fadeOutEndMs']), limit=True)
    alpha = ease(alpha)

    return {
        'filename': frameFilename,
        'image': frameImage,
        'alpha': alpha
    }

progress = 0
def doFrame(f):
    global progress
    global frameCount
    global instructions
    global tprops
    global lineHeight

    frameSteps = [i for i in instructions if i['ms'] <= f['ms'] < i['endMs']]

    if len(frameSteps) < 1:
        print('Error: no instructions at %s' % formatSeconds(f['ms']/1000.0))
        return

    if len(frameSteps) > 2:
        print('Warning: more than two steps at %s' % formatSeconds(f['ms']/1000.0))

    baseImage = None
    step = frameSteps[0]

    if len(frameSteps) > 1:
        frame0 = getFrameFromTime(frameSteps[0], f['ms'], image=True)
        frame1 = getFrameFromTime(frameSteps[1], f['ms'], image=True)
        baseImage = Image.blend(frame0['image'], frame1['image'], frame0['alpha'])

    # check if text is visible
    elif 'text' in step and len(step['text']) > 0 and step['textFadeInStartMs'] < f['ms'] < step['textFadeOutEndMs']:
        textAlpha = 1.0
        if f['ms'] < step['textFadeInEndMs']:
            textAlpha = norm(f['ms'], (step['textFadeInStartMs'], step['textFadeInEndMs']), limit=True)
        elif f['ms'] > step['textFadeOutStartMs']:
            textAlpha = norm(f['ms'], (step['textFadeOutStartMs'], step['textFadeOutEndMs']), limit=True)

        if textAlpha > 0.0:
            sourceFrame = getFrameFromTime(step, f['ms'], image=True)
            baseImage = sourceFrame['image']
            lines = addTextMeasurements([{
                "type": a.TEXT_STYLE,
                "text": step['text']
            }], tprops)
            width, height = baseImage.size
            x = roundInt(width * 0.05)
            y = height - x - lineHeight
            c = roundInt(textAlpha * 255.0)
            baseImage = linesToImage(lines, None, width, height, color="#ffffff", bgColor="#000000", x=x, y=y, bgImage=baseImage, alpha=textAlpha)

    # No processing necessary, just copy frame over
    if baseImage is None:
        sourceFrame = getFrameFromTime(step, f['ms'])
        shutil.copyfile(sourceFrame['filename'], f['filename'])

    else:
        baseImage.save(f['filename'])

    progress += 1
    printProgress(progress, frameCount)

for f in range(totalFrames):
    frame = f + 1
    if a.DEBUG > 0 and frame != a.DEBUG:
        continue
    ms = frameToMs(frame, a.FPS)
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    if not a.OVERWRITE and os.path.isfile(filename) and a.DEBUG < 0:
        continue
    videoFrames.append({
        "frame": frame,
        "filename": filename,
        "ms": ms
    })

threads = getThreadCount(a.THREADS)

if threads > 1:
    pool = ThreadPool(threads)
    pool.map(doFrame, videoFrames)
    pool.close()
    pool.join()
else:
    for i, f in enumerate(videoFrames):
        doFrame(f)

if a.VIDEO_ONLY:
    audioFilename = False

if a.DEBUG > 0:
    sys.exit()

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFilename)
