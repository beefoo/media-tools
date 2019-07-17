# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.composition_utils import *
from lib.math_utils import *
from lib.io_utils import *
from lib.text_utils import *
from lib.video_utils import *
from gllib import *

parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-co', dest="COLLECTION_FILE", default="projects/global_lives/data/ia_globallives_collections.csv", help="Input collection csv file")
parser.add_argument('-celld', dest="CELL_DURATION", default=3.0, type=float, help="Cell duration in minutes")
parser.add_argument('-ppf', dest="PIXELS_PER_FRAME", default=1.0, type=float, help="Number of pixels to move per frame")
parser.add_argument('-textfdur', dest="TEXT_FADE_DUR", default=1000, type=int, help="Duration text should fade in milliseconds")
parser.add_argument('-textfdel', dest="TEXT_FADE_DELAY", default=500, type=int, help="Duration text should delay fade in milliseconds")
parser.add_argument('-clipsmo', dest="CLIPS_MOVE_OFFSET", default=-4000, type=int, help="Offset the clips should start moving in in milliseconds")
parser.add_argument('-clockh', dest="CLOCK_LABEL_HEIGHT", default=0.05, type=float, help="Clock label height as a percent of height")

# Text options
parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
parser.add_argument('-cotext', dest="COLLECTION_TEXT_PROPS", default="font=OpenSans-Light.ttf&size=36&letterSpacing=2", help="Text styles for collection labels (font, size, letter-width)")
parser.add_argument('-cltext', dest="CLOCK_TEXT_PROPS", default="font=OpenSans-Regular.ttf&size=60&letterSpacing=2", help="Text styles for clock labels (font, size, letter-width)")
parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")
parser.add_argument('-talign', dest="TEXT_ALIGN", default="center", help="Default text align")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["CLOCK_LABEL_HEIGHT"] = roundInt(a.CLOCK_LABEL_HEIGHT * a.HEIGHT)
aa["CLIP_AREA_HEIGHT"] = a.HEIGHT - a.CLOCK_LABEL_HEIGHT * 2
aa["CLIP_ASPECT_RATIO"] = 1.0 * a.WIDTH / a.CLIP_AREA_HEIGHT

startTime = logTime()
stepTime = startTime

# Read and initialize data
vFieldNames, videos = readCsv(a.INPUT_FILE)
cFieldNames, collections = readCsv(a.COLLECTION_FILE)
collections = [c for c in collections if c["active"] > 0]
collections = sorted(collections, key=lambda c: -c["lat"])
collectionCount = len(collections)
print("%s collections" % collectionCount)
videos = prependAll(videos, ("filename", a.MEDIA_DIRECTORY))
collections = addIndices(collections, "row")

# break videos up into cells per collection
cellsPerCollection = roundInt(24.0 * 60.0 / a.CELL_DURATION)
print("Cells per collection: %s" % cellsPerCollection)
collections = addCellsToCollections(collections, videos, cellsPerCollection)
# collectionToImg(collections, "output/global_lives.png", cellsPerCollection)

# calculate cell size and composition size and duration
cellH = int(1.0 * a.CLIP_AREA_HEIGHT / collectionCount)
cellW = roundInt(cellH * a.CLIP_ASPECT_RATIO)
totalW = cellW * cellsPerCollection
totalXDelta = totalW + a.WIDTH
print("%s total pixel movement" % formatNumber(totalXDelta))
totalMoveFrames = roundInt(totalXDelta / a.PIXELS_PER_FRAME)
totalMoveMs = frameToMs(totalMoveFrames, a.FPS)
print("Total movement duration: %s" % formatSeconds(totalMoveMs/1000.0))

# calculate text durations
textDurationMs = a.TEXT_FADE_DELAY * collectionCount * 2 + max(a.TEXT_FADE_DUR - a.TEXT_FADE_DELAY, 0)
moveStartMs = textDurationMs + a.CLIPS_MOVE_OFFSET
durationMs = a.PAD_START + moveStartMs + totalMoveMs + textDurationMs
print("Total duration: %s" % formatSeconds(durationMs/1000.0))
oneScreenMs = frameToMs(a.WIDTH / a.PIXELS_PER_FRAME, a.FPS)
print("One screen duration: %s" % formatSeconds(oneScreenMs/1000.0))
textInStartMs = a.PAD_START
textInEndMs = textInStartMs + moveStartMs + oneScreenMs
textOutStartMs = moveStartMs + totalMoveMs - oneScreenMs
textOutEndMs = textOutStartMs + textDurationMs

# init text
collectionTextProps = parseQueryString(a.COLLECTION_TEXT_PROPS, doParseNumbers=True)
clockTextProps = parseQueryString(a.CLOCK_TEXT_PROPS, doParseNumbers=True)
collectionFont = ImageFont.truetype(font=a.FONT_DIR + collectionTextProps["font"], size=collectionTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
clockFont = ImageFont.truetype(font=a.FONT_DIR + clockTextProps["font"], size=clockTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
aw, ah = collectionFont.getsize("A")
textOffsetY = roundInt((cellH - ah) * 0.5)
textMargin, _ = collectionFont.getsize("+")

for i, c in enumerate(collections):
    collections[i]["locLabel"] = "%s, %s" % (c["city"], c["country"])
# create samples
# add index
# create clips

# custom clip to numpy array function to override default tweening logic
def clipToNpArrGL(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    x = y = w = h = tn = alpha = 0

    # determine position and size here

    customProps = {
        "pos": [x, y],
        "size": [w, h]
    }

    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(alpha * precisionMultiplier),
        roundInt(tn * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(props["brightness"] * precisionMultiplier)
    ], dtype=np.int32)

def preProcessGL(im, ms):
    global a
    global textInStartMs
    global textInEndMs
    global textOutStartMs
    global textOutEndMs
    global collectionTextProps
    global collectionFont
    global collections
    global cellW
    global textOffsetY
    global textMargin

    if im is None:
        im = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)
    textColor = hex2rgb(a.TEXT_COLOR)

    isTextIn = textInStartMs <= ms <= textOutEndMs
    isTextOut = textOutStartMs <= ms <= textOutEndMs
    isTextIn = True

    if isTextIn or isTextOut:
        cx = a.WIDTH * 0.5
        cCount = len(collections)
        y0 = a.CLOCK_LABEL_HEIGHT
        lsw = collectionTextProps["letterSpacing"]
        for i, c in enumerate(collections):
            alpha = 1.0
            tx = cx - textMargin
            ty = y0 + i * cellH + textOffsetY
            for char in reversed(list(c["locLabel"])):
                chw, chh = collectionFont.getsize(char)
                tx -= chw
                draw.text((tx, ty), char, font=collectionFont, fill=tuple([roundInt(v*alpha) for v in textColor]))
                tx -= lsw
            tx = cx + textMargin
            alpha = 1.0
            for char in list(c["name"]):
                draw.text((tx, ty), char, font=collectionFont, fill=tuple([roundInt(v*alpha) for v in textColor]))
                chw, chh = collectionFont.getsize(char)
                tx += chw + lsw

    return im


# testIm = preProcessGL(None, 0)
# testIm.save("output/global_lives_text_test.png")

# processComposition(a, clips, durationMs, stepTime=stepTime, startTime=startTime, customClipToArrFunction=clipToNpArrGL, preProcessingFunction=preProcessGL, renderOnTheFly=True)
