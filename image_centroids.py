# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image
from pprint import pprint
import sys

from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/*.jpg", help="Input file pattern; can be a single file or a glob string")
a = parser.parse_args()

# Read files
files = getFilenames(a.INPUT_FILE)

for fn in files:
    im = Image.open(fn)
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    w, h = im.size
    pixels = im.load()

    nonTransparentPixels = []
    for x in range(w):
        for y in range(h):
            px = pixels[x, y]
            r, g, b, a = px
            if a > 0:
                nonTransparentPixels.append((x, y))

    x = [p[0] for p in nonTransparentPixels]
    y = [p[1] for p in nonTransparentPixels]
    cx = (1.0 * sum(x) / len(nonTransparentPixels)) / w
    cy = (1.0 * sum(y) / len(nonTransparentPixels)) / h
    cx = round(cx, 3)
    cy = round(cy, 3)

    print(f"{fn}:\t{cx}, {cy}")

print("Done.")
