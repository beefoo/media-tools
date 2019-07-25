# -*- coding: utf-8 -*-

import argparse
import inspect
import math
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
parser.add_argument('-cellmx', dest="CELL_MARGIN_X", default=2, type=int, help="Cell x margin in pixels")
parser.add_argument('-cellmy', dest="CELL_MARGIN_Y", default=4, type=int, help="Cell y margin in pixels")
parser.add_argument('-ppf', dest="PIXELS_PER_FRAME", default=1.0, type=float, help="Number of pixels to move per frame")
parser.add_argument('-textfdur', dest="TEXT_FADE_DUR", default=3000, type=int, help="Duration text should fade in milliseconds")
parser.add_argument('-textfdel', dest="TEXT_FADE_DELAY", default=500, type=int, help="Duration text should delay fade in milliseconds")
parser.add_argument('-clipsmo', dest="CLIPS_MOVE_OFFSET", default=-4000, type=int, help="Offset the clips should start moving in in milliseconds")
parser.add_argument('-clockh', dest="CLOCK_LABEL_HEIGHT", default=0.05, type=float, help="Clock label height as a percent of height")
parser.add_argument('-vthreads', dest="VIDEO_THREADS", default=8, type=int, help="Concurrent threads for reading video files to extract clip pixels")
parser.add_argument('-cliplw', dest="CLIP_OUTLINE_WIDTH", default=4, type=int, help="Line width of clip border when playing")
parser.add_argument('-cliplc', dest="CLIP_OUTLINE_COLOR", default="#AAAAAA", help="Line color of clip border when playing")
parser.add_argument('-cliplmar', dest="CLIP_OUTLINE_MAX_ALPHA_RANGE", default="0.5,1.0", help="Line max alpha range of clip border when playing")

# Audio option
parser.add_argument('-maxtpc', dest="MAX_TRACKS_PER_CELL", default=2, type=int, help="How many audio tracks can play at any given time cell")
parser.add_argument('-padaudio', dest="PAD_AUDIO", default=2000, type=int, help="Pad the beginning and end of audio in milliseconds")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.333,0.667", help="Volume range")

# Text options
parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
parser.add_argument('-cotext', dest="COLLECTION_TEXT_PROPS", default="font=OpenSans-Light.ttf&size=36&letterSpacing=2", help="Text styles for collection labels (font, size, letter-width)")
parser.add_argument('-cltext', dest="CLOCK_TEXT_PROPS", default="font=OpenSans-Bold.ttf&size=24&letterSpacing=2", help="Text styles for clock labels (font, size, letter-width)")
parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")
parser.add_argument('-ccolor', dest="CLOCK_TEXT_COLOR", default="#DDDDDD", help="Color of font")
parser.add_argument('-talign', dest="TEXT_ALIGN", default="center", help="Default text align")
parser.add_argument('-clock', dest="CLOCK_INTERVAL", default=15.0, type=float, help="How often to display clock in minutes")

a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["CLOCK_LABEL_HEIGHT"] = roundInt(a.CLOCK_LABEL_HEIGHT * a.HEIGHT)
aa["CLIP_AREA_HEIGHT"] = a.HEIGHT - a.CLOCK_LABEL_HEIGHT * 2
aa["CLIP_ASPECT_RATIO"] = 1.0 * a.WIDTH / a.CLIP_AREA_HEIGHT
aa["PRECISION"] = 6
aa["BRIGHTNESS_RANGE"] = (0.1, 1.0)
aa["CLIP_OUTLINE_COLOR"] = hex2rgb(a.CLIP_OUTLINE_COLOR)
aa["CLIP_OUTLINE_MAX_ALPHA_RANGE"] = tuple([float(v) for v in a.CLIP_OUTLINE_MAX_ALPHA_RANGE.strip().split(",")])
# aa["MASTER_DB"] = -1.5

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
print("Cell: %s x %s" % (cellW, cellH))
totalW = cellW * cellsPerCollection
totalXDelta = totalW + a.WIDTH
print("%s total pixel movement" % formatNumber(totalXDelta))
totalMoveFrames = roundInt(totalXDelta / a.PIXELS_PER_FRAME)
totalMoveMs = frameToMs(totalMoveFrames, a.FPS)
cellMoveFrames = 1.0 * cellW / a.PIXELS_PER_FRAME
cellMoveMs = frameToMs(cellMoveFrames, a.FPS)
cellMoveMsF = frameToMs(cellMoveFrames, a.FPS, roundResult=False)
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

