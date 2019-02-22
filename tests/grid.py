# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-width', dest="WIDTH", default=1920, type=int, help="Output video width")
parser.add_argument('-height', dest="HEIGHT", default=1080, type=int, help="Output video height")
parser.add_argument('-margin', dest="CLIP_MARGIN", default=1.0, type=float, help="Output video height")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
a = parser.parse_args()

# parse arguments
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])

samples = [{"index": i, "filename": "", "start": 0, "dur": 0} for i in range(GRID_W*GRID_H)]
samples = addGridPositions(samples, GRID_W, a.WIDTH, a.HEIGHT, marginX=a.CLIP_MARGIN, marginY=a.CLIP_MARGIN)

for i, s in enumerate(samples):
    pixels = np.array([[getRandomColor(i)]])
    samples[i]["framePixelData"] = [pixels]

clipsToFrame({
    "filename": "output/test_grid.png",
    "width": a.WIDTH,
    "height": a.HEIGHT,
    "clips": samples,
    "overwrite": True,
    "gpu": True,
    "debug": True
})

clipsToFrame({
    "filename": "output/test_grid2.png",
    "width": 100,
    "height": 100,
    "clips": [{
        "width": 99.0,
        "height": 99.0,
        "x": 0.5,
        "y": 0.5,
        "index": 0,
        "framePixelData": [getSolidPixels((255,0,0))]
    }],
    "overwrite": True,
    "gpu": True,
    "debug": True
})
clipsToFrame({
    "filename": "output/test_grid3.png",
    "width": 100,
    "height": 100,
    "clips": [{
        "width": 99.5,
        "height": 99.5,
        "x": 0.0,
        "y": 0.0,
        "index": 0,
        "framePixelData": [getSolidPixels((255,0,0))]
    }],
    "overwrite": True,
    "gpu": True,
    "debug": True
})
clipsToFrame({
    "filename": "output/test_grid4.png",
    "width": 100,
    "height": 100,
    "clips": [{
        "width": 99.5,
        "height": 99.5,
        "x": 0.5,
        "y": 0.5,
        "index": 0,
        "framePixelData": [getSolidPixels((255,0,0))]
    }],
    "overwrite": True,
    "gpu": True,
    "debug": True
})

print("Done.")
