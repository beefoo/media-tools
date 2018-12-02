# -*- coding: utf-8 -*-

import argparse
import inspect
from matplotlib import pyplot as plt
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-sort', dest="SORT", default="flatness=desc=0.5&power=desc", help="Query string to sort by")
parser.add_argument('-lim', dest="LIMIT", default=1296, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-highlight', dest="HIGHLIGHT", default="", help="Property to highlight")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
SORT = args.SORT
LIMIT = args.LIMIT
HIGHLIGHT = args.HIGHLIGHT

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Sort and limit
rows = sortByQueryString(rows, SORT)
if LIMIT > 0 and len(rows) > LIMIT:
    rows = rows[:LIMIT]

x = [row["tsne"] for row in rows]
y = [row["tsne2"] for row in rows]


plt.figure(figsize = (10,10))
if len(HIGHLIGHT) > 0:
    values = list(set([row[HIGHLIGHT] for row in rows]))
    colors = [values.index(row[HIGHLIGHT]) for row in rows]
    plt.scatter(x, y, c=colors, s=4)
else:
    plt.scatter(x, y, s=4)
plt.show()
