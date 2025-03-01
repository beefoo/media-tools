# -*- coding: utf-8 -*-

import inspect
import os
from PIL import Image, ImageFont, ImageDraw
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

# Config
debug = False
projectPath = "projects/mixed_messages/"
outPath = "output/mixed_messages/"
framesPath = "output/mixed_messages/frames/{fn}.png"
outputFile = "output/mixed_messages/mixed-messages-intro.mp4"
frameWidth = 1920
frameHeight = 1080
fps = 30
multiplier = 2
randomSeed = 7
transitions = 2
letterSpacing = 0
titleTop = 0.333
margin = 0.1
bgColor = "#1b1b1c"
title = [
    {"text": "Mixed", "color": "#eb67ff"},
    {"text": "Messages", "color": "#ffc800"}
]
subtitle = [
    {"text": "Demo", "color": "#d8dbde"}
]

# Timing config
holdStartDur = int(0.5 * 1000)
transitionInOutDur = int(0.667 * 1000)
moveDur = int(0.5 * 1000)
holdDur = int(0.25 * 1000)
titleHoldDur = int(4 * 1000)
holdEndDur = int(0.5 * 1000)

# Handle output folders
makeDirectories(framesPath)
if not debug:
    removeFiles(framesPath.format(fn="*"))

# Fonts
fontPath = f"{projectPath}JetBrainsMono-ExtraBold.ttf"
fontSizeTitle = 180 * multiplier
fontSizeSubtitle = 120 * multiplier
titleFont = ImageFont.truetype(font=fontPath, size=fontSizeTitle)
subtitleFont = ImageFont.truetype(font=fontPath, size=fontSizeSubtitle)

# Letter positioning
canvasWidth = frameWidth * multiplier
canvasHeight = frameHeight * multiplier
titleY = titleTop * canvasHeight
marginY = margin * canvasHeight
letterSpacingX = letterSpacing * canvasWidth
_titleX0, titleY0, _titleX1, titleY1 = titleFont.getbbox("L")
titleHeight = titleY1 - titleY0
subtitleY = titleY + titleHeight + marginY

def getCharData(texts, y, font, letterSpacing, canvasWidth):
    chars = []
    for text in texts:
        letters = list(text["text"])
        
        for letter in letters:
            x0, y0, x1, y1 = font.getbbox(letter)
            chars.append({
                "text": letter,
                "y": y,
                "w": x1 - x0,
                "h": y1 - y0,
                "color": text["color"],
                "font": font
            })

    charCount = len(chars)
    width = sum([char["w"] for char in chars]) + (charCount - 1) * letterSpacing
    x = (canvasWidth - width) * 0.5
    for i, char in enumerate(chars):
        chars[i]["x"] = x
        x += letterSpacing + char["w"]

    return chars

titleChars = getCharData(title, titleY, titleFont, letterSpacingX, canvasWidth)
subtitleChars = getCharData(subtitle, subtitleY, subtitleFont, letterSpacingX, canvasWidth)
chars = titleChars + subtitleChars
charCount = len(chars)
for i, char in enumerate(chars):
    chars[i]["i"] = i

positions = []
# Shuffle positions
for i in range(transitions):
    pos = [(char["x"], char["y"]) for char in chars]
    random.seed(randomSeed + i)
    random.shuffle(pos)
    positions.append(pos)
# Add final state
positions.append([(char["x"], char["y"]) for char in chars])
# Add transitions in and out
for i in range(2):
    ref = positions[0]
    if i > 0:
        ref = positions[-1]
    pos = []
    for j, char in enumerate(ref):
        x, y = char
        rand = pseudoRandom(randomSeed + i * charCount + j)
        rand2 = pseudoRandom(randomSeed + i * charCount + j + 100)
        sign = 1
        if rand > 0.5:
            sign = -1
        if rand2 > 0.5:
            x = canvasWidth * 1.5 * sign
        else:
            y = canvasHeight * 1.5 * sign
        pos.append((x, y))
    if i > 0:
        positions.append(pos)
    else:
        positions.insert(0, pos)

# Calculate start times
start = 0
transitionInStart = holdStartDur
transitionInEnd = transitionInStart + transitionInOutDur
moveStart = transitionInEnd
moveEnd = moveStart + moveDur * transitions + holdDur * transitions
titleStart = moveEnd
titleEnd = titleStart + titleHoldDur
transitionOutStart = titleEnd
transitionOutEnd = transitionOutStart + transitionInOutDur
holdEndStart = transitionOutEnd
end = holdEndStart + holdEndDur

# calculate duration and frames
totalMs = end
totalFrames = msToFrame(totalMs, fps)
totalFrames = int(ceilToNearest(totalFrames, fps))
totalMs = frameToMs(totalFrames, fps)

def transitionText(draw, fromPos, toPos, t):
    eased = ease(t)
    for i, c in enumerate(chars):
        x0, y0 = fromPos[i]
        x1, y1 = toPos[i]
        x = lerp((x0, x1), eased)
        y = lerp((y0, y1), eased)
        draw.text((x, y), c["text"], font=c["font"], fill=c["color"])

def drawFrame(fn, frame, total):
    if frame > total:
        return
    ms = frameToMs(frame, fps)
    if ms > totalMs:
        return

    base = Image.new(mode="RGB", size=(canvasWidth, canvasHeight), color=bgColor)
    draw = ImageDraw.Draw(base)

    if ms >= transitionInStart and ms < transitionInEnd:
        t = norm(ms, (transitionInStart, transitionInEnd), True)
        transitionText(draw, positions[0], positions[1], t)

    elif ms >= moveStart and ms < moveEnd:
        elapsed = ms - moveStart
        transitionDur = holdDur + moveDur
        iteration = floorInt(elapsed / transitionDur)
        iterationElapsed = elapsed % transitionDur
        t = 0
        if iterationElapsed > holdDur:
            t = norm(iterationElapsed, (holdDur, transitionDur), True)
        transitionText(draw, positions[iteration + 1], positions[iteration + 2], t)

    elif ms >= titleStart and ms < titleEnd:
        transitionText(draw, positions[-2], positions[-1], 0.0)

    elif ms >= transitionOutStart and ms < transitionOutEnd:
        t = norm(ms, (transitionOutStart, transitionOutEnd), True)
        transitionText(draw, positions[-2], positions[-1], t)

    base = base.resize((frameWidth, frameHeight))
    base.save(fn)

print(f"Total frames: {totalFrames}")
# drawFrame(f"{outPath}test.png", 60, totalFrames)

if debug:
    debugMs = titleStart
    debugFrame = msToFrame(debugMs, fps)
    drawFrame(f"{outPath}test.png", debugFrame, totalFrames)

else:
    for f in range(totalFrames):
        frame = f + 1
        fn = framesPath.format(fn=zeroPad(frame, totalFrames))
        drawFrame(fn, frame, totalFrames)
        prevFn = fn
        printProgress(frame, totalFrames)

    compileFrames(framesPath.format(fn="%s"), fps, outputFile, getZeroPadding(totalFrames), audioFile=None)

print("Done")