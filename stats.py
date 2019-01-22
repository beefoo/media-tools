# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.math_utils import *
from matplotlib import pyplot as plt
import os
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-bins', dest="BINS", type=int, default=50, help="Bins for histogram")
parser.add_argument('-ncols', dest="NCOLS", type=int, default=3, help="Number of columns")
parser.add_argument('-fig', dest="FIG_SIZE", default=" 16,8", help="Figure size in inches")
parser.add_argument('-plot', dest="PLOT_KEYS", default="power,dur,clarity,hz,note,octave", help="Comma separated list of parameters to plot")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
BINS = args.BINS
NCOLS = args.NCOLS
FIG_SIZE = tuple([int(d) for d in args.FIG_SIZE.strip().split(",")])
PLOT_KEYS = args.PLOT_KEYS.strip().split(",")

# Read files
rows = []
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

propertyCount = len(PLOT_KEYS)
ncols = NCOLS if propertyCount > NCOLS else propertyCount
nrows = ceilInt(1.0 * propertyCount / ncols)

plt.figure(figsize=FIG_SIZE)

for i, key in enumerate(PLOT_KEYS):
    data = [parseFloat(r[key]) for r in rows if p[key] in r]
    if len(data) > 0:
        first = data[0]
        ax = plt.subplot(nrows, ncols, i+1)
        ax.set_title(key)
        if isNumber(first):
            plt.hist(data, bins=BINS)
        else:
            labels = unique(data)
            ndata = [labels.index(d) for d in data]
            plt.xticks(range(len(labels)), labels)
            plt.hist(ndata, bins=BINS)

plt.tight_layout()
plt.show()