if not a.PROBE:
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
    collections[i]["locFadeInOutStart"] = collections[i]["locFadeInStart"] + roundInt(oneScreenMs * 0.5)
    collections[i]["nameFadeInOutStart"] = collections[i]["nameFadeInStart"] + roundInt(oneScreenMs * 0.5)
    collections[i]["locFadeOutStart"] = textOutStartMs + (collectionCount-1-i) * 2 * a.TEXT_FADE_DELAY
    collections[i]["nameFadeOutStart"] = collections[i]["locFadeOutStart"] + a.TEXT_FADE_DELAY
    collections[i]["locFadeOutInStart"] = collections[i]["locFadeOutStart"] - roundInt(oneScreenMs * 0.5)
    collections[i]["nameFadeOutInStart"] = collections[i]["nameFadeOutStart"] - roundInt(oneScreenMs * 0.5)
collections = sorted(collections, key=lambda c: c["row"])

# determine relative powers per cell which will change the cell scale and volume over time
minPower = 0.125 # make this number larger to make more even
cellWeights = []
for col in range(cellsPerCollection):
    colPowers = [max(c["cells"][col]["npowerIndex"], minPower) for c in collections]
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
# visualizeGLPower(collections)
# sys.exit()
# collectionPowerToImg(collections, "output/global_lives_power.png", cellsPerCollection)
# sys.exit()

# create samples, clips
samples = []
for c in collections:
    for cell in c["cells"]:
        for s in cell["samples"]:
            sample = s.copy()
            sample["cellDur"] = cell["dur"]
            # if 0 < s["cellStart"] < 60000:
            #     cellStartMs = roundInt(cell["col"] * cellMoveMsF) + moveStartMs
            #     cellEndMs = cellStartMs + oneScreenMs
            #     print("%s:%s %s - %s" % (c["name"], cell["col"], formatSeconds(cellStartMs/1000.0), formatSeconds(cellEndMs/1000.0)))
            samples.append(sample)
samples = addIndices(samples)
clips = samplesToClips(samples)

# Create clock cells
clockCellCount = roundInt(24.0 * 60 / a.CLOCK_INTERVAL)
clockCellW = 1.0 * totalW / clockCellCount
clockCells = []
noon = 12.0 * 60.0
for i in range(clockCellCount):
    minute = i * a.CLOCK_INTERVAL
    clabel = formatClockTime(minute*60)
    if i == 0:
        clabel = "MIDNIGHT"
    elif minute == noon:
        clabel = "NOON"

    chars = list(clabel)
    _, labelH = clockFont.getsize(clabel)
    labelW = 0
    labelChars = []
    for char in chars:
        chw, chh = clockFont.getsize(char)
        labelChars.append((char, chw))
        labelW += chw + clockTextProps["letterSpacing"]
    labelW -= clockTextProps["letterSpacing"]

    clockCells.append({
        "col": i,
        "label": clabel,
        "labelW": labelW,
        "labelH": labelH,
        "labelChars": labelChars
    })

# Create audio sequence
sequenceStart = moveStartMs
offsetMs = oneScreenMs * 0.5 # amount of time it takes for clip to move from right side of screen (when the video starts playing) to center
audioSequence = getGLAudioSequence(collections, cellsPerCollection, sequenceStart, cellMoveMsF, offsetMs, a)
# from lib.audio_mixer import *
# plotAudioSequence(audioSequence)
# visualizeGLAudioSequence(audioSequence, videos)
# sys.exit()

playClips = []
for s in audioSequence:
    playClips.append({
        "start": s["ms"],
        "end": s["ms"] + s["dur"],
        "nvolume": s["nvolume"],
        "row": s["row"],
        "col": s["col"]
    })
playClips = sorted(playClips, key=lambda c: c["start"])
playClipCount = len(playClips)

# for s in audioSequence:
#     if s["ms"] < 2332000 < s["ms"] + s["dur"]:
#         print(s["filename"])
# sys.exit()

def getCurrentWeights(ms):
    global a
    global moveStartMs
    global moveEndMs
    global cellWeights
    global collectionCount
    global totalWidthMoveMs

    wcount = len(cellWeights)
    transitionStartMs = moveStartMs + oneScreenMs * 0.25
    lerpStartMs = moveStartMs + oneScreenMs * 0.5
    lerpEndMs = lerpStartMs + totalWidthMoveMs
    equi = 1.0 / collectionCount
    w0 = [(equi, i*equi) for i in range(collectionCount)]
    w1 = w0[:]
    nprogress = 0

    # lerp in the first entry
    if transitionStartMs <= ms < lerpStartMs:
        w1 = cellWeights[0]
        nprogress = norm(ms, (transitionStartMs, lerpStartMs))
    elif lerpStartMs <= ms < lerpEndMs:
        lnprogress = norm(ms, (lerpStartMs, lerpEndMs))
        findex = lnprogress * wcount
        i0 = floorInt(findex)
        i1 = ceilInt(findex)
        w0 = cellWeights[i0] if i0 < wcount else w0
        w1 = cellWeights[i1] if i1 < wcount else w1
        nprogress = findex - i0

    # lerp the weights
    weights = []
    nprogress = ease(nprogress)
    for i in range(collectionCount):
        nsize = lerp((w0[i][0], w1[i][0]), nprogress)
        ny = lerp((w0[i][1], w1[i][1]), nprogress)
        weights.append((nsize, ny))
    return weights

