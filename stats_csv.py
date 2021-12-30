# -*- coding: utf-8 -*-

import argparse
import collections
import inspect
import math
import os
from pprint import pprint
import re
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/records.csv", help="Input csv file")
parser.add_argument('-props', dest="PROPS", default="duration,samples", help="Comma-separated list of properties; leave blank to see a summary of all props")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-delimeter', dest="LIST_DELIMETER", default="", help="If a list, provide delimeter(s)")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Limit list length")
parser.add_argument('-ee', dest="EXCLUDE_EMPTY", action="store_true", help="Exclude empty value?")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Optional file to output the results to")
a = parser.parse_args()

# Parse arguments
PROPS = [p.strip() for p in a.PROPS.strip().split(",")]

# Read rows
filenames = getFilenames(a.INPUT_FILE)
rows = []
for fn in filenames:
    _, fRows = readCsv(fn)
    rows += fRows
rowCount = len(rows)
print(f'{rowCount} total rows found')

if len(a.PROPS) < 1:
    allProps = {}
    for row in rows:
        for key, value in row.items():
            if len(str(value).strip()) < 1:
                continue
            if key in allProps:
                allProps[key]["count"] += 1
            else:
                allProps[key] = {
                    "count": 1,
                    "example": value
                }

    allPropsSorted = []
    for key, p in allProps.items():
        allPropsSorted.append({
            "key": key,
            "count": p["count"],
            "example": p["example"]
        })
    allPropsSorted = sorted(allPropsSorted, key=lambda p: -p["count"])

    print("Unique properties:")
    for p in allPropsSorted:
        print(f'- {p["key"]}: {p["count"]} (e.g. "{p["example"]}")')

    sys.exit()


if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print(f'{rowCount} rows after filtering')

for prop in PROPS:
    values = [row[prop] for row in rows if prop in row]
    if len(a.LIST_DELIMETER) > 0:
        expandedValues = []
        for value in values:
            value = str(value).strip()
            expanded = [v.strip() for v in re.split(a.LIST_DELIMETER, value)]
            expanded = [v for v in expanded if len(v) > 0] # remove blanks
            expandedValues += expanded
        values = expandedValues

    if a.EXCLUDE_EMPTY:
        values = [v for v in values if str(v).strip() != ""]
    vcount = len(values)
    uvalues = unique(values)

    counter = collections.Counter(values)
    counts = None
    if a.LIMIT > 0:
        counts = counter.most_common(a.LIMIT)
    else:
        counts = counter.most_common()
    print("---------------------------")
    print(f'{len(uvalues)} unique values for "{prop}"')
    print("---------------------------")
    rowsOut = []
    for value, count in counts:
        percent = round(1.0 * count / vcount * 100.0, 1)
        if value == "":
            value = "<empty>"
        # print(f'{formatNumber(count)} ({percent}%)\t{value}')
        print(f'{value} ({percent}%)')
        row = {}
        row[prop] = value
        row["count"] = count
        row["percent"] = percent
        rowsOut.append(row)

    if len(a.OUTPUT_FILE) > 0:
        makeDirectories(a.OUTPUT_FILE)
        writeCsv(a.OUTPUT_FILE % prop, rowsOut, headings=[prop, "count", "percent"])
