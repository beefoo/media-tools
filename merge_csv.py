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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/rows.csv", help="Input file")
parser.add_argument('-in2', dest="INPUT_FILE2", default="tmp/rows2.csv", help="Second input file")
parser.add_argument('-cols', dest="COLS", default="", help="Columns from the first; leave blank if all")
parser.add_argument('-cols2', dest="COLS2", default="original:url,releaseDate:year", help="Columns from the second; leave blank if all")
parser.add_argument('-key', dest="KEY", default="identifier", help="Match on this key from the first file")
parser.add_argument('-key2', dest="KEY2", default="digest", help="Match on this key from the second file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if update the first file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Show plot?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite value if it already exists?")
a = parser.parse_args()

# Parse arguments
cols1 = a.COLS.strip().split(",") if len(a.COLS) > 0 else []
cols2 = a.COLS2.strip().split(",") if len(a.COLS2) > 0 else []
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

headings1, rows = readCsv(a.INPUT_FILE)
headings2, rows2 = readCsv(a.INPUT_FILE2)
rowCount = len(rows)

if len(cols1) < 1:
    cols1 = headings1

cols2From = []
cols2To = []
if len(cols2) < 1:
    cols2From = headings2
    cols2To = headings2
else:
    for i, col in enumerate(cols2):
        if ":" in col:
            keyFrom, keyTo = tuple(col.split(":"))
            cols2From.append(keyFrom)
            cols2To.append(keyTo)
        else:
            cols2From.append(col)
            cols2To.append(col)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)
headingsOut = unionLists(cols1, cols2To)

rows2Lookup = createLookup(rows2, a.KEY2)

noMatchCount = 0
for i, row in enumerate(rows):
    key = row[a.KEY]
    if key in rows2Lookup:
        row2 = rows2Lookup[key]
        for j, colFrom in enumerate(cols2From):
            rows[i][cols2To[j]] = row2[colFrom]
    else:
        noMatchCount += 1
    printProgress(i+1, rowCount)

print("Matched %s files" % (rowCount-noMatchCount))
print("Did not match %s files" % noMatchCount)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headingsOut)
