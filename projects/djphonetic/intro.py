# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from PIL import Image, ImageFont, ImageDraw
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.text_utils import *

projectPath = "projects/djphonetic/"
assetPath = f"{projectPath}assets/"
outputPath = "output/djphonetic/"

makeDirectories(outputPath)

frameWidth = 1920
frameHeight = 1080
multiplier = 2
canvasWidth = frameWidth * multiplier
canvasHeight = frameHeight * multiplier

bgColor = "#ff3e3e"
fontPath = f"{assetPath}subatomic.tsoonami.ttf"
textColor = "#000000"
fontSizeTitle = 90 * multiplier
fontSizeSubtitle = 72 * multiplier
titleFont = ImageFont.truetype(font=fontPath, size=fontSizeTitle)
subtitleFont = ImageFont.truetype(font=fontPath, size=fontSizeSubtitle)

titleY = 0.1925 * canvasHeight
logoY = 0.34 * canvasHeight
tongueY = 0.461 * canvasHeight
subtitleY = 0.802 * canvasHeight

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
    {"i": 0, "text": "D", "start": 0.388, "font": titleFont, "y": titleY},
    {"i": 1, "text": "J ", "start": 0.718, "font": titleFont, "y": titleY},
    {"i": 2, "text": "Pho", "start": 1.355, "font": titleFont, "y": titleY},
    {"i": 3, "text": "net", "start": 1.64, "font": titleFont, "y": titleY},
    {"i": 4, "text": "ic", "start": 1.82, "font": titleFont, "y": titleY}
]
title = addPositionsToText(title, titleY, titleFont)
subtitle = [
    {"i": 6, "text": "De", "start": 2.26, "font": subtitleFont, "y": subtitleY},
    {"i": 7, "text": "mo", "start": 2.631, "font": subtitleFont, "y": subtitleY}
]
subtitle = addPositionsToText(subtitle, subtitleY, subtitleFont)
titles = title + subtitle
images = {
    "mouth": {},
    "teethTop": {"path": f"{assetPath}teeth_top.png", "y": logoY},
    "teethBottom": {"path": f"{assetPath}teeth_bottom.png"},
    "tongue1": {"path": f"{assetPath}tongue_1.png"},
    "tongue2": {"path": f"{assetPath}tongue_2.png"},
    "tongue3": {"path": f"{assetPath}tongue_3.png"},
    "tongue4": {"path": f"{assetPath}tongue_4.png"},
    "tongue5": {"path": f"{assetPath}tongue_5.png", "y": tongueY}
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
    "x": teethTop["x"],
    "y": teethTop["y"] + teethTop["h"],
    "w": images["teethTop"]["w"],
    "h": images["teethTop"]["w"] - images["teethTop"]["h"] * 2
}
images["mouth"]["image"] = Image.new(mode="RGBA", size=(images["mouth"]["w"], images["mouth"]["h"]), color=textColor)
images["teethBottom"]["y"] = images["teethTop"]["y"] + images["teethTop"]["h"] + images["mouth"]["h"]

tongue = images["tongue5"]
for i in range(4, 0, -1):
    k = f"tongue{i}"
    images[k]["y"] = tongue["y"] + (tongue["h"] - images[k]["h"])

spokenAudio = f"{assetPath}dj_phonetic_demo_tetyys.com_RobotSoft_Five_120_60_reverb.wav"
swipeAudio = f"{assetPath}slide-metal_01.wav"

holdStart = 1.0
openDuration = 0.4
holdOpen = 1.0
closeDuration = 0.4
holdClose = 0.5
wipeDuration = 0.5
holdEnd = 1.0

base = Image.new(mode="RGB", size=(canvasWidth, canvasHeight), color=bgColor)
for k, p in images.items():
    base.paste(p["image"], (roundInt(p["x"]), roundInt(p["y"])), p["image"])

txt = Image.new("RGBA", base.size, (255, 255, 255, 0))
d = ImageDraw.Draw(txt)
for title in titles:
    d.text((title["x"], title["y"]), title["text"], font=title["font"], fill=textColor)
base.paste(txt, (0, 0), txt)

base.save(f"{outputPath}test.png")