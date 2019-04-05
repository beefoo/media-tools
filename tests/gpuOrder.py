# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from PIL import Image
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.gpu_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

WIDTH = 1920
HEIGHT = 1080
OUTPUT_FILE = "output/gpu_order_test/frame%s.png"

CLIP_W = roundInt(WIDTH * 0.25)
CLIP_H = roundInt(HEIGHT * 0.25)

makeDirectories([OUTPUT_FILE])

colors = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0)
]
clipCount = len(colors) * 4
margin = ((HEIGHT * 0.5) - CLIP_H) * 0.5 / len(colors)
clipPixelCount = CLIP_W * CLIP_H * 3
for step in range(5):
    properties = np.zeros((clipCount, 5), dtype=np.int32)
    pixelData = np.zeros(clipPixelCount * clipCount, dtype=np.uint8)
    offset = 0
    for i, c in enumerate(colors):
        for j in range(4):
            marginIX = (len(colors)-i) if j % 2 > 0 else i+1
            marginIY = (len(colors)-i) if j < 2 else i+1
            if step == 0:
                marginIX = i+1
                marginIY = i+1
            elif step == 1:
                marginIX = (len(colors)-i)
                marginIY = (len(colors)-i)
            elif step == 2:
                marginIX = i+1
            elif step == 3:
                marginIY = i+1
            x = (j % 2) * (WIDTH * 0.5) + margin * marginIX
            y = margin * marginIY if j < 2 else (HEIGHT * 0.5) + margin * marginIY
            im = Image.new(mode="RGB", size=(CLIP_W, CLIP_H), color=c)
            pixels = np.array(im, dtype=np.uint8)
            pixelData[offset:(offset+clipPixelCount)] = pixels.reshape(-1)
            properties[i*4+j] = np.array([offset, roundInt(x), roundInt(y), CLIP_W, CLIP_H])
            offset += clipPixelCount

    pixels = clipsToImageGPULite(WIDTH, HEIGHT, pixelData, properties)
    im = Image.fromarray(pixels, mode="RGB")
    filename = OUTPUT_FILE % (step+1)
    im.save(filename)
    print("Saved %s" % filename)
print("Done.")
