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
parser.add_argument('-in', dest="INPUT_FILE", default="media/*.png", help="Input file pattern; can be a single file or a glob string")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/segments/", help="Output directory")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Display debug info inly?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILE)
# filenames = filenames[:2]

# filenames = validateImages(filenames)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

def saveImageWithLargestSegment(fn):
    global a
    originalImageWithAlpha = Image.open(fn) # this must have alpha
    imW, imH = originalImageWithAlpha.size

    black = Image.new("L", size=(imW, imH), color=0)
    white = Image.new("L", size=(imW, imH), color=255)
    mask = Image.composite(white, black, originalImageWithAlpha)

    pixels = np.asarray(mask)
    nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(pixels, connectivity=4)
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
        return

    imageMaskWithLargestSegment = Image.fromarray(maskWithLargestSegment)
    imageMaskWithLargestSegment = imageMaskWithLargestSegment.convert("L")
    imageWithLargestSegment = alphaMask(originalImageWithAlpha, imageMaskWithLargestSegment)
    newImagePath = a.OUTPUT_DIR + os.path.basename(fn)
    imageWithLargestSegment.save(newImagePath)

total = len(filenames)
for i, fn in enumerate(filenames):
    saveImageWithLargestSegment(fn)
    if a.DEBUG:
        break
    printProgress(i+1, total)

print("Done.")
