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
parser.add_argument('-props', dest="PROPS", default="", help="Comma-separated list of properties to output; leave empty for all")
parser.add_argument('-groups', dest="GROUPS", default="", help="Comma-separated list of groups to output")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-sort', dest="SORT", default="", help="Sort string")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit the number of results; -1 for all")
parser.add_argument('-light', dest="LIGHT", action="store_true", help="Output the data in a 'light' format")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/samples.json", help="Output json file")
a = parser.parse_args()
# Parse arguments

PROPS = [p for p in a.PROPS.strip().split(",")]

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
if len(PROPS) < 1:
    PROPS = fieldNames
rowCount = len(rows)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

if len(a.SORT) > 0:
    rows = sortByQueryString(rows, a.SORT)
    rowCount = len(rows)
    print("%s rows after sorting" % rowCount)

if a.LIMIT > 0 and len(rows) > a.LIMIT:
    rows = rows[:a.LIMIT]
    rowCount = len(rows)
    print("%s rows after limiting" % rowCount)

GROUPS = [p for p in a.GROUPS.strip().split(",")] if len(a.GROUPS) > 0 else []
groups = None
if len(GROUPS) > 0:
    groups = {}
    for groupKey in GROUPS:
        groups[groupKey] = sorted(unique([r[groupKey] for r in rows]))

items = []
for r in rows:
    item = {}
    for p in PROPS:
        if p in GROUPS:
            item[p] = groups[p].index(r[p])
        else:
            item[p] = r[p]
    items.append(item)

jsonOut = {}
if a.LIGHT:
    jsonOut["itemHeadings"] = PROPS
    jrows = []
    for r in rows:
        jrows.append([r[p] for p in PROPS])
    jsonOut["items"] = jrows
else:
    jsonOut["items"] = items

if groups is not None:
    jsonOut["groups"] = groups

makeDirectories(a.OUTPUT_FILE)
writeJSON(a.OUTPUT_FILE, jsonOut)
