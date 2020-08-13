# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import os
from pprint import pprint
import re
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_globallives_all.csv", help="Input file")
parser.add_argument('-key', dest="COLUMN_KEY", default="filename", help="Column key to match against")
parser.add_argument('-pattern', dest="PATTERN", default=".*([0-2]\d):?([0-5]\d):?([0-5]\d)[ \-_]+([0-2]\d):?([0-5]\d):?([0-5]\d).*", help="File pattern")
parser.add_argument('-features', dest="PATTERN_FEATURES", default="hh0,mm0,ss0,hh1,mm1,ss1", help="Features that the pattern maps to")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if update the same file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Show plot?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite value if it already exists?")
a = parser.parse_args()

# Parse arguments
INPUT_FILE = a.INPUT_FILE
COLUMN_KEY = a.COLUMN_KEY
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else INPUT_FILE
PATTERN = a.PATTERN.strip()
PATTERN_FEATURES = a.PATTERN_FEATURES.strip().split(",")
PROBE = a.PROBE

# Read data
headings, rows = readCsv(INPUT_FILE)
for feature in PATTERN_FEATURES:
    if feature not in headings:
        headings.append(feature)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

pattern = re.compile(PATTERN)
rowCount = len(rows)
noMatchCount = 0
noMatches = []
for i, row in enumerate(rows):
    matches = pattern.match(str(row[COLUMN_KEY]))

    if not matches:
        # if a.PROBE:
        #     print("Did not match: %s" % row[COLUMN_KEY])
        noMatchCount += 1
        noMatches.append(row[COLUMN_KEY])
    elif a.PROBE:
        print("Matched %s" % row[COLUMN_KEY])

    for j, feature in enumerate(PATTERN_FEATURES):
        # check to see if we can overwrite
        if feature in row and not a.OVERWRITE and len(row[feature]) > 0:
            continue
        if matches:
            rows[i][feature] = matches.group(j+1)
        else:
            rows[i][feature] = ""

    printProgress(i+1, rowCount)

print("Matched %s files" % (rowCount-noMatchCount))
print("Did not match %s files" % noMatchCount)

if a.PROBE:
    if len(noMatches) > 0:
        pprint(noMatches)
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings)
