# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import subprocess
import sys

from lib.audio_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
# add text properties
addTextArguments(parser)
parser.add_argument('-in', dest="INPUT_FILE", default="titles/main.md", help="Input smarkdown file")
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-fps', dest="FPS", default=24, type=int, help="Output video frames per second")
parser.add_argument('-duration', dest="DURATION_MS", default=4000, type=int, help="Duration of text in ms, excludes fade and padding")
parser.add_argument('-fadein', dest="FADE_IN_MS", default=500, type=int, help="Fade in of text in ms")
parser.add_argument('-fadeout', dest="FADE_OUT_MS", default=500, type=int, help="Fade out of text in ms")
parser.add_argument('-ease', dest="FADE_EASE", default="sin", help="Easing function for fading: linear, sin, quadInOut, cubicInOut")
parser.add_argument('-pad0', dest="PAD_START", default=1000, type=int, help="Padding at start in ms")
parser.add_argument('-pad1', dest="PAD_END", default=1000, type=int, help="Padding at end in ms")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/title_main.mp4", help="Output media file")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
a = parser.parse_args()
aa = vars(a)
aa["REAL_WIDTH"] = a.WIDTH
aa["REAL_HEIGHT"] = a.HEIGHT
aa["WIDTH"] = roundInt(a.WIDTH * a.RESIZE_RESOLUTION)
aa["HEIGHT"] = roundInt(a.HEIGHT * a.RESIZE_RESOLUTION)

if len(a.OUTPUT_FRAME) < 1:
    aa["OUTPUT_FRAME"] = "tmp/%s_frames/frame.%%s.png" % getBasename(a.OUTPUT_FILE)

# parse properties
tprops = getTextProperties(a)
TEXTBLOCK_Y_OFFSET = roundInt(a.HEIGHT * a.TEXTBLOCK_Y_OFFSET)
TEXTBLOCK_X_OFFSET = roundInt(a.WIDTH * a.TEXTBLOCK_X_OFFSET)

# make dirs
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# remove existing files
if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

# Read text
lines = parseMdFile(a.INPUT_FILE, a)
lines = addTextMeasurements(lines, tprops)

if a.DEBUG:
    linesToImage(lines, a.OUTPUT_FRAME % "test", a.WIDTH, a.HEIGHT,
                    color=a.TEXT_COLOR,
                    bgColor=a.BG_COLOR,
                    tblockYOffset=TEXTBLOCK_Y_OFFSET,
                    tblockXOffset=TEXTBLOCK_X_OFFSET,
                    resizeResolution=a.RESIZE_RESOLUTION)
    sys.exit()

# Determine length
totalMs = a.PAD_START + a.FADE_IN_MS + a.DURATION_MS + a.FADE_OUT_MS + a.PAD_END
totalFrames = msToFrame(totalMs, a.FPS)
# ceil to the nearest second
totalFrames = int(ceilToNearest(totalFrames, a.FPS))
print("Total frames: %s" % totalFrames)
totalMs = frameToMs(totalFrames, a.FPS)
print("Total time: %s" % formatSeconds(totalMs/1000.0))

fadeInStart = a.PAD_START
fadeInEnd = a.PAD_START + a.FADE_IN_MS
fadeOutStart = a.PAD_START + a.FADE_IN_MS + a.DURATION_MS
fadeOutEnd = a.PAD_START + a.FADE_IN_MS + a.DURATION_MS + a.FADE_OUT_MS

# get frame sequence
print("Making video frame sequence...")
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    # padding: just output blank image
    if ms <= fadeInStart or ms >= fadeOutEnd:
        saveBlankFrame(filename, a.REAL_WIDTH, a.REAL_HEIGHT, bgColor=a.BG_COLOR, overwrite=a.OVERWRITE)
    # otherwise, draw text
    else:
        textColor = a.TEXT_COLOR
        lerpColor = 1.0

        # fading in or out
        if fadeInStart <= ms <= fadeInEnd:
            lerpColor = norm(ms, (fadeInStart, fadeInEnd), limit=True)
        elif fadeOutStart <= ms <= fadeOutEnd:
            lerpColor = 1.0 - norm(ms, (fadeOutStart, fadeOutEnd), limit=True)

        if lerpColor < 1.0:
            lerpColor = ease(lerpColor, a.FADE_EASE)
            c0 = hex2rgb(a.BG_COLOR)
            c1 = hex2rgb(a.TEXT_COLOR)
            textColor = []
            for i in range(3):
                textColor.append(roundInt(lerp((c0[i], c1[i]), lerpColor)))
            textColor = tuple(textColor)

        linesToImage(lines, filename, a.WIDTH, a.HEIGHT,
                        color=textColor,
                        bgColor=a.BG_COLOR,
                        tblockYOffset=TEXTBLOCK_Y_OFFSET,
                        tblockXOffset=TEXTBLOCK_X_OFFSET,
                        resizeResolution=a.RESIZE_RESOLUTION,
                        overwrite=a.OVERWRITE)
    printProgress(frame, totalFrames)

# Create a blank audio track
audioFile = a.OUTPUT_FILE.replace(".mp4", ".mp3")
makeBlankAudio(totalMs, audioFile)

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile)
