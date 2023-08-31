# -*- coding: utf-8 -*-

import argparse
import inspect
import os
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

frameWidth = 1920
frameHeight = 1080
multiplier = 2
canvasWidth = frameWidth * multiplier
canvasHeight = frameHeight * multiplier

bgColor = "#ff3e3e"
font = f"{assetPath}subatomic.tsoonami.ttf"
textColor = "#000000"
fontSizeTitle = 90
fontSizeSubtitle = 72
letterSpacing = 2

titleY = 0.1925
logoY = 0.34
subtitleY = 0.802

title = [
    {"i": 0, "text": "D", "start": 0.388},
    {"i": 1, "text": "J ", "start": 0.718},
    {"i": 2, "text": "Pho", "start": 1.355},
    {"i": 3, "text": "net", "start": 1.64},
    {"i": 4, "text": "ic", "start": 1.82}
]
subtitle = [
    {"i": 6, "text": "De", "start": 2.26},
    {"i": 7, "text": "mo", "start": 2.631}
]
images = [
    "teethTop": f"{assetPath}teeth_top.png",
    "teethBottom": f"{assetPath}teeth_bottom.png",
    "tongue1": f"{assetPath}tongue_1.png",
    "tongue2": f"{assetPath}tongue_2.png",
    "tongue3": f"{assetPath}tongue_3.png",
    "tongue4": f"{assetPath}tongue_4.png",
    "tongue5": f"{assetPath}tongue_5.png"
]


spokenAudio = f"{assetPath}dj_phonetic_demo_tetyys.com_RobotSoft_Five_120_60_reverb.wav"
swipeAudio = f"{assetPath}slide-metal_01.wav"

holdStart = 1.0
openDuration = 0.4
holdOpen = 1.0
closeDuration = 0.4
holdClose = 0.5
wipeDuration = 0.5
holdEnd = 1.0