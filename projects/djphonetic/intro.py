# -*- coding: utf-8 -*-

import argparse
import inspect
import librosa
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

from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.text_utils import *
from lib.video_utils import *

projectPath = "projects/djphonetic/"
assetPath = f"{projectPath}assets/"
framesPath = "output/djphonetic/frames/{fn}.png"
outputFile = "output/djphonetic/djphonetic-intro.mp4"

makeDirectories(framesPath)
removeFiles(framesPath.format(fn="*"))

frameWidth = 1920
frameHeight = 1080
fps = 30
multiplier = 2
canvasWidth = frameWidth * multiplier
canvasHeight = frameHeight * multiplier

bgColor = "#ff3e3e"
fontPath = f"{assetPath}subatomic.tsoonami.ttf"
textColor = "#000000"
wipeColor = "#000000"
fontSizeTitle = 90 * multiplier
fontSizeSubtitle = 72 * multiplier
titleFont = ImageFont.truetype(font=fontPath, size=fontSizeTitle)
subtitleFont = ImageFont.truetype(font=fontPath, size=fontSizeSubtitle)

titleY = 0.1925 * canvasHeight
logoY = 0.34 * canvasHeight
tongueY = 0.461 * canvasHeight
subtitleY = 0.802 * canvasHeight

textAnimateLength = 48 * multiplier
tongueAnimateLength = 72 * multiplier

def addPositionsToText(phones, y, font):
    totalWidth = 0
    for i, p in enumerate(phones):
        x0, y0, x1, y1 = font.getbbox(p["text"])
        phones[i]["w"] = x1 - x0
        phones[i]["h"] = y1 - y0
        totalWidth += phones[i]["w"]

    offsetX = (canvasWidth - totalWidth) * 0.5
    for i, p in enumerate(phones):
        phones[i]["x"] = offsetX
        offsetX += p["w"]
        
    return phones

title = [
    {"i": 0, "text": "D", "start": roundInt(0.388 * 1000), "font": titleFont, "y": titleY},
    {"i": 1, "text": "J ", "start": roundInt(0.718 * 1000), "font": titleFont, "y": titleY},
    {"i": 2, "text": "Pho", "start": roundInt(1.355 * 1000), "font": titleFont, "y": titleY},
    {"i": 3, "text": "net", "start": roundInt(1.64 * 1000), "font": titleFont, "y": titleY},
    {"i": 4, "text": "ic", "start": roundInt(1.82 * 1000), "font": titleFont, "y": titleY}
]
title = addPositionsToText(title, titleY, titleFont)
subtitle = [
    {"i": 6, "text": "De", "start": roundInt(2.26 * 1000), "font": subtitleFont, "y": subtitleY},
    {"i": 7, "text": "mo", "start": roundInt(2.631 * 1000), "font": subtitleFont, "y": subtitleY}
]
subtitle = addPositionsToText(subtitle, subtitleY, subtitleFont)
titles = title + subtitle
images = {
    "mouth": {},
    "tongue1": {"path": f"{assetPath}tongue_1.png"},
    "tongue2": {"path": f"{assetPath}tongue_2.png"},
    "tongue3": {"path": f"{assetPath}tongue_3.png"},
    "tongue4": {"path": f"{assetPath}tongue_4.png"},
    "tongue5": {"path": f"{assetPath}tongue_5.png", "y": tongueY},
    "teethTop": {"path": f"{assetPath}teeth_top.png", "y": logoY},
    "teethBottom": {"path": f"{assetPath}teeth_bottom.png"}
}
for k, p in images.items():
    if "path" in p:
        images[k]["image"] = Image.open(p["path"])
        w, h = images[k]["image"].size
        images[k]["w"] = w
        images[k]["h"] = h
        images[k]["x"] = (canvasWidth - w) * 0.5
teethTop = images["teethTop"]
images["mouth"] = {
    "x": teethTop["x"] + 1,
    "y": teethTop["y"] + teethTop["h"],
    "w": images["teethTop"]["w"] - 2,
    "h": images["teethTop"]["w"] - images["teethTop"]["h"] * 2
}
images["mouth"]["image"] = Image.new(mode="RGBA", size=(images["mouth"]["w"], images["mouth"]["h"]), color=textColor)
images["teethBottom"]["y"] = images["teethTop"]["y"] + images["teethTop"]["h"] + images["mouth"]["h"]

tongue = images["tongue5"]
for i in range(4, 0, -1):
    k = f"tongue{i}"
    images[k]["y"] = tongue["y"] + (tongue["h"] - images[k]["h"])

for k, p in images.items():
    images[k]["dx"] = p["x"]
    images[k]["dy"] = p["y"]
    images[k]["dw"] = p["w"]
    images[k]["dh"] = p["h"]

# Load audio data
spokenAudio = f"{assetPath}dj_phonetic_demo_tetyys.com_RobotSoft_Five_120_60_reverb.wav"
y, sr = loadAudioData(spokenAudio)
audioData = np.abs(librosa.stft(y))
dataH, dataW = audioData.shape
trimDataTop = int(0.1 * dataH)
trimDataBottom = int(0.1 * dataH)
dataH = dataH - trimDataTop - trimDataBottom
dataBucketCount = 5
bucketLength = int(dataH / dataBucketCount)
dataBuckets = np.zeros((dataBucketCount, dataW))
for i in range(dataBucketCount):
    i0 = i * bucketLength + trimDataTop
    i1 = i0 + bucketLength
    dataBuckets[i] = np.mean(audioData[i0:i1], axis=0)