def getCellPositionAndSize(ms, row, col, myCellW="auto", margin=0):
    global a
    global clipW
    global moveStartMs
    global moveEndMs
    global totalXDelta

    # get row weights at time
    weights = getCurrentWeights(ms)
    nsize, ny = weights[row]

    # get horizontal progress
    nprogress = norm(ms, (moveStartMs, moveEndMs))
    xOffset = -totalXDelta * nprogress

    # determine clip scale since we limit how small the clip can shrink to
    sCellH = nsize * a.CLIP_AREA_HEIGHT
    sCellW = max(cellW, sCellH * a.CLIP_ASPECT_RATIO)

    # calculate size and position
    y = a.CLOCK_LABEL_HEIGHT + ny * a.CLIP_AREA_HEIGHT + a.CELL_MARGIN_Y
    h = sCellH - a.CELL_MARGIN_Y * 2

    # scale the row around center anchor
    anchorX = a.WIDTH * 0.5
    scaleX = 1.0 * sCellW / cellW
    newLeftX = getScaledValue(a.WIDTH + xOffset, scaleX, anchorX)
    newCellW = sCellW if myCellW == "auto" else myCellW * scaleX
    x = newLeftX + newCellW * col + margin
    w = newCellW - margin * 2

    # make brightness relative to max weight and distance from center
    nweight = ease(nsize / max([w[0] for w in weights]), "cubicInOut")
    cx = x + w * 0.5
    distanceFromCenter = min(abs(anchorX - cx), anchorX)
    nDistanceFromCenter = ease(1.0 - 1.0 * distanceFromCenter / anchorX, "cubicInOut")
    brightness = nweight * nDistanceFromCenter

    return (x, y, w, h, brightness)

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
    brightness = 1.0

    # determine position and size here
    if moveStartMs <= ms <= moveEndMs:
        x, y, w, h, brightness = getCellPositionAndSize(ms, clip.props["row"], clip.props["col"], margin=a.CELL_MARGIN_X)

        # determine clip time
        cellStartMs = roundInt(clip.props["col"] * cellMoveMsF) + moveStartMs
        timeSinceStartMs = ms - cellStartMs
        # check to see if current clip is playing
        cellMs = 1.0 * timeSinceStartMs % clip.props["cellDur"] # amount of time in cell
        if clip.props["cellStart"] <= cellMs < clip.props["cellStart"] + clip.props["dur"]:
            timeSinceStartMs -= clip.props["cellStart"]
            tn = 1.0 * (timeSinceStartMs % clip.props["dur"]) / clip.props["dur"]
            # tn = timeSinceStartMs % clip.props["dur"]
        else:
            x = y = w = h = tn = 0

    brightness = lerp(a.BRIGHTNESS_RANGE, brightness)

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
        roundInt(props["alpha"] * precisionMultiplier),
        roundInt(tn * precisionMultiplier),
        roundInt(props["zindex"]),
        roundInt(props["rotation"] * precisionMultiplier),
        roundInt(props["blur"] * precisionMultiplier),
        roundInt(brightness * precisionMultiplier)
    ], dtype=np.int32)

def getTextAlpha(ms, c, prefix, fadeDur):
    alpha = 0
    if c["%sFadeInStart" % prefix] <= ms < c["%sFadeInOutStart" % prefix]:
        alpha = norm(ms, (c["%sFadeInStart" % prefix], c["%sFadeInStart" % prefix]+fadeDur), limit=True)
    elif c["%sFadeInOutStart" % prefix] <= ms < (c["%sFadeInOutStart" % prefix]+fadeDur):
        alpha = 1.0 - norm(ms, (c["%sFadeInOutStart" % prefix], c["%sFadeInOutStart" % prefix]+fadeDur), limit=True)
    elif c["%sFadeOutInStart" % prefix] <= ms < c["%sFadeOutStart" % prefix]:
        alpha = norm(ms, (c["%sFadeOutInStart" % prefix], c["%sFadeOutInStart" % prefix]+fadeDur), limit=True)
    elif c["%sFadeOutStart" % prefix] <= ms < (c["%sFadeOutStart" % prefix]+fadeDur):
        alpha = 1.0 - norm(ms, (c["%sFadeOutStart" % prefix], c["%sFadeOutStart" % prefix]+fadeDur), limit=True)
    return alpha

