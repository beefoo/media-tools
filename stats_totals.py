# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/movies.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="duration,samples", help="Comma-separated list of properties")
parser.add_argument('-filter', dest="FILTER", default="samples>0&medianPower>0", help="Filter string")
a = parser.parse_args()

# Parse arguments
PROPS = [p for p in a.PROPS.strip().split(",")]

# Read files
filenames = getFilenames(a.INPUT_FILE)
rows = []
for fn in filenames:
    _fieldNames, frows = readCsv(fn)
    rows += frows
rowCount = len(rows)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

def formatTime(s):
    h = int(s / 3600)
    s = s % 3600
    m = int(s / 60)
    s = s % 60
    s = roundInt(s)
    return str(h) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)

for prop in PROPS:
    d = [r[prop] for r in rows if prop in r and r[prop] > 0]
    print("-----\n" + prop + ":")
    total = sum(d)
    if "dur" in prop:
        print("Total: %s" % formatTime(total))
    else:
        print("Total: %s" % formatNumber(total))
    median = roundInt(np.median(d))
    if "dur" in prop:
        print("Median: %s" % formatSeconds(median))
    else:
        print("Median: %s" % formatNumber(median))
