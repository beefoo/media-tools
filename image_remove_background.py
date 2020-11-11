# -*- coding: utf-8 -*-

import argparse
import cv2
from matplotlib import pyplot as plt
import numpy as np
import os
from PIL import Image
from pprint import pprint
import sys

from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/*.jpg", help="Input file pattern; can be a single file or a glob string")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/segments/", help="Segment data output directory")
# parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-blur', dest="BLUR_RADIUS", default=0.0, type=float, help="Guassian blur radius, e.g. 2.0")
parser.add_argument('-thresh', dest="THRESHOLD", default=0.99, type=float, help="Only include segments with at least this score")
parser.add_argument('-validate', dest="VALIDATE", action="store_true", help="Validate images?")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Display plot of first result?")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_DIR + "segments.csv"
filenames = getFilenames(a.INPUT_FILE)
filecount = len(filenames)

if a.VALIDATE:
    filenames = validateImages(filenames)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

def imageToSegment(filename, outFilename):
    global a

    # Read image, convert to grayscale, do threshold
    im_in = cv2.imread(filename)
    gray = cv2.cvtColor(im_in, cv2.COLOR_BGR2GRAY)
    th, im_th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Copy the thresholded image.
    im_floodfill = im_th.copy()

    # Mask used to flood filling.
    # Notice the size needs to be 2 pixels than the image.
    h, w = im_th.shape[:2]
    mask = np.zeros((h+2, w+2), np.uint8)

    # Floodfill from point (0, 0)
    cv2.floodFill(im_floodfill, mask, (0,0), 255)

    # Invert floodfilled image
    im_floodfill_inv = cv2.bitwise_not(im_floodfill)

    # Combine the two images to get the foreground.
    im_out = im_th | im_floodfill_inv

    # Display images.
    if a.DEBUG:
        # cv2.imshow("Original Image", im_in)
        # cv2.imshow("Thresholded Image", im_th)
        # cv2.imshow("Floodfilled Image", im_floodfill)
        # cv2.imshow("Inverted Floodfilled Image", im_floodfill_inv)
        cv2.imshow("Foreground", im_out)
        cv2.waitKey(0)

    # now try to get the largest segment
    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(im_out, connectivity=4)
    sizes = stats[:, -1]
    max_label = 1
    max_size = sizes[1]
    for i in range(1, nb_components):
        if sizes[i] > max_size:
            max_label = i
            max_size = sizes[i]

    maskWithLargestSegment = np.zeros(output.shape)
    maskWithLargestSegment[output == max_label] = 255

    if a.DEBUG:
        cv2.imshow("Biggest component", maskWithLargestSegment)
        cv2.waitKey(0)

    # get bounding box
    width = stats[max_label, cv2.CC_STAT_WIDTH]
    height = stats[max_label, cv2.CC_STAT_HEIGHT]
    x = stats[max_label, cv2.CC_STAT_LEFT]
    y = stats[max_label, cv2.CC_STAT_TOP]

    imageMaskWithLargestSegment = Image.fromarray(maskWithLargestSegment)
    imageMaskWithLargestSegment = imageMaskWithLargestSegment.convert("L")
    imageMaskWithLargestSegment = imageMaskWithLargestSegment.crop((x, y, x+width, y+height))

    srcImage = Image.open(filename)
    srcImage = srcImage.convert("RGBA")
    srcImage = srcImage.crop((x, y, x+width, y+height))

    segmentOut = alphaMask(srcImage, imageMaskWithLargestSegment)
    segmentOut.save(outFilename)
    print("Saved %s" % outFilename)

    return (x, y, width, height)

# imageToSegment("E:/production/papercuts/downloads/fish/6006022416.jpg", "E:/production/papercuts/segments/fish/6006022416.png")
# sys.exit()

segmentRows = []
for i, fn in enumerate(filenames):
    segmentFilename = getBasename(fn) + ".png"
    segmentFilepath = a.OUTPUT_DIR + segmentFilename

    x, y, w, h = imageToSegment(fn, segmentFilepath)
    printProgress(i+1, filecount)

    segmentRows.append({
        "sourceFilename": os.path.basename(fn),
        "filename": segmentFilename,
        "x": x,
        "y": y,
        "width": w,
        "height": h
    })

    if a.DEBUG:
        break

if a.DEBUG:
    sys.exit()

writeCsv(OUTPUT_FILE, segmentRows)
