# -*- coding: utf-8 -*-

import argparse
from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *
import os
from PIL import Image, ImageStat
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="images.csv", help="Input file pattern")
parser.add_argument('-dir', dest="IMAGE_DIR", default="path/to/images/", help="Input dir")
parser.add_argument('-fkey', dest="FILENAME_KEY", default="filename", help="Key for filename")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output csv file; leave blank if same as input")
parser.add_argument('-cutoff', dest="MSE_CUTOFF", default=22, type=int, help="Median squared error cut-off")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
a = parser.parse_args()

# Parse arguments
INPUT_FILE = a.INPUT_FILE
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else INPUT_FILE

keysToAdd = ["isColorImage"]

makeDirectories(OUTPUT_FILE)

print("Reading files...")
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)

# add keys
for key in keysToAdd:
    if key not in fieldNames:
        fieldNames.append(key)

# https://stackoverflow.com/questions/20068945/detect-if-image-is-color-grayscale-or-black-and-white-with-python-pil
def detectColorImage(file, thumb_size=40, MSE_cutoff=22, adjust_color_bias=True):
    isColor = 0
    pil_img = Image.open(file)
    bands = pil_img.getbands()
    if bands == ('R','G','B') or bands == ('R','G','B','A'):
        thumb = pil_img.resize((thumb_size, thumb_size))
        SSE, bias = 0, [0,0,0]
        if adjust_color_bias:
            bias = ImageStat.Stat(thumb).mean[:3]
            bias = [b - sum(bias)/3 for b in bias ]
        for pixel in thumb.getdata():
            mu = sum(pixel)/3
            SSE += sum((pixel[i] - mu - bias[i])*(pixel[i] - mu - bias[i]) for i in [0,1,2])
        MSE = float(SSE)/(thumb_size*thumb_size)
        if MSE > MSE_cutoff:
            isColor = 1

    return isColor

for i, row in enumerate(rows):
    filename = a.IMAGE_DIR + row[a.FILENAME_KEY]
    isColor = detectColorImage(filename, MSE_cutoff=a.MSE_CUTOFF)
    rows[i]["isColorImage"] = isColor
    printProgress(i+1, rowCount)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
