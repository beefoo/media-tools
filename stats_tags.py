# -*- coding: utf-8 -*-

import argparse
import collections
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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/items.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="tags", help="Comma-separated list of properties")
parser.add_argument('-sep', dest="SEPARATOR", default="|", help="Comma-separated list of properties")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-count', dest="DISPLAY_COUNT", default=50, type=int, help="Top tags to display")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/tags.csv", help="Output file")
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

tags = []
for row in rows:
    for prop in PROPS:
        if prop not in row or len(row[prop]) < 1:
            continue
        rtags = [value.strip().lower() for value in row[prop].split(a.SEPARATOR)]
        tags += rtags

tagCount = len(tags)
utags = unique(tags)
print("%s unique tags" % len(utags))
counter = collections.Counter(tags)
counts = counter.most_common(a.DISPLAY_COUNT)
for value, count in counts:
    print("%s (%s%%)\t %s" % (count, round(1.0*count / tagCount * 100.0, 2), value))

allCounts = counter.most_common()
rows = []
fields = ["value", "count"]
for value, count in allCounts:
    rows.append({
        "value": value,
        "count": count
    })
writeCsv(a.OUTPUT_FILE, rows, headings=fields)
