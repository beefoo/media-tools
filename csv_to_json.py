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
parser.add_argument('-lists', dest="LISTS", default="", help="Comma-separated list of lists to output")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-sort', dest="SORT", default="", help="Sort string")
parser.add_argument('-replace', dest="REPLACE_STRING", default="", help="Query string of keys to rename, e.g. keyFind=keyReplace&key2Find=key2Replace")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit the number of results; -1 for all")
parser.add_argument('-light', dest="LIGHT", action="store_true", help="Output the data in a 'light' format")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/samples.json", help="Output json file")
a = parser.parse_args()
# Parse arguments

props = [p for p in a.PROPS.strip().split(",")]

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
if len(props) < 1:
    props = fieldNames
rowCount = len(rows)

for i, row in enumerate(rows):
    if "id" in row:
        rows[i]["id"] = str(row["id"])
    if "title" in row:
        rows[i]["title"] = str(row["title"])

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

if len(a.SORT) > 0:
    rows = sortByQueryString(rows, a.SORT)
    rowCount = len(rows)
    print("%s rows after sorting" % rowCount)

replaceKeys = {}
if len(a.REPLACE_STRING) > 0:
    replaceKeys = parseQueryString(a.REPLACE_STRING, doParseNumbers=False)

if a.LIMIT > 0 and len(rows) > a.LIMIT:
    rows = rows[:a.LIMIT]
    rowCount = len(rows)
    print("%s rows after limiting" % rowCount)

GROUPS = [p for p in a.GROUPS.strip().split(",")] if len(a.GROUPS) > 0 else []
groups = None
if len(GROUPS) > 0:
    groups = {}
    for groupKey in GROUPS:
        groupKeyNew = groupKey
        if groupKey in replaceKeys:
            groupKeyNew = replaceKeys[groupKey]
        groups[groupKeyNew] = sorted(unique([r[groupKey] for r in rows]))

LISTS = [p for p in a.LISTS.strip().split(",")] if len(a.LISTS) > 0 else []
for i, r in enumerate(rows):
    for listKey in LISTS:
        rows[i][listKey] = r[listKey].split(" | ")
if len(LISTS) > 0:
    if groups is None:
        groups = {}
    for groupKey in LISTS:
        groupKeyNew = groupKey
        if groupKey in replaceKeys:
            groupKeyNew = replaceKeys[groupKey]
        groups[groupKeyNew] = sorted(unique(flattenList([r[groupKey] for r in rows])))

items = []
for r in rows:
    item = {}
    for p in props:
        pnew = p
        if p in replaceKeys:
            pnew = replaceKeys[p]
        if p in GROUPS:
            item[pnew] = groups[pnew].index(r[p])
        elif p in LISTS:
            item[pnew] = [groups[pnew].index(value) for value in r[p]]
        else:
            item[pnew] = r[p]
    items.append(item)

for i, p in enumerate(props):
    if p in replaceKeys:
        props[i] = replaceKeys[p]

jsonOut = {}
if a.LIGHT:
    jsonOut["itemHeadings"] = props
    jrows = []
    for r in items:
        jrows.append([r[p] for p in props])
    jsonOut["items"] = jrows
else:
    jsonOut["items"] = items

if groups is not None:
    jsonOut["groups"] = groups

jsonOut["lists"] = LISTS

makeDirectories(a.OUTPUT_FILE)
writeJSON(a.OUTPUT_FILE, jsonOut)
