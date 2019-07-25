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

from lib.clip import *
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

# Layout options
parser.add_argument('-clipw', dest="CLIP_WIDTH", default=0.333, type=float, help="Clip width as a percentage of width")
parser.add_argument('-targetl', dest="TARGET_LINES", default=10, type=int, help="Target lines per credit")
parser.add_argument('-creditw', dest="CREDIT_WIDTH", default=0.333, type=float, help="Credit width as a percentage of width")

# Timing options
parser.add_argument('-creditdur', dest="CREDIT_DURATION", default=8000, type=int, help="Credit duration in milliseconds")
parser.add_argument('-fadedur', dest="FADE_DURATION", default=1000, type=int, help="Fade duration in milliseconds")
parser.add_argument('-paddur', dest="PAD_DURATION", default=0, type=int, help="Time between credits")

# Text options
parser.add_argument('-fdir', dest="FONT_DIR", default="media/fonts/Open_Sans/", help="Directory of font files")
parser.add_argument('-ttext', dest="TITLE_TEXT_PROPS", default="font=OpenSans-Regular.ttf&size=36&lineHeight=1&letterSpacing=2&margin=1.0", help="Text styles for collection labels (font, size, line-height, letter-width)")
parser.add_argument('-titext', dest="TITLE_ITALIC_TEXT_PROPS", default="font=OpenSans-Italic.ttf&size=36&lineHeight=1&letterSpacing=2&margin=1.0", help="Text styles for collection labels (font, size, line-height, letter-width)")
parser.add_argument('-ctext', dest="CREDIT_TEXT_PROPS", default="font=OpenSans-Regular.ttf&size=24&lineHeight=1.5&letterSpacing=1", help="Text styles for clock labels (font, size, line-height, letter-width)")
parser.add_argument('-color', dest="TEXT_COLOR", default="#FFFFFF", help="Color of font")

# Audio options
parser.add_argument('-cvolume', dest="CLIP_VOLUME", default=0.667, type=float, help="Volume of audio")

a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)

ASPECT_RATIO = 1920.0 / 1080.0
NUDGE_X = 0
aa["PRECISION"] = 5
aa["CLIP_WIDTH"] = roundInt(a.CLIP_WIDTH * a.WIDTH)
aa["CLIP_HEIGHT"] = roundInt(a.CLIP_WIDTH / ASPECT_RATIO)
aa["CREDIT_WIDTH"] = roundInt(a.CREDIT_WIDTH * a.WIDTH)
aa["MARGIN_X"] = (a.WIDTH - (a.CLIP_WIDTH + a.CREDIT_WIDTH)) / 3.0
aa["CLIP_X"] = a.MARGIN_X + NUDGE_X
aa["CLIP_Y"] = (a.HEIGHT - a.CLIP_HEIGHT) * 0.5
aa["CREDIT_CX"] = a.MARGIN_X * 2 + a.CLIP_WIDTH + a.CREDIT_WIDTH*0.5 - NUDGE_X
aa["TEXT_COLOR"] = hex2rgb(a.TEXT_COLOR)

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

if not a.PROBE:
    makeDirectories([a.OUTPUT_FRAME, a.OUTPUT_FILE, a.CELL_FILE])

# Add audio analysis to cells
collections = addCellDataToCollections(collections, cellsPerCollection, a.CELL_FILE)

minPerGroup = 2
ms = a.PAD_START
for i, c in enumerate(collections):
    producers = [p.strip() for p in c["producers"].split(",")]
    producerCount = len(producers)
    # print(producerCount)
    groupCount = ceilInt(1.0 * producerCount / a.TARGET_LINES)
    remainder = producerCount % a.TARGET_LINES
    if producerCount > a.TARGET_LINES and 0 < remainder <= minPerGroup:
        groupCount -= 1
    # print("%s -> %s" % (producerCount, groupCount))
    addPerGroup = [0 for j in range(groupCount)]
    if 0 < remainder <= minPerGroup:
        gindex = 0
        while remainder > 0:
            addPerGroup[gindex] += 1
            remainder -= 1
            gindex += 1
            if gindex >= groupCount:
                gindex = 0
    groups = []
    for j in range(groupCount):
        groupLen = min(producerCount, a.TARGET_LINES + addPerGroup[j])
        group = []
        for k in range(groupLen):
            if len(producers) <= 0:
                break
            group.append(producers.pop(0))
        fadeInStart = ms
        ms += a.FADE_DURATION
        fadeInEnd = ms
        ms += a.CREDIT_DURATION
        fadeOutStart = ms
        ms += a.FADE_DURATION
        fadeOutEnd = ms
        ms += a.PAD_DURATION
        groups.append({
            "groupLen": len(group),
            "producers": group,
            "fadeInStart": fadeInStart,
            "fadeInEnd": fadeInEnd,
            "fadeOutStart": fadeOutStart,
            "fadeOutEnd": fadeOutEnd
        })
    collections[i]["fadeInStart"] = groups[0]["fadeInStart"]
    collections[i]["fadeInEnd"] = groups[0]["fadeInEnd"]
    collections[i]["fadeOutStart"] = groups[-1]["fadeOutStart"]
    collections[i]["fadeOutEnd"] = groups[-1]["fadeOutEnd"]
    collections[i]["dur"] = collections[i]["fadeOutEnd"] - collections[i]["fadeInStart"]
    collections[i]["groups"] = groups
durationMs = ms

