# -*- coding: utf-8 -*-

import argparse
import math
import numpy as np
import os
from pprint import pprint
import rasterfairy
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="tsne,tsne2", help="Properties to sort x,y matrix by")
parser.add_argument('-sort', dest="SORT", default="clarity=desc=0.5&power=desc", help="Query string to filter and sort by")
parser.add_argument('-oprops', dest="OUT_PROPS", default="gridX,gridY", help="Output grid properties")
parser.add_argument('-grid', dest="GRID", default="256x256", help="Size of grid")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output file; blank if the same as input file")
a = parser.parse_args()

# Parse arguments
PROPS = [p for p in a.PROPS.strip().split(",")]
PROP1, PROP2 = tuple(PROPS)
OUT_PROPS = [p for p in a.OUT_PROPS.strip().split(",")]
OUT_PROP1, OUT_PROP2 = tuple(OUT_PROPS)
GRID_W, GRID_H = tuple([int(v) for v in a.GRID.strip().split("x")])
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
GRID_COUNT = GRID_W * GRID_H

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

# Add out props to fieldnames
for p in OUT_PROPS:
    if p not in fieldNames:
        fieldNames.append(p)

# Sort and limit
if sampleCount > GRID_COUNT:
    print("Too many samples... sorting and limiting")
    samples = sortByQueryString(samples, a.SORT)
    samples = samples[:GRID_COUNT]
elif sampleCount < GRID_COUNT:
    print("Not enough samples (%s) for the grid you want (%s x %s = %s). Exiting." % (sampleCount, GRID_W, GRID_H, GRID_COUNT))
    sys.exit()

# prep values
for i, s in enumerate(samples):
    for p in PROPS:
        value = s[p]
        if p == "hz":
            value = math.log(value)
        value *= 1000.0
        samples[i]["_"+p] = value

xy = [[s["_"+PROP1], s["_"+PROP2]] for s in samples]
# pprint(xy)
# sys.exit()
xy = np.array(xy)

print("Determining grid assignment...")
gridAssignment = rasterfairy.transformPointCloud2D(xy, target=(GRID_W, GRID_H))
grid, gridShape = gridAssignment
for i, s in enumerate(samples):
    gridX, gridY = grid[i]
    samples[i][OUT_PROP1] = int(gridX)
    samples[i][OUT_PROP2] = int(gridY)

writeCsv(OUTPUT_FILE, samples, headings=fieldNames)
