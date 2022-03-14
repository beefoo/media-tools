# -*- coding: utf-8 -*-

import argparse
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import os
from pprint import pprint
import re
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/*.csv", help="Input files")
parser.add_argument('-cols', dest="COLS", default="", help="Columns to take; leave blank if all; supports mapping, e.g. fromField:toField,...")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just display info?")
a = parser.parse_args()

# Parse arguments
cols = a.COLS.strip().split(",") if len(a.COLS) > 0 else []
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
takeAllCols = len(cols) < 1

colReplace = {}
_cols = []
for col in cols:
    if ":" in col:
        keyFrom, col = tuple(col.split(":"))
        colReplace[keyFrom] = col
    if col not in _cols:
        _cols.append(col)
cols = _cols

files = getFilenames(a.INPUT_FILE)
rowsOut = []

for file in files:
    headings, rows = readCsv(file)

    for row in rows:
        rowOut = {}
        for h in headings:
            if h in cols or takeAllCols:

                if h not in cols:
                    cols.append(h)

                rowOut[h] = row[h]

            elif h in colReplace:
                colTo = colReplace[h]

                rowOut[colTo] = row[h]

        rowsOut.append(rowOut)


# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

if a.PROBE:
    sys.exit()

writeCsv(a.OUTPUT_FILE, rowsOut, cols)
