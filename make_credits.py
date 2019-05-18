# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import subprocess
import sys

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
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/credits/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/credits.mp4", help="Output media file")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
parser.add_argument('-ds', dest="DEBUG_SECONDS", default=120, type=int, help="Debug time in seconds")
parser.add_argument('-speed', dest="SCROLL_SPEED", default=2.0, type=float, help="(scroll mode only) How much to scroll per frame in px? assumes 30fps; assumes 1920x1080px")
a = parser.parse_args()
aa = vars(a)
aa["SCROLL_SPEED"] = a.SCROLL_SPEED * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["MAX_TEXT_WIDTH"] = roundInt(a.MAX_TEXT_WIDTH * a.WIDTH) if 0 < a.MAX_TEXT_WIDTH <= 1.0 else a.WIDTH

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
        saveBlankFrame(filename, a.WIDTH, a.HEIGHT, bgColor=a.BG_COLOR)
    else:
        nprogress = norm(ms, (startMs, endMs), limit=True)
        y = lerp((a.HEIGHT, -(th+a.HEIGHT)), nprogress)
        linesToImage(lines, filename, a.WIDTH, a.HEIGHT,
                        color=a.TEXT_COLOR,
                        bgColor=a.BG_COLOR,
                        y=y,
                        tblockXOffset=TEXTBLOCK_X_OFFSET)
    printProgress(frame, totalFrames)

if a.DEBUG:
    sys.exit()

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames))