def drawClockTime(draw, cc, x, y, pad=2):
    global a
    global clockFont
    global clockTextProps

    if -(cc["labelW"] + pad) <= x <= a.WIDTH + cc["labelW"] + pad:
        lsw = clockTextProps["letterSpacing"]
        tx = x - cc["labelW"] * 0.5
        clockTextOffsetY = roundInt((a.CLOCK_LABEL_HEIGHT - cc["labelH"]) * 0.33)
        ty = y + clockTextOffsetY
        for char, charW in cc["labelChars"]:
            draw.text((tx, ty), char, font=clockFont, fill=a.CLOCK_TEXT_COLOR)
            tx += charW + lsw

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
    global cellH
    global textMargin

    if im is None:
        im = Image.new(mode="RGB", size=(a.WIDTH, a.HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)
    # draw.rectangle([0, 0, a.WIDTH, a.CLOCK_LABEL_HEIGHT], fill="#0000FF")
    # draw.rectangle([0, a.HEIGHT-a.CLOCK_LABEL_HEIGHT, a.WIDTH, a.HEIGHT], fill="#00FF00")

    weights = getCurrentWeights(ms)

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
            alpha = getTextAlpha(ms, c, "loc", a.TEXT_FADE_DUR)
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
            alpha = getTextAlpha(ms, c, "name", a.TEXT_FADE_DUR)
            if alpha > 0.0:
                alpha = ease(alpha)
                tx = cx + textMargin
                for char in list(c["name"]):
                    draw.text((tx, ty), char, font=collectionFont, fill=tuple([roundInt(v*alpha) for v in textColor]))
                    chw, chh = collectionFont.getsize(char)
                    tx += chw + lsw

    # render clock
    global clockCells
    global clockCellW

    yTop = 0
    yBottom = a.HEIGHT - a.CLOCK_LABEL_HEIGHT
    for cc in clockCells:
        xTop, _y, _w, _h, _alpha = getCellPositionAndSize(ms, row=0, col=cc["col"], myCellW=clockCellW)
        xBottom, _y, _w, _h, _alpha = getCellPositionAndSize(ms, row=-1, col=cc["col"], myCellW=clockCellW)
        drawClockTime(draw, cc, xTop, yTop)
        drawClockTime(draw, cc, xBottom, yBottom)

    return im

def postProcessGL(im, ms, globalArgs={}):
    global a
    global playClips
    global playClipCount

    rr = 2 # resize resolution
    width, height = im.size
    stagingImg = Image.new(mode="RGBA", size=(width*rr, height*rr), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(stagingImg)
    drawn = False
    deleted = 0
    for i, clip in enumerate(playClips):
        if clip["start"] <= ms < clip["end"]:
            x, y, w, h, brightness = getCellPositionAndSize(ms, clip["row"], clip["col"], margin=a.CELL_MARGIN_X)
            x, y, w, h = (x*rr, y*rr, w*rr, h*rr)
            nprogress = norm(ms, (clip["start"], clip["end"]))
            alpha = easeSinInOutBell(nprogress)
            maxAlpha = lerp(a.CLIP_OUTLINE_MAX_ALPHA_RANGE, clip["nvolume"])
            alpha *= maxAlpha
            color = tuple(a.CLIP_OUTLINE_COLOR + [roundInt(alpha*255.0)])
            draw.rectangle([x, y, x+w, y+h], fill=None, outline=color, width=a.CLIP_OUTLINE_WIDTH)
            drawn = True

        # we've played all the clips we could; break the loop
        elif ms < clip["start"]:
            break

        # we've played this clip already; delete it
        else:
            deleted += 1

    if deleted > 0:
        del playClips[:deleted]
        playClipCount -= deleted

    if drawn:
        im = im.convert("RGBA")
        stagingImg = stagingImg.resize((width, height), resample=Image.LANCZOS)
        im = Image.alpha_composite(im, stagingImg)
        im = im.convert("RGB")

    return im

# durationMs = textInEndMs
# durationMs = textInEndVisibleMs
# durationMs = textInEndVisibleMs + oneScreenMs * 2
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

# testIm = preProcessGL(None, roundInt(textInEndVisibleMs + oneScreenMs*0.33))
# testIm.save("output/global_lives_text_test.png")
# sys.exit()

processComposition(a, clips, durationMs, stepTime=stepTime, startTime=startTime,
    audioSequence=audioSequence,
    customClipToArrFunction=clipToNpArrGL,
    preProcessingFunction=preProcessGL,
    postProcessingFunction=postProcessGL,
    renderOnTheFly=True
)
