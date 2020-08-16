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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input csv file")
parser.add_argument('-add', dest="ADD_VALUES", default="", help="Query string to add more values, e.g. key1=value1&key2=value2")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if update the same file")
a = parser.parse_args()

# Parse arguments
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
addValues = parseQueryString(a.ADD_VALUES, doParseNumbers=True)

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

for key in addValues:
    if key not in fieldNames:
        fieldNames.append(key)

for i, row in enumerate(rows):
    for key, value in addValues.items():
        rows[i][key] = value

makeDirectories(OUTPUT_FILE)
writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
