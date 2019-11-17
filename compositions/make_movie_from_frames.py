# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
from PIL import Image, ImageDraw
from pprint import pprint
import shutil
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

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
parser.add_argument('-collections', dest="COLLECTIONS_FILE", default="path/to/collections.csv", help="Input csv collections file")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/movie_frames/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/movie.mp4", help="Output media file")
parser.add_argument('-fps', dest="FPS", default=24, type=int, help="Output video frames per second")
parser.add_argument('-threads', dest="THREADS", default=6, type=int, help="Amount of parallel frames to process (too many may result in too many open files)")
parser.add_argument('-ao', dest="AUDIO_ONLY", action="store_true", help="Render audio only?")
parser.add_argument('-vo', dest="VIDEO_ONLY", action="store_true", help="Render video only?")
parser.add_argument('-toffset', dest="TEXT_OFFSET", default=2000, type=int, help="Start text fade in this much time after the frame fades in")
parser.add_argument('-tfade', dest="TEXT_FADE", default=2000, type=int, help="Fade in/out text duration")
parser.add_argument('-tstyle', dest="TEXT_STYLE", default="h3", help="Text style: p, h1, h2, h3")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just view statistics")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
parser.add_argument('-debug', dest="DEBUG", default=-1, type=int, help="Debug frame")
a = parser.parse_args()
aa = vars(a)

_, instructions = readCsv(a.INPUT_FILE)
instructionCount = len(instructions)
_, collections = readCsv(a.COLLECTIONS_FILE)
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

if len(instructions) <= 0:
    print("No instructions in %s" % a.INPUT_FILE)
    sys.exit()

# Infer group order from instructions
groupNames = []
for i in instructions:
    if i['comp'] not in groupNames:
        groupNames.append(i['comp'])

# get frames for each collection
hasError = False
for i, c in enumerate(collections):
    cAudioFiles = {}
    cFrames = []
    gFrameStart = 0
    for j, groupName in enumerate(groupNames):

        cFramesFile = c['frame_dir'] + c['uid'] + '_' + groupName + '_frames/frame.*.png'
        gFrames = sorted(getFilenames(cFramesFile, verbose=False))
        gFrameCount = len(gFrames)

        gAudioFilename = c['audio_dir'] + c['uid'] + '_' + zeroPad(j+1, 10) + '_' + groupName + '.mp3'
        # Check for audio file
        if not os.path.isfile(gAudioFilename):
            print("Error: could not find audio file %s" % gAudioFilename)
            hasError = True

        cAudioFiles[groupName] = {
            'filename': gAudioFilename,
            'frameStart': gFrameStart,
            'frameCount': gFrameCount,
            'durMs': frameToMs(gFrameCount, a.FPS),
            'startMs': frameToMs(gFrameStart, a.FPS),
            'endMs': frameToMs(gFrameStart+gFrameCount, a.FPS)
        }
        gFrameStart += gFrameCount
        cFrames += gFrames

    collections[i]['audioFiles'] = cAudioFiles
    collections[i]['frameFiles'] = cFrames

# Check frameCounts
frameCount = -1
for c in collections:
    cFrameCount = len(c['frameFiles'])
    if frameCount < 0:
        frameCount = cFrameCount
    elif frameCount != cFrameCount:
        print("%s framecount (%s) differs from %s (%s)" % (collections[0]['uid'], frameCount, c['uid'], cFrameCount))
        hasError = True
        break

collectionLookup = createLookup(collections, 'uid')
totalFrames = frameCount
durationMs = frameToMs(totalFrames, a.FPS)

