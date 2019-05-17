# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import subprocess
import sys

from lib.io_utils import *
from lib.math_utils import *
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
parser.add_argument('-speed', dest="SCROLL_SPEED", default=0.5, type=float, help="(scroll mode only) How much to scroll per frame in px? assumes 30fps; assumes 1920x1080px")
a = parser.parse_args()
aa = vars(a)
aa["SCROLL_SPEED"] = a.SCROLL_SPEED * (a.WIDTH / 1920.0) / (a.FPS / 30.0)
aa["MAX_TEXT_WIDTH"] = roundInt(a.MAX_TEXT_WIDTH * a.WIDTH)
aa["TEXT_INDENT"] = roundInt(a.TEXT_INDENT * a.WIDTH)

# parse properties
tprops = getTextProperties(a)
TEXTBLOCK_X_OFFSET = roundInt(a.WIDTH * a.TEXTBLOCK_X_OFFSET)

# make dirs
makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE])
# remove existing files
removeFiles(a.OUTPUT_FRAME % "*")

# Read text
lines = parseMdFile(a.INPUT_FILE, a)
print("Found %s lines" % len(lines))

lines = addTextMeasurements(lines, tprops, a)
tw, th = getBBoxFromLines(lines, a)
