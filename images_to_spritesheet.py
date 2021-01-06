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
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/images.csv", help="Input file pattern")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/", help="Input dir if input file is a .csv")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-rows', dest="ROWS", default=8, type=int, help="Number of rows")
parser.add_argument('-cols', dest="COLS", default=8, type=int, help="Number of cols")
parser.add_argument('-cellw', dest="CELL_W", default=256, type=int, help="Width of sprite cell")
parser.add_argument('-cellh', dest="CELL_H", default=256, type=int, help="Height of sprite cell")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit number of images; -1 if fill as much as possible")
parser.add_argument('-type', dest="RESIZE_TYPE", default="fill", help="Resize type: fill or contain")
parser.add_argument('-out', dest="OUTPUT_IMAGE", default="output/sprite.png", help="Image output file")
parser.add_argument('-alpha', dest="HAS_ALPHA", action="store_true", help="Treat images as RGBA?")
parser.add_argument('-small', dest="TO_EIGHT_BIT_FILE", action="store_true", help="Make this an 8-bit file?")
a = parser.parse_args()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_IMAGE)

# Read files
fieldNames, rows, rowCount = getFilesFromString(a)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

if len(a.SORT) > 0:
    rows = sortByQueryString(rows, a.SORT)
    rowCount = len(rows)
    print("%s rows after sorting" % rowCount)

limit = a.ROWS * a.COLS
if a.LIMIT > 0:
    limit = min(limit, a.LIMIT)
rows = rows[:limit]
imageW = a.CELL_W * a.COLS
imageH = a.CELL_H * a.ROWS
bgColor = (0,0,0)
imageMode = "RGB"
if a.HAS_ALPHA:
    bgColor = (0,0,0,0)
    imageMode = "RGBA"
baseImg = Image.new(mode=imageMode, size=(imageW, imageH), color=bgColor)

for i, row in enumerate(rows):
    im = Image.open(row["filename"])
    if im.mode != imageMode:
        im = im.convert(imageMode)
    imW, imH = im.size
    if imW != a.CELL_W or imH != a.CELL_H:
        im = resizeImage(im, a.CELL_W, a.CELL_H, mode=a.RESIZE_TYPE)

    x = i % a.COLS * a.CELL_W
    y = floorInt(1.0 * i / a.COLS) * a.CELL_H
    baseImg.paste(im, (x, y))

if a.TO_EIGHT_BIT_FILE:
    toEightBit(baseImg, a.OUTPUT_IMAGE)
else:
    baseImg.save(a.OUTPUT_IMAGE)

print("Done.")
