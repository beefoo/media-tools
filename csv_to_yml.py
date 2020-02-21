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
parser.add_argument('-key', dest="FILENAME_KEY", default="id", help="Key to use as a filename")
parser.add_argument('-props', dest="PROPS", default="", help="Comma-separated list of properties to output; leave empty for all")
parser.add_argument('-filter', dest="FILTER", default="", help="Filter string")
parser.add_argument('-replace', dest="REPLACE_STRING", default="", help="Query string of keys to rename, e.g. keyFind=keyReplace&key2Find=key2Replace")
parser.add_argument('-add', dest="ADD_VALUES", default="", help="Query string to add more values, e.g. key1=value1&key2=value2")
parser.add_argument('-prepend', dest="PREPEND_STRING", default="---", help="Prepend with this string")
parser.add_argument('-append', dest="APPEND_STRING", default="---", help="Append with this string")
parser.add_argument('-appendf', dest="APPEND_FILE", default="", help="Append with this file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/%s.md", help="Output yaml files")
a = parser.parse_args()
# Parse arguments

PROPS = [p for p in a.PROPS.strip().split(",")]

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
if len(PROPS) < 1:
    PROPS = fieldNames
rowCount = len(rows)
propCount = len(PROPS)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    rowCount = len(rows)
    print("%s rows after filtering" % rowCount)

replaceKeys = {}
if len(a.REPLACE_STRING) > 0:
    replaceKeys = parseQueryString(a.REPLACE_STRING, parseNumbers=False)

addValues = []
if len(a.ADD_VALUES) > 0:
    addValues = parseQueryString(a.ADD_VALUES, parseNumbers=True)
    addValues = [{"key": key, "value": addValues[key]} for key in addValues]

prependLines = []
if len(a.PREPEND_STRING) > 0:
    prependLines.append(a.PREPEND_STRING)

appendLines = []
if len(a.APPEND_STRING) > 0:
    appendLines.append(a.APPEND_STRING)

if len(a.APPEND_FILE) > 0 and os.path.isfile(a.APPEND_FILE):
    with open(a.APPEND_FILE, "r", encoding="utf8") as f:
        appendLines += [line.rstrip() for line in f]

makeDirectories(a.OUTPUT_FILE)

for row in rows:
    lines = prependLines[:]
    values = [{"key": p, "value": row[p]} for p in PROPS] + addValues[:]

    for v in values:
        keynew = v["key"]
        if keynew in replaceKeys:
            keynew = replaceKeys[keynew]
        value = v["value"]
        if not isNumber(value):
            value = str(value)
            value = value.replace('"', '\\"')
            value = '"' + value + '"'
        lines.append("%s: %s" % (keynew, value))

    if len(appendLines) > 0:
        lines += appendLines

    filenameOut = a.OUTPUT_FILE % row[a.FILENAME_KEY]
    with open(filenameOut, "w", encoding="utf8") as f:
        f.write('\n'.join(lines))
        print("Wrote to %s" % filenameOut)

print("Done.")
