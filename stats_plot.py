# -*- coding: utf-8 -*-

# python -W ignore samples_to_plot.py -in tmp/ia_politicaladarchive_samples.csv -props "power,hz" -log 1 -lim -1

import argparse
import inspect
import math
from matplotlib import pyplot as plt
import numpy as np
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="power,hz", help="X and Y properties")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by, e.g. clarity=desc")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-log', dest="LOG", default=0, type=int, help="Display using log?")
parser.add_argument('-highlight', dest="HIGHLIGHT", default="", help="Property to highlight")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
PROPS = [p for p in args.PROPS.strip().split(",")]
SORT = args.SORT
LIMIT = args.LIMIT
HIGHLIGHT = args.HIGHLIGHT
LOG = args.LOG

PROP1 = PROPS[0]
PROP2 = PROPS[1] if len(PROPS) > 1 else None

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Sort and limit
rows = sortByQueryString(rows, SORT)
if LIMIT > 0 and len(rows) > LIMIT:
    rows = rows[:LIMIT]

def log(value, base=1):
    if base==1:
        base = math.e
    return math.log(value, base) if value > 0 else value

x = []
y = []
if PROP2 is not None:
    x = [row[PROP1] for row in rows]
    y = [row[PROP2] for row in rows]
    if LOG > 0:
        x = [log(row[PROP1], LOG) for row in rows]
        y = [log(row[PROP2], LOG) for row in rows]
else:
    y = [row[PROP1] for row in rows]
    if LOG > 0:
        y = [log(row[PROP1], LOG) for row in rows]
    y = sorted(y)
    x = np.linspace(0.0, 1.0, len(y))

plt.figure(figsize = (10,10))
if len(HIGHLIGHT) > 0:
    values = list(set([row[HIGHLIGHT] for row in rows]))
    colors = [values.index(row[HIGHLIGHT]) for row in rows]
    plt.scatter(x, y, c=colors, s=4)
else:
    plt.scatter(x, y, s=4)
plt.show()
