# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
import os
import re
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="Input file")
parser.add_argument('-keys', dest="KEYS_TO_SEARCH", default="date,title,description", help="Column keys to search; in order of priority; comma-separated")
parser.add_argument('-re', dest="REGEX", default="\b(19[0-9][0-9])[\b\-]", help="Pattern to match")
parser.add_argument('-out', dest="OUT_KEY", default="year", help="Column key to create")
a = parser.parse_args()

KEYS_TO_SEARCH = args.KEYS_TO_SEARCH.strip().split(",")

# get files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

if a.OUT_KEY not in fieldNames:
    fieldNames.append(a.OUT_KEY)

pattern = re.compile(a.PATTERN)

print("Getting meta features...")
for i, row in enumerate(rows):
    value = ""
    for k in KEYS_TO_SEARCH:
        matches = pattern.match(row[k])
        if matches:
            value = matches.group(1)
            break
    rows[i][a.OUT_KEY] = value
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*(i+1)/rowCount*100,1))
    sys.stdout.flush()

writeCsv(a.INPUT_FILE, rows, headings=fieldNames)
