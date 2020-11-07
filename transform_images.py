# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/images.csv", help="Input file")
parser.add_argument('-dir', dest="INPUT_DIR", default="tmp/images/", help="Input image directory")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-fkey', dest="FILENAME_COL", default="filename", help="Filename column name")
parser.add_argument('-rotate', dest="ROTATE", default="", help="Degrees to rotate; can be a number or column name")
parser.add_argument('-maxd', dest="MAX_DIMENSION", default=-1, type=int, help="Maximum dimension of the image; -1 if none")
parser.add_argument('-ld', dest="TARGET_LONGEST_DIMENSION", default=-1, type=int, help="Target dimension of the longest side; -1 if none")
parser.add_argument('-flipx', dest="FLIP_X", default="", help="Flip left-to-right if negative value")
parser.add_argument('-flipy', dest="FLIP_Y", default="", help="Flip bottom-to-top if negative value")
parser.add_argument('-square', dest="SQUARIFY", action="store_true", help="Make it a square?")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/transformed/", help="Directory to output results")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

def parseParamValue(string, row):
    value = parseNumber(string)
    if not isNumber(value):
        value = row[string]
    return value

for i, row in enumerate(rows):
    fn = a.INPUT_DIR + row[a.FILENAME_COL]

    im = Image.open(fn)

    if len(a.FLIP_X) > 0:
        val = parseParamValue(a.FLIP_X, row)
        if isNumber(val) and val < 0:
            im = im.transpose(method=Image.FLIP_LEFT_RIGHT)

    if len(a.FLIP_Y) > 0:
        val = parseParamValue(a.FLIP_Y, row)
        if isNumber(val) and val < 0:
            im = im.transpose(method=Image.FLIP_TOP_BOTTOM)

    if len(a.ROTATE) > 0:
        degrees = parseParamValue(a.ROTATE, row)
        if isNumber(degrees):
            im = rotateImage(im, degrees, expand=True)

    w, h = im.size

    if a.MAX_DIMENSION > 0:

        resized = False
        if w > a.MAX_DIMENSION:
            scale = 1.0 * a.MAX_DIMENSION / w
            w = a.MAX_DIMENSION
            h = roundInt(h * scale)
            resized = True

        if h > a.MAX_DIMENSION:
            scale = 1.0 * a.MAX_DIMENSION / h
            h = a.MAX_DIMENSION
            w = roundInt(w * scale)
            resized = True

        if resized:
            im = resizeImage(im, w, h, mode="warp")

    if a.TARGET_LONGEST_DIMENSION > 0:
        tw = w
        th = h
        if w >= h:
            tw = a.TARGET_LONGEST_DIMENSION
            scale = 1.0 * tw / w
            th = roundInt(h * scale)
        else:
            th = a.TARGET_LONGEST_DIMENSION
            scale = 1.0 * th / h
            tw = roundInt(w * scale)

        if tw != w or th != h:
            im = resizeImage(im, tw, th, mode="warp")
            w = tw
            h = th

    if a.SQUARIFY and w != h:
        d = max(w, h)
        im = resizeCanvas(im, d, d)

    fnOut = a.OUTPUT_DIR + row[a.FILENAME_COL]
    im.save(fnOut)
    printProgress(i+1, rowCount)
