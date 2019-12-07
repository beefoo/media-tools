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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-sort', dest="SORT", default="", help="Sort string")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Number of results to limit to; -1 for no limit")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="File to output results; leave empty to update input file")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

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

if a.LIMIT > 0 and rowCount > a.LIMIT:
    rows = rows[:a.LIMIT]
    rowCount = len(rows)
    print("%s rows after limiting" % rowCount)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
