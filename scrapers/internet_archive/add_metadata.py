# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_ows-youtube_protest.csv", help="CSV output file")
parser.add_argument('-query', dest="QUERY", default="collection:(ows-youtube) AND mediatype:(movies) AND subject:(protest)", help="Query. See reference: https://archive.org/advancedsearch.php")
parser.add_argument('-keys', dest="ADD_KEYS", default="creator", help="List of keys to add")
parser.add_argument('-rows', dest="ROWS", default=100, type=int, help="Rows per page")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
QUERY = args.QUERY
ADD_KEYS = args.ADD_KEYS.strip().split(",")
ROWS = args.ROWS
OUTPUT_FILE = args.OUTPUT_FILE if len(args.OUTPUT_FILE) > 0 else INPUT_FILE

if not os.path.isfile(INPUT_FILE):
    print("Could not find %s" % INPUT_FILE)
    sys.exit()

# Get existing data
fieldNames, rows = readCsv(INPUT_FILE)
fieldNames = unionLists(fieldNames, ADD_KEYS)
rowCount = len(rows)

rows = addIndices(rows)
rowLookup = dict([(r["identifier"], r) for r in rows])

returnKeys = ["identifier"] + ADD_KEYS
returnKeysString = "".join(["&fl[]="+k for k in returnKeys])
url = "https://archive.org/advancedsearch.php?q=%s%s&rows=%s&output=json&save=yes" % (QUERY, returnKeysString, ROWS)
page = 1

firstPage = getJSONFromURL(url + "&page=%s" % page)
numFound = firstPage["response"]["numFound"]
pages = int(math.ceil(1.0*numFound/ROWS))
print("Found %s results in %s pages" % (numFound, pages))

pageRows = firstPage["response"]["docs"]

while len(pageRows) > 0:
    for row in pageRows:
        rowId = row["identifier"]
        if rowId in rowLookup:
            for key in ADD_KEYS:
                if key in row:
                    rowLookup[rowId][key] = row[key]
    page += 1
    if page > pages:
        break
    data = getJSONFromURL(url + "&page=%s" % page)
    pageRows = data["response"]["docs"]

rows = []
for key in rowLookup:
    rows.append(rowLookup[key])
rows = sorted(rows, key=lambda r: r["index"])
writeCsv(OUTPUT_FILE, rows, fieldNames)