print('Total frames: %s' % totalFrames)
print('Duration: %s' % formatSeconds(durationMs/1000.0))

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
    startMs = timecodeToMs(step["start"]) # time this step starts in the full sequence
    prevStep = instructions[i-1] if i > 0 else None
    nextStep = instructions[i+1] if i < instructionCount-1 else None
    fadeIn = roundInt(prevStep['fade'] * 1000) if prevStep is not None else 0
    fadeOut = roundInt(step['fade'] * 1000)
    durMs = timecodeToMs(nextStep["start"]) - startMs if nextStep is not None else durationMs - startMs

    # Determine audio properties
    collection = collectionLookup[step['uid']]
    audio = collection['audioFiles'][step['comp']]
    audioMs = startMs
    audioStartMs = startMs - audio['startMs'] # start time within the audio file
    audioDurMs = timecodeToMs(nextStep["start"]) - startMs if nextStep is not None else audio['durMs'] - audioStartMs
    audioDurMs = min(audioDurMs, audio['durMs'] - audioStartMs)
    audioEndMs = audioStartMs + audioDurMs
    audioFadeIn = fadeIn
    audioFadeOut = fadeOut
    # only fade in if there's enough time in the beginning
    audioFadeIn = min(audioStartMs, audioFadeIn)
    # only fade out if there's enough time in the end
    audioFadeOut = min(audio['durMs'] - audioEndMs, audioFadeOut)
    audioFadeOut = max(audioFadeOut, 0)

    # adjust start and duration based on fade
    startMs -= roundInt(fadeIn * 0.5)
    durMs += roundInt(fadeIn * 0.5)
    durMs += roundInt(fadeOut * 0.5)

    # adjust start and duration based on fade
    audioStartMs -= roundInt(audioFadeIn * 0.5)
    audioMs -= roundInt(audioFadeIn * 0.5)
    audioDurMs += roundInt(audioFadeIn * 0.5)
    audioDurMs += roundInt(audioFadeOut * 0.5)

    instructions[i]['ms'] = startMs
    instructions[i]['durMs'] = durMs
    instructions[i]['endMs'] = startMs + durMs
    instructions[i]['fadeInEndMs'] = startMs + fadeIn
    instructions[i]['fadeOutDurMs'] = fadeOut
    instructions[i]['fadeOutStartMs'] = startMs + durMs - fadeOut
    instructions[i]['fadeOutEndMs'] = startMs + durMs

    instructions[i]['audioFile'] = audio['filename']
    instructions[i]['audioMs'] = audioMs
    instructions[i]['audioStartMs'] = audioStartMs
    instructions[i]['audioDurMs'] = audioDurMs
    instructions[i]['audioFadeInDurMs'] = audioFadeIn
    instructions[i]['audioFadeOutDurMs'] = audioFadeOut

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

# for i in instructions:
#     print('%s -> %s (%s)' % (formatSeconds(i['fadeInStartMs']/1000.0), formatSeconds(i['fadeOutEndMs']/1000.0), os.path.basename(i['audioFile'])))
# sys.exit()

audioFilename = replaceFileExtension(a.OUTPUT_FILE, ".mp3")

# Do audio
if not a.VIDEO_ONLY and (a.OVERWRITE or not os.path.isfile(audioFilename)) and a.DEBUG < 0:

    audioInstructions = []

    for i, step in enumerate(instructions):
        audioInstructions.append({
            "ms": step['audioMs'],
            "filename": step["audioFile"],
            "start": step['audioStartMs'],
            "dur": step['audioDurMs'],
            "fadeIn": step['audioFadeInDurMs'],
            "fadeOut": step['audioFadeOutDurMs']
        })

    mixAudio(audioInstructions, durationMs, audioFilename)

# Do video
if a.AUDIO_ONLY:
    sys.exit()

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

tprops = getTextProperties(a)
_, lineHeight, _ = getLineSize(tprops[a.TEXT_STYLE]['font'], 'A')

def getFrameData(step, ms, frame, image=False):
    global collectionLookup
    global totalFrames

    cData = collectionLookup[step['uid']]
    cFrames = cData['frameFiles']
    frameIndex = lim(frame-1, (0, totalFrames-1))
    frameFilename = cFrames[frameIndex]

    frameImage = None
    if image:
        frameImage = Image.open(frameFilename)

    # determine alpha
    alpha = 0.0
    if step['fadeOutDurMs'] > 0 and ms > step['fadeOutStartMs']:
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
    global totalFrames
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
        frame0 = getFrameData(frameSteps[0], f['ms'], f['frame'], image=True)
        frame1 = getFrameData(frameSteps[1], f['ms'], f['frame'], image=True)
        baseImage = Image.blend(frame0['image'], frame1['image'], frame0['alpha'])

    # check if text is visible
    elif 'text' in step and len(step['text']) > 0 and step['textFadeInStartMs'] < f['ms'] < step['textFadeOutEndMs']:
        textAlpha = 1.0
        if f['ms'] < step['textFadeInEndMs']:
            textAlpha = norm(f['ms'], (step['textFadeInStartMs'], step['textFadeInEndMs']), limit=True)
        elif f['ms'] > step['textFadeOutStartMs']:
            textAlpha = 1.0 - norm(f['ms'], (step['textFadeOutStartMs'], step['textFadeOutEndMs']), limit=True)
        textAlpha = ease(textAlpha)

        if textAlpha > 0.0:
            sourceFrame = getFrameData(step, f['ms'], f['frame'], image=True)
            baseImage = sourceFrame['image']
            lines = addTextMeasurements([{
                "type": a.TEXT_STYLE,
                "text": step['text']
            }], tprops)
            width, height = baseImage.size
            x = roundInt(width * 0.02)
            y = height - x - lineHeight
            c = roundInt(textAlpha * 255.0)
            baseImage = linesToImage(lines, None, width, height, color="#ffffff", bgColor="#000000", x=x, y=y, bgImage=baseImage, alpha=textAlpha)

    # No processing necessary, just copy frame over
    if baseImage is None:
        sourceFrame = getFrameData(step, f['ms'], f['frame'])
        shutil.copyfile(sourceFrame['filename'], f['filename'])

    else:
        baseImage.save(f['filename'])

    progress += 1
    printProgress(progress, totalFrames)

videoFrames = []
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
