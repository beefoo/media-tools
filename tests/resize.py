# -*- coding: utf-8 -*-

import argparse
import inspect
import math
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont
from pprint import pprint
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

WIDTH = 800
HEIGHT = 600
EXCERPT_MS = 30000
FPS = 30
SIZES = [64, 32, 16, 8]
FRAME_FILE = "tmp/resize_test/frame.%s.png"
OUTPUT_FILE = "output/resize_test.mp4"

makeDirectories([FRAME_FILE, OUTPUT_FILE])

video = VideoFileClip("media/sample/LivingSt1958.mp4", audio=False)
videoDur = video.duration

totalFrames = msToFrame(EXCERPT_MS, FPS)
fnt = ImageFont.truetype('media/fonts/Open_Sans/OpenSans-Regular.ttf', 28)

def pasteSizes(im, draw, clipImg, sizes, method, x, y, w, h, label):
    global fnt

    maxSize = max(sizes)
    sizeCount = len(sizes)
    cols = ceilInt(math.sqrt(sizeCount))
    rows = ceilInt(1.0*sizeCount/cols)
    boxW = w / cols
    boxH = h / rows
    clipW, clipH = clipImg.size
    aspectRatio = 1.0 * clipW / clipH
    for i, size in enumerate(sizes):
        rw = size
        rh = roundInt(size / aspectRatio)
        resized = clipImg.resize((rw, rh), resample=method)
        row = int(i / cols)
        col = i % cols
        rx = col * boxW + (boxW-rw) * 0.5 + x
        ry = row * boxH + (boxH-rh) * 0.5 + y
        im.paste(resized, (roundInt(rx), roundInt(ry)))
    draw.text((roundInt(x)+20, roundInt(h/2+y)-14), label, fill=(255, 255, 255), font=fnt)
    return im

zpad = getZeroPadding(totalFrames)
for f in range(totalFrames):
    frame = f + 1
    ms = frameToMs(frame, FPS)
    videoT = ms / 1000.0
    videoPixels = video.get_frame(videoT)
    clipImg = Image.fromarray(videoPixels, mode="RGB")
    im = Image.new(mode="RGB", size=(WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(im)

    boxW = WIDTH / 3.0
    boxH = HEIGHT / 2.0
    im = pasteSizes(im, draw, clipImg, SIZES, Image.NEAREST, 0, 0, boxW, boxH, "Nearest")
    im = pasteSizes(im, draw, clipImg, SIZES, Image.BOX, 1.0*WIDTH/3, 0, boxW, boxH, "Box")
    im = pasteSizes(im, draw, clipImg, SIZES, Image.BILINEAR, 2.0*WIDTH/3, 0, boxW, boxH, "Bilinear")
    im = pasteSizes(im, draw, clipImg, SIZES, Image.HAMMING, 0, HEIGHT/2, boxW, boxH, "Hamming")
    im = pasteSizes(im, draw, clipImg, SIZES, Image.BICUBIC, 1.0*WIDTH/3, HEIGHT/2, boxW, boxH, "Bicubic")
    im = pasteSizes(im, draw, clipImg, SIZES, Image.LANCZOS, 2.0*WIDTH/3, HEIGHT/2, boxW, boxH, "Lanczos")

    filename = FRAME_FILE % zeroPad(frame, totalFrames)
    im.save(filename)
    printProgress(frame, totalFrames)

video.reader.close()
del video

compileFrames(FRAME_FILE, FPS, OUTPUT_FILE, getZeroPadding(totalFrames))
