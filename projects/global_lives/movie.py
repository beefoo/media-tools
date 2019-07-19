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
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *
from gllib import *

parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-co', dest="COLLECTION_FILE", default="projects/global_lives/data/ia_globallives_collections.csv", help="Input collection csv file")
parser.add_argument('-celldat', dest="CELL_FILE", default="projects/global_lives/data/ia_globallives_cells.csv", help="Input/output cell csv file")
parser.add_argument('-celldur', dest="CELL_DURATION", default=3.0, type=float, help="Cell duration in minutes")
parser.add_argument('-cellmx', dest="CELL_MARGIN_X", default=1, type=int, help="Cell x margin in pixels")
parser.add_argument('-cellmy', dest="CELL_MARGIN_Y", default=2, type=int, help="Cell y margin in pixels")
parser.add_argument('-ppf', dest="PIXELS_PER_FRAME", default=1.0, type=float, help="Number of pixels to move per frame")
parser.add_argument('-textfdur', dest="TEXT_FADE_DUR", default=3000, type=int, help="Duration text should fade in milliseconds")
parser.add_argument('-textfdel', dest="TEXT_FADE_DELAY", default=300, type=int, help="Duration text should delay fade in milliseconds")
parser.add_argument('-clipsmo', dest="CLIPS_MOVE_OFFSET", default=-4000, type=int, help="Offset the clips should start moving in in milliseconds")
parser.add_argument('-clockh', dest="CLOCK_LABEL_HEIGHT", default=0.05, type=float, help="Clock label height as a percent of height")

# Text options
parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
parser.add_argument('-cotext', dest="COLLECTION_TEXT_PROPS", default="font=OpenSans-Light.ttf&size=36&letterSpacing=2", help="Text styles for collection labels (font, size, letter-width)")
parser.add_argument('-cltext', dest="CLOCK_TEXT_PROPS", default="font=OpenSans-Bold.ttf&size=24&letterSpacing=2", help="Text styles for clock labels (font, size, letter-width)")
parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")
parser.add_argument('-talign', dest="TEXT_ALIGN", default="center", help="Default text align")
parser.add_argument('-clock', dest="CLOCK_INTERVAL", default=15.0, type=float, help="How often to display clock in minutes")

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
cellMoveFrames = 1.0 * cellW / a.PIXELS_PER_FRAME
cellMoveMs = frameToMs(cellMoveFrames, a.FPS)
print("Total movement duration: %s" % formatSeconds(totalMoveMs/1000.0))

# calculate text durations
textDurationMs = a.TEXT_FADE_DELAY * collectionCount * 2 + max(a.TEXT_FADE_DUR - a.TEXT_FADE_DELAY, 0)
moveStartMs = a.PAD_START + textDurationMs + a.CLIPS_MOVE_OFFSET
moveEndMs = moveStartMs + totalMoveMs
durationMs = moveEndMs + textDurationMs
print("Total duration: %s" % formatSeconds(durationMs/1000.0))
oneScreenMs = frameToMs(a.WIDTH / a.PIXELS_PER_FRAME, a.FPS)
print("One screen duration: %s" % formatSeconds(oneScreenMs/1000.0))
oneScreenDaySeconds = (1.0 * a.WIDTH / totalW) * (24 * 3600)
oneScreenDayMinutes = oneScreenDaySeconds / 60.0
print("One screen footage duration: %s" % formatSeconds(oneScreenDaySeconds))
print("One cell duration: %s" % formatSeconds(cellMoveMs/1000.0))
totalWidthMoveMs = totalMoveMs - oneScreenMs

if a.PROBE:
    sys.exit()

makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CELL_FILE])

# Add audio analysis to cells
collections = addCellDataToCollections(collections, cellsPerCollection, a.CELL_FILE)