clips = []
for i, c in enumerate(collections):
    cdur = c["dur"]
    cells = sorted(c["cells"], key=lambda c: c["powerIndex"], reverse=True)
    loudestCell = cells[0]
    csample = loudestCell["samples"][0]
    csampleStart = csample["start"]
    csampleDur = cdur
    if csample["dur"] < cdur:
        delta = cdur - csample["dur"]
        csampleStart -= delta
    if csampleStart < 0:
        print("Warning: sample not long enough")
        csampleDur += csampleStart
        csampleStart = 0
    sample = {
        "index": len(clips),
        "x": a.CLIP_X,
        "y": a.CLIP_Y,
        "width": a.CLIP_WIDTH,
        "height": a.CLIP_HEIGHT,
        "filename": csample["filename"],
        "start": csampleStart,
        "dur": csampleDur
    }
    clip = Clip(sample)
    clip.queueTween(c["fadeInStart"], a.FADE_DURATION, [
        ("alpha", 0, 1.0, "sin")
    ])
    clip.queueTween(c["fadeOutStart"], a.FADE_DURATION, [
        ("alpha", 1.0, 0, "sin")
    ])
    clip.queuePlay(c["fadeInStart"], {
        "volume": a.CLIP_VOLUME,
        "fadeOut": a.FADE_DURATION,
        "fadeIn": a.FADE_DURATION,
        "matchDb": a.MATCH_DB
    })
    clips.append(clip)

# Calculate text sizes
titleTextProps = parseQueryString(a.TITLE_TEXT_PROPS, doParseNumbers=True)
titleItalicProps = parseQueryString(a.TITLE_ITALIC_TEXT_PROPS, doParseNumbers=True)
creditTextProps = parseQueryString(a.CREDIT_TEXT_PROPS, doParseNumbers=True)
titleFont = ImageFont.truetype(font=a.FONT_DIR + titleTextProps["font"], size=titleTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
titleItalicFont = ImageFont.truetype(font=a.FONT_DIR + titleItalicProps["font"], size=titleItalicProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
creditFont = ImageFont.truetype(font=a.FONT_DIR + creditTextProps["font"], size=creditTextProps["size"], layout_engine=ImageFont.LAYOUT_RAQM)
_, ah = creditFont.getsize("A")
creditLineHeight = ah * creditTextProps["lineHeight"]

def textToChars(text, font, props, startX):
    chars = []
    x = startX
    for char in list(text):
        cw, ch = font.getsize(char)
        chars.append({
            "x": x,
            "char": char
        })
        x += (props["letterSpacing"] + cw)
    return chars

producedText = " produced by"
producedTextLen = len(producedText)
for i, c in enumerate(collections):
    # determine title position and size
    title = c["name"] + producedText
    titleW, titleH = titleFont.getsize(title)
    titleW += (titleTextProps["letterSpacing"] * (len(title)-1))
    titleX = a.CREDIT_CX - titleW*0.5
    titleChars = textToChars(title, titleFont, titleTextProps, titleX)
    creditH = titleH + titleH * titleTextProps["margin"]
    creditH += (c["groups"][0]["groupLen"] * creditLineHeight)
    titleY = (a.HEIGHT - creditH) * 0.5
    creditY = titleY + titleH + titleH * titleTextProps["margin"]

    for j, g in enumerate(c["groups"]):
        producers = g["producers"]
        lines = []
        for k, p in enumerate(producers):
            producerY = creditY + k * creditLineHeight
            pw, ph = creditFont.getsize(p)
            pw += (creditTextProps["letterSpacing"] * (len(p)-1))
            px = a.CREDIT_CX - pw*0.5
            pChars = textToChars(p, creditFont, creditTextProps, px)
            lines.append({
                "y": producerY,
                "chars": pChars
            })
        collections[i]["groups"][j]["lines"] = lines

    collections[i]["titleY"] = titleY
    collections[i]["titleChars"] = titleChars

def getAlpha(p, ms):
    alpha = 0.0
    if p["fadeInStart"] <= ms < p["fadeOutEnd"]:
        # display title
        alpha = 1.0
        if c["fadeInStart"] <= ms < c["fadeInEnd"]:
            alpha = norm(ms, (c["fadeInStart"], c["fadeInEnd"]))
        elif c["fadeOutStart"] <= ms < c["fadeOutEnd"]:
            alpha = 1.0 - norm(ms, (c["fadeOutStart"], c["fadeOutEnd"]))
        alpha = ease(alpha)
    return alpha

def postProcessGLCredits(im, ms, globalArgs={}):
    global a
    global collections
    global titleFont
    global titleItalicFont
    global creditFont
    global producedTextLen

    draw = ImageDraw.Draw(im)

    for c in collections:
        if c["fadeInStart"] <= ms < c["fadeOutEnd"]:
            # display title
            alpha = getAlpha(c, ms)
            if alpha > 0:
                ty = c["titleY"]
                italicEnd = len(c["titleChars"]) - producedTextLen
                for cindex, char in enumerate(c["titleChars"]):
                    tfont = titleFont if cindex >= italicEnd else titleItalicFont
                    draw.text((char["x"], ty), char["char"], font=tfont, fill=tuple([roundInt(v*alpha) for v in a.TEXT_COLOR]))

            for g in c["groups"]:
                alpha = getAlpha(g, ms)
                if alpha <= 0.0:
                    continue
                for line in g["lines"]:
                    lineY = line["y"]
                    for char in line["chars"]:
                        draw.text((char["x"], lineY), char["char"], font=creditFont, fill=tuple([roundInt(v*alpha) for v in a.TEXT_COLOR]))

        elif ms < c["fadeInStart"]:
            break

    return im

processComposition(a, clips, durationMs, stepTime=stepTime, startTime=startTime,
    postProcessingFunction=postProcessGLCredits,
    renderOnTheFly=True
)
