# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import subprocess
import sys

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
# add text properties
addTextArguments(parser)
parser.add_argument('-in', dest="INPUT_FILE", default="titles/credits.md", help="Input markdown file")
parser.add_argument('-sdir', dest="SAMPLE_DATA_DIR", default="tmp/", help="Input markdown file")
parser.add_argument('-mdir', dest="METADATA_DIR", default="tmp/", help="Input markdown file")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-fps', dest="FPS", default=30, type=int, help="Output video frames per second")
parser.add_argument('-pad0', dest="PAD_START", default=1000, type=int, help="Padding at start in ms")
parser.add_argument('-pad1', dest="PAD_END", default=2000, type=int, help="Padding at end in ms")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/credits.mp4", help="Output media file")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
parser.add_argument('-ds', dest="DEBUG_SECONDS", default=120, type=int, help="Debug time in seconds")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
parser.add_argument('-speed', dest="SCROLL_SPEED", default=3.0, type=float, help="How much to scroll per frame in px? assumes 30fps; assumes 1920x1080px")

parser.add_argument('-audio', dest="AUDIO_FILE", default="", help="Audio track to add to credits")
parser.add_argument('-astart', dest="AUDIO_START", default=0, type=int, help="Audio start in ms")
parser.add_argument('-afadein', dest="AUDIO_FADE_IN", default=3000, type=int, help="Fade in audio in ms")
parser.add_argument('-afadeout', dest="AUDIO_FADE_OUT", default=5000, type=int, help="Fade out audio in ms")
parser.add_argument('-apad0', dest="AUDIO_PAD_IN", default=500, type=int, help="Pad in audio in ms")
parser.add_argument('-apad1', dest="AUDIO_PAD_OUT", default=500, type=int, help="Pad out audio in ms")
a = parser.parse_args()
aa = vars(a)
aa["REAL_WIDTH"] = a.WIDTH
aa["REAL_HEIGHT"] = a.HEIGHT
aa["WIDTH"] = roundInt(a.WIDTH * a.RESIZE_RESOLUTION)
aa["HEIGHT"] = roundInt(a.HEIGHT * a.RESIZE_RESOLUTION)
aa["SCROLL_SPEED"] = a.SCROLL_SPEED * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["MAX_TEXT_WIDTH"] = roundInt(a.MAX_TEXT_WIDTH * a.WIDTH) if 0 < a.MAX_TEXT_WIDTH <= 1.0 else a.WIDTH

if len(a.OUTPUT_FRAME) < 1:
    aa["OUTPUT_FRAME"] = "tmp/%s/frame.%%s.png" % getBasename(a.OUTPUT_FILE)

# parse properties
tprops = getTextProperties(a)
TEXTBLOCK_X_OFFSET = roundInt(a.WIDTH * a.TEXTBLOCK_X_OFFSET)

# Read text
lines = parseMdFile(a.INPUT_FILE, a)
print("Found %s lines" % len(lines))

lines = addTextMeasurements(lines, tprops, maxWidth=a.MAX_TEXT_WIDTH)
tw, th = getBBoxFromLines(lines)

print("Size: %s x %s" % (tw, th))
totalFrames = roundInt((th+a.HEIGHT) / a.SCROLL_SPEED) + msToFrame(a.PAD_START + a.PAD_END, a.FPS)
durationMs = frameToMs(totalFrames, a.FPS)
print("Total time: %s" % formatSeconds(durationMs/1000.0))

# make dirs
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# remove existing files
if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

# get frame sequence

print("Making video frame sequence...")
startMs = a.PAD_START
endMs = durationMs - a.PAD_END
debugFrame = msToFrame(a.DEBUG_SECONDS*1000, a.FPS)
for f in range(totalFrames):
    frame = f + 1
    if a.DEBUG and frame != debugFrame:
        continue
    ms = frameToMs(frame, a.FPS)
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    if ms <= startMs or ms > endMs:
        saveBlankFrame(filename, a.REAL_WIDTH, a.REAL_HEIGHT, bgColor=a.BG_COLOR, overwrite=a.OVERWRITE)
    else:
        nprogress = norm(ms, (startMs, endMs), limit=True)
        y = lerp((a.HEIGHT, -(th+a.HEIGHT)), nprogress)
        linesToImage(lines, filename, a.WIDTH, a.HEIGHT,
                        color=a.TEXT_COLOR,
                        bgColor=a.BG_COLOR,
                        y=y,
                        tblockXOffset=TEXTBLOCK_X_OFFSET,
                        resizeResolution=a.RESIZE_RESOLUTION,
                        overwrite=a.OVERWRITE)
    printProgress(frame, totalFrames)

audioFile = a.OUTPUT_FILE.replace(".mp4", ".mp3")
audioDur = durationMs
if len(a.AUDIO_FILE) > 0:
    if not os.path.isfile(audioFile) or a.OVERWRITE:
        srcDur = floorInt(getDurationFromFile(a.AUDIO_FILE, accurate=True) * 1000)
        print("Source audio dur: %s" % formatSeconds(srcDur/1000.0))
        clipDur = audioDur - a.AUDIO_PAD_IN - a.AUDIO_PAD_OUT
        if a.AUDIO_START + clipDur > srcDur:
            print("Source audio not long enough (%s > %s)" % (a.AUDIO_START + clipDur, srcDur))
        instructions = [{
            "ms": a.AUDIO_PAD_IN,
            "filename": a.AUDIO_FILE,
            "start": a.AUDIO_START,
            "dur": clipDur,
            "volume": 1.0,
            "fadeIn": a.AUDIO_FADE_IN,
            "fadeOut": a.AUDIO_FADE_OUT,
            "matchDb": -16
        }]
        if a.DEBUG:
            sys.exit()
        mixAudio(instructions, audioDur, audioFile)
else:
    makeBlankAudio(audioDur, audioFile)

if a.DEBUG:
    sys.exit()

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile)
