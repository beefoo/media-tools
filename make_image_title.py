# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image
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
parser.add_argument('-in', dest="INPUT_FILE", default="projects/global_lives/titles/main.png", help="Input image file")
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
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/global_lives_title_main.mp4", help="Output media file")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Debug mode?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
a = parser.parse_args()
aa = vars(a)

if len(a.OUTPUT_FRAME) < 1:
    aa["OUTPUT_FRAME"] = "tmp/%s_frames/frame.%%s.png" % getBasename(a.OUTPUT_FILE)

# make dirs
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])

# remove existing files
if a.OVERWRITE:
    removeFiles(a.OUTPUT_FRAME % "*")

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

blankImage = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=a.BG_COLOR)
im = Image.open(a.INPUT_FILE)
im = im.resize((a.WIDTH, a.HEIGHT), resample=Image.LANCZOS)

# get frame sequence
print("Making video frame sequence...")
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, a.FPS)
    filename = a.OUTPUT_FRAME % zeroPad(frame, totalFrames)
    # padding: just output blank image
    if ms <= fadeInStart or ms >= fadeOutEnd:
        saveBlankFrame(filename, a.WIDTH, a.HEIGHT, bgColor=a.BG_COLOR, overwrite=a.OVERWRITE, verbose=False)
    # otherwise, draw image
    else:
        nfade = 1.0
        # fading in or out
        if fadeInStart <= ms <= fadeInEnd:
            nfade = norm(ms, (fadeInStart, fadeInEnd), limit=True)
        elif fadeOutStart <= ms <= fadeOutEnd:
            nfade = 1.0 - norm(ms, (fadeOutStart, fadeOutEnd), limit=True)
        if 0.0 < nfade < 1.0:
            nfade = ease(nfade, a.FADE_EASE)
        if nfade >= 1.0:
            im.save(filename)
        else:
            fadedImg = Image.blend(blankImage, im, nfade)
            fadedImg.save(filename)
    printProgress(frame, totalFrames)

# Create a blank audio track
audioFile = a.OUTPUT_FILE.replace(".mp4", ".mp3")
makeBlankAudio(totalMs, audioFile)

compileFrames(a.OUTPUT_FRAME, a.FPS, a.OUTPUT_FILE, getZeroPadding(totalFrames), audioFile=audioFile)
