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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_fedflixnara.csv", help="Input file")
parser.add_argument('-key', dest="COLUMN_KEY", default="description", help="Column key to match against")
parser.add_argument('-pattern', dest="PATTERN", default="Department of [A-Za-z ]+", help="String pattern")
parser.add_argument('-features', dest="OUTPUT_KEY", default="collection", help="Features that the pattern maps to")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if update the same file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Show plot?")
parser.add_argument('-verbose', dest="VERBOSE", action="store_true", help="Verbose messaging?")
a = parser.parse_args()

# Parse arguments
INPUT_FILE = a.INPUT_FILE
COLUMN_KEY = a.COLUMN_KEY
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else INPUT_FILE
PATTERN = a.PATTERN.strip()
OUTPUT_KEY = a.OUTPUT_KEY.strip()
PROBE = a.PROBE

# Read data
headings, rows = readCsv(INPUT_FILE)
if OUTPUT_KEY not in headings:
    headings.append(OUTPUT_KEY)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

pattern = re.compile(PATTERN+'|$')
rowCount = len(rows)
noMatchCount = 0
matched = [False for i in range(len(rows))]
for i, row in enumerate(rows):
    match = pattern.search(row[COLUMN_KEY]).group()

    if len(match) < 1:
        if a.VERBOSE:
            print("Did not match: %s" % row[COLUMN_KEY])
        noMatchCount += 1
    else:
        matched[i] = True

    rows[i][OUTPUT_KEY] = match

print("Matched %s files" % (rowCount-noMatchCount))
print("Did not match %s files" % noMatchCount)

if a.PROBE:
    counts = getCounts(rows, OUTPUT_KEY)
    pprint(counts)
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings)