# Calculations for text timing
textInStartMs = a.PAD_START
textInEndMs = textInStartMs + textDurationMs
textInEndVisibleMs = textInEndMs + oneScreenMs
textOutStartMs = moveStartMs + totalMoveMs
textOutStartVisibleMs = textOutStartMs - oneScreenMs
textOutEndMs = textOutStartMs + textDurationMs

# init text
collectionTextProps = parseQueryString(a.COLLECTION_TEXT_PROPS, doParseNumbers=True)
clockTextProps = parseQueryString(a.CLOCK_TEXT_PROPS, doParseNumbers=True)
collectionFont = ImageFont.truetype(font=a.FONT_DIR + collectionTextProps["font"], size=collectionTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
clockFont = ImageFont.truetype(font=a.FONT_DIR + clockTextProps["font"], size=clockTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
_, ah = collectionFont.getsize("A")
textOffsetY = roundInt((cellH - ah) * 0.5)
textMargin, _ = collectionFont.getsize("+")

# preprocess some collection logic
for i, c in enumerate(collections):
    collections[i]["locLabel"] = "%s, %s" % (c["city"], c["country"])
    collections[i]["titleSort"] = (abs((collectionCount-1) * 0.5 - i), i)
collections = sorted(collections, key=lambda c: c["titleSort"])
for i, c in enumerate(collections):
    collections[i]["locFadeInStart"] = textInStartMs + i * 2 * a.TEXT_FADE_DELAY
    collections[i]["nameFadeInStart"] = collections[i]["locFadeInStart"] + a.TEXT_FADE_DELAY
    collections[i]["locFadeOutStart"] = textOutStartMs + (collectionCount-1-i) * 2 * a.TEXT_FADE_DELAY
    collections[i]["nameFadeOutStart"] = collections[i]["locFadeOutStart"] + a.TEXT_FADE_DELAY
collections = sorted(collections, key=lambda c: c["row"])

# determine relative powers per cell which will change the cell scale and volume over time
minPower = 1.0 / collectionCount
cellWeights = []
for col in range(cellsPerCollection):
    colPowers = [max(c["cells"][col]["npower"], minPower) for c in collections]
    colPowerSum = sum(colPowers)
    ny = 0
    cellWeight = []
    for j, c in enumerate(collections):
        rnpower = 1.0 * colPowers[j] / colPowerSum
        collections[j]["cells"][col]["nsize"] = rnpower
        collections[j]["cells"][col]["ny"] = ny
        cellWeight.append((rnpower, ny))
        ny += rnpower
    cellWeights.append(cellWeight)
# collectionPowerToImg(collections, "output/global_lives_power.png", cellsPerCollection)
# sys.exit()

# create samples, clips
samples = []
for c in collections:
    for cell in c["cells"]:
        for s in cell["samples"]:
            sample = s.copy()
            sample["cellDur"] = cell["dur"]
            samples.append(sample)
samples = addIndices(samples)
clips = samplesToClips(samples)

def getCurrentWeights(ms):
    global a
    global moveStartMs
    global moveEndMs
    global cellWeights
    global collectionCount
    global totalWidthMoveMs

    wcount = len(cellWeights)
    lerpStartMs = moveStartMs + oneScreenMs * 0.5
    lerpEndMs = lerpStartMs + totalWidthMoveMs
    equi = 1.0 / collectionCount
    w0 = [(equi, i*equi) for i in range(collectionCount)]
    w1 = w0[:]

    # lerp in the first entry
    if moveStartMs <= ms < lerpStartMs:
        w1 = cellWeights[0]
        nprogress = norm(ms, (moveStartMs, lerpStartMs))
    elif lerpStartMs <= ms < lerpEndMs:
        lnprogress = norm(ms, (lerpStartMs, lerpEndMs))
        findex = lnprogress * wcount
        i0 = floorInt(findex)
        i1 = ceilInt(findex)
        w0 = cellWeights[i0] if i0 < wcount else w0
        w1 = cellWeights[i1] if i1 < wcount else w1
        nprogress = findex - i0
    # lerp out last entry
    elif lerpEndMs <= ms < moveEndMs:
        w0 = cellWeights[-1]
        nprogress = norm(ms, (lerpEndMs, moveEndMs))

    # lerp the weights
    weights = []
    nprogress = ease(nprogress)
    for i in range(collectionCount):
        nsize = lerp((w0[i][0], w1[i][0]), nprogress)
        ny = lerp((w0[i][1], w1[i][1]), nprogress)
        weights.append((nsize, ny))
    return weights

# custom clip to numpy array function to override default tweening logic
def clipToNpArrGL(clip, ms, containerW, containerH, precision, parent, globalArgs={}):
    global a
    global moveStartMs
    global moveEndMs
    global totalMoveMs
    global cellsPerCollection
    global totalW
    global totalXDelta
    global cellH
    global cellW
    global cellMoveMs

    x = y = w = h = tn = 0
    alpha = 1.0

    # determine position and size here
    if moveStartMs <= ms <= moveEndMs:
        nprogress = norm(ms, (moveStartMs, moveEndMs))
        xOffset = -totalXDelta * nprogress
        y = a.CLOCK_LABEL_HEIGHT + clip.props["row"] * cellH + a.CELL_MARGIN_Y
        x = a.WIDTH + cellW * clip.props["col"] + a.CELL_MARGIN_X + xOffset
        w = cellW - a.CELL_MARGIN_X * 2
        h = cellH - a.CELL_MARGIN_Y * 2
        cellStartMs = clip.props["col"] * cellMoveMs + moveStartMs
        timeSinceStartMs = ms - cellStartMs
        # check to see if current clip is playing
        cellMs = timeSinceStartMs % clip.props["cellDur"] # amount of time in cell
        if clip.props["cellStart"] <= cellMs < clip.props["cellStart"] + clip.props["dur"]:
            timeSinceStartMs -= clip.props["cellStart"]
            tn = 1.0 * (timeSinceStartMs % clip.props["dur"]) / clip.props["dur"]
        else:
            x = y = w = h = tn = 0

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

def preProcessGL(im, ms, globalArgs={}):
    global a
    global textInStartMs
    global textInEndVisibleMs
    global textOutStartVisibleMs
    global textOutEndMs
    global collectionTextProps
    global collectionFont
    global collections
    global cellW
    global textMargin

    if im is None:
        im = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)
    # draw.rectangle([0, 0, a.WIDTH, a.CLOCK_LABEL_HEIGHT], fill="#0000FF")
    # draw.rectangle([0, a.HEIGHT-a.CLOCK_LABEL_HEIGHT, a.WIDTH, a.HEIGHT], fill="#00FF00")

    # render collection text in the beginning and end
    isTextIn = textInStartMs <= ms <= textInEndVisibleMs
    isTextOut = textOutStartVisibleMs <= ms <= textOutEndMs
    if isTextIn or isTextOut:
        textColor = hex2rgb(a.TEXT_COLOR)
        cx = a.WIDTH * 0.5
        cCount = len(collections)
        y0 = a.CLOCK_LABEL_HEIGHT
        lsw = collectionTextProps["letterSpacing"]
        for i, c in enumerate(collections):
            # if i % 2 > 0:
            #     draw.rectangle([0, y0 + i * cellH, a.WIDTH, y0 + (i+1) * cellH], fill="#0000FF")
            alpha = norm(ms, (c["locFadeInStart"], c["locFadeInStart"]+a.TEXT_FADE_DUR), limit=True) if isTextIn else 1.0-norm(ms, (c["locFadeOutStart"], c["locFadeOutStart"]+a.TEXT_FADE_DUR), limit=True)
            labelW, labelH = collectionFont.getsize(c["locLabel"] + c["name"])
            textOffsetY = roundInt((cellH - labelH) * 0.33)
            ty = y0 + i * cellH + textOffsetY
            if alpha > 0.0:
                alpha = ease(alpha)
                tx = cx - textMargin
                for char in reversed(list(c["locLabel"])):
                    chw, chh = collectionFont.getsize(char)
                    tx -= chw
                    draw.text((tx, ty), char, font=collectionFont, fill=tuple([roundInt(v*alpha) for v in textColor]))
                    tx -= lsw
            alpha = norm(ms, (c["nameFadeInStart"], c["nameFadeInStart"]+a.TEXT_FADE_DUR), limit=True) if isTextIn else 1.0-norm(ms, (c["nameFadeOutStart"], c["nameFadeOutStart"]+a.TEXT_FADE_DUR), limit=True)
            if alpha > 0.0:
                alpha = ease(alpha)
                tx = cx + textMargin
                for char in list(c["name"]):
                    draw.text((tx, ty), char, font=collectionFont, fill=tuple([roundInt(v*alpha) for v in textColor]))
                    chw, chh = collectionFont.getsize(char)
                    tx += chw + lsw

    # render clock
    global moveStartMs
    global moveEndMs
    global totalMoveMs
    global oneScreenDayMinutes
    global clockFont
    global clockTextProps

    nprogress = norm(ms, (moveStartMs, moveEndMs))
    elapsedDayMinutes = nprogress * 24 * 60
    tRight = elapsedDayMinutes
    tLeft = elapsedDayMinutes - oneScreenDayMinutes
    pad = 2
    tStart = roundInt(tLeft) - pad
    tSteps = roundInt(tRight - tLeft) + pad*2
    lsw = clockTextProps["letterSpacing"]
    ty = 0
    ty1 = a.HEIGHT - a.CLOCK_LABEL_HEIGHT
    for i in range(tSteps):
        minute = 1.0 * (i + tStart)
        day = 24.0 * 60.0
        if minute % a.CLOCK_INTERVAL < 1 and 0 <= minute <= day:
            label = formatClockTime(minute*60)
            noon = 12.0 * 60.0
            if minute == 0.0 or minute == day:
                label = "MIDNIGHT"
            elif minute == noon:
                label = "NOON"
            cx = norm(minute, (tLeft, tRight)) * a.WIDTH
            chars = list(label)
            labelW, labelH = clockFont.getsize(label)
            labelW += lsw * (len(chars)-1)
            tx = cx - labelW * 0.5
            clockTextOffsetY = roundInt((a.CLOCK_LABEL_HEIGHT - labelH) * 0.33)
            for char in chars:
                draw.text((tx, ty+clockTextOffsetY), char, font=clockFont, fill=a.TEXT_COLOR)
                draw.text((tx, ty1+clockTextOffsetY), char, font=clockFont, fill=a.TEXT_COLOR)
                chw, chh = clockFont.getsize(char)
                tx += chw + lsw

    return im

durationMs = textInEndVisibleMs
# totalFrames = msToFrame(durationMs, a.FPS)
# outframefile = "tmp/global_lives_text_test_frames/frame.%s.png"
# makeDirectories(outframefile)
# removeFiles(outframefile % "*")
# for f in range(totalFrames):
#     frame = f + 1
#     ms = frameToMs(frame, a.FPS)
#     testIm = preProcessGL(None, ms)
#     testIm.save(outframefile % zeroPad(frame, totalFrames))
#     printProgress(frame, totalFrames)
# compileFrames(outframefile, a.FPS, "output/global_lives_text_test.mp4", getZeroPadding(totalFrames))

# testIm = preProcessGL(None, roundInt(textInEndVisibleMs - oneScreenMs*0.5))
# testIm.save("output/global_lives_text_test.png")

processComposition(a, clips, durationMs, stepTime=stepTime, startTime=startTime, customClipToArrFunction=clipToNpArrGL, preProcessingFunction=preProcessGL, renderOnTheFly=True)
