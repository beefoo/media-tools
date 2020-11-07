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
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/", help="Input dir if input file is a .csv")
parser.add_argument('-width', dest="WIDTH", default=360, type=int, help="Image width, -1 for auto")
parser.add_argument('-height', dest="HEIGHT", default=120, type=int, help="Image height, -1 for auto")
parser.add_argument('-type', dest="RESIZE_TYPE", default="fill", help="Resize type: fill or contain")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/", help="Image output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing images?")
a = parser.parse_args()

if a.WIDTH <= 0 and a.HEIGHT <= 0:
    print("Enter a valid width and/or height")
    sys.exit()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

# Read files
files = getFilenames(a.INPUT_FILE)

for fn in files:
    outfn = a.OUTPUT_DIR + os.path.basename(fn)

    if not a.OVERWRITE and os.path.isfile(outfn):
        continue

    im = Image.open(fn)
    imW, imH = im.size
    imRatio = 1.0 * imW / imH

    if a.HEIGHT <= 0:
        height = roundInt(a.WIDTH / imRatio)
        im = im.resize((a.WIDTH, height), resample=Image.LANCZOS)

    elif a.WIDTH <= 0:
        width = roundInt(a.HEIGHT * imRatio)
        im = im.resize((width, a.HEIGHT), resample=Image.LANCZOS)

    elif a.RESIZE_TYPE == "fill":
        im = fillImage(im, a.WIDTH, a.HEIGHT)

    else:
        im = containImage(im, a.WIDTH, a.HEIGHT)

    im.save(outfn)
    print("Saved %s" % outfn)

print("Done.")
