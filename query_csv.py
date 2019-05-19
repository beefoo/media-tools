# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/movies.csv", help="Input file")
parser.add_argument('-display', dest="DISPLAY_PROPS", default="filename,title", help="Comma-separated list of properties to output")
parser.add_argument('-filter', dest="FILTER", default="duration>150&medianPower>0", help="Filter string")
parser.add_argument('-sort', dest="SORT", default="samples=desc", help="Sort string")
parser.add_argument('-count', dest="RESULT_COUNT", default=20, type=int, help="Number of results to display")
a = parser.parse_args()
# Parse arguments
DISPLAY_PROPS = [p for p in a.DISPLAY_PROPS.strip().split(",")]

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

if len(a.SORT) > 0:
    rows = sortByQueryString(rows, a.SORT)
    rowCount = len(rows)
    print("%s rows after sorting" % rowCount)

print("========")
for i, row in enumerate(rows):
    if i >= a.RESULT_COUNT:
        break
    displayStr = " ".join([row[p] for p in DISPLAY_PROPS])
    print("%s. %s" % (i+1, displayStr))
print("========")