dataMin, dataMax = (dataBuckets.min(), dataBuckets.max())
# print(dataMin, dataMax)

# timing config
holdStart = int(1.0 * 1000)
openDuration = int(0.4 * 1000)
holdBeforeSpeak = int(1.0 * 1000)
speakDuration = int(getDurationFromAudioData(y, sr) * 1000)
textInDuration = int(0.25 * 1000)
holdAfterSpeak = int(5.0 * 1000)

# calculate duration and frames
totalMs = holdStart + openDuration + holdBeforeSpeak + speakDuration + holdAfterSpeak
totalFrames = msToFrame(totalMs, fps)
totalFrames = int(ceilToNearest(totalFrames, fps))
totalMs = frameToMs(totalFrames, fps)

start = 0
openStart = holdStart
holdBeforeSpeakStart = openStart + openDuration
speakStart = holdBeforeSpeakStart + holdBeforeSpeak
holdAfterSpeakStart = speakStart + speakDuration
end = holdAfterSpeakStart + holdAfterSpeak

def drawFrame(fn, frame, total, prevFn=None):
    if frame > total:
        return
    ms = frameToMs(frame, fps)
    if ms > end:
        return

    if ms > holdAfterSpeakStart and prevFn is not None:
        copyfile(prevFn, fn)
        return

    base = Image.new(mode="RGB", size=(canvasWidth, canvasHeight), color=bgColor)

    mouthH = images["mouth"]["h"]
    logoH = images["teethTop"]["w"]
    teethH = images["teethTop"]["h"]

    # mouth is closed
    if ms <= openStart:
        deltaY = (logoH - (teethH * 2)) * 0.5
        images["teethTop"]["dy"] = images["teethTop"]["y"] + deltaY
        images["teethBottom"]["dy"] = images["teethBottom"]["y"] - deltaY
        images["mouth"]["dh"] = 0

    # mouth is opening
    elif ms < holdBeforeSpeakStart:
        n = norm(ms, (openStart, holdBeforeSpeakStart), limit=True)
        n = easeSinInOut(n)
        deltaY = (logoH - (teethH * 2)) * 0.5
        deltaY = deltaY * (1.0 - n)
        images["teethTop"]["dy"] = images["teethTop"]["y"] + deltaY
        images["teethBottom"]["dy"] = images["teethBottom"]["y"] - deltaY
        images["mouth"]["dy"] = images["teethTop"]["dy"] + teethH
        images["mouth"]["dh"] = images["teethBottom"]["dy"] - images["mouth"]["dy"]
    
    # mouth is open
    else:
        images["teethTop"]["dy"] = images["teethTop"]["y"]
        images["teethBottom"]["dy"] = images["teethBottom"]["y"]
        images["mouth"]["dh"] = images["mouth"]["h"]
        images["mouth"]["dy"] = images["mouth"]["y"]

    for i in range(1, 6):
        k = f"tongue{i}"
        image = images[k]
        dy = image["y"]

        if ms > speakStart and ms < holdAfterSpeakStart:
            n = norm(ms, (speakStart, holdAfterSpeakStart), limit=True)
            n = easeSinInOut(n)
            dataIndex = i - 1
            dataBucket = dataBuckets[4 - dataIndex]
            valueIndex = roundInt((dataW - 1) * n)
            value = dataBucket[valueIndex]
            nvalue = norm(value, (dataMin, dataMax), limit=True)
            deltaY = tongueAnimateLength * nvalue
            dy = dy - deltaY

        images[k]["dy"] = dy

    for k, p in images.items():
        if p["dw"] <= 0 or p["dh"] <= 0:
            continue

        image = p["image"]
        if p["w"] != p["dw"] or p["h"] != p["dh"]:
            image = image.resize((roundInt(p["dw"]), roundInt(p["dh"])))
        base.paste(image, (roundInt(p["dx"]), roundInt(p["dy"])), image)

    # draw text
    if ms > speakStart:

        for title in titles:

            txtStart = speakStart + title["start"]
            if ms <= txtStart:
                continue
            txtEnd = txtStart + textInDuration

            tx = title["x"]
            ty = title["y"]
            tw = title["w"]
            th = title["h"]
            deltaY = 0

            if ms < txtEnd:
                n = norm(ms, (txtStart, txtEnd), limit=True)
                n = easeSinInOut(n)
                tw = roundInt(tw * n)
                th = roundInt(th * n)
                tx = tx + (title["w"] - tw) * 0.5
                ty = ty + (title["h"] - th) * 0.5
                deltaY = (1.0 - n) * textAnimateLength
                ty = ty - deltaY

            if tw <= 0 or th <= 0:
                continue

            txt = Image.new("RGBA", (title["w"], title["h"]), (255, 255, 255, 0))
            d = ImageDraw.Draw(txt)
            d.text((0, 0), title["text"], font=title["font"], fill=textColor)
            xy = (roundInt(tx), roundInt(ty))
            if tw != title["w"] or th != title["h"]:
                txt = txt.resize((tw, th))
            base.paste(txt, xy, txt)

    base = base.resize((frameWidth, frameHeight))
    base.save(fn)

print(f"Total frames: {totalFrames}")
# drawFrame("output/djphonetic/test.png", 60, totalFrames)

prevFn = None
for f in range(totalFrames):
    frame = f + 1
    fn = framesPath.format(fn=zeroPad(frame, totalFrames))
    drawFrame(fn, frame, totalFrames, prevFn)
    prevFn = fn
    printProgress(frame, totalFrames)

compileFrames(framesPath.format(fn="%s"), fps, outputFile, getZeroPadding(totalFrames), audioFile=None)

print("Done")