# -*- coding: utf-8 -*-

# Parse NDJSON files from Smithsonian Open Access Metadata on Github: https://github.com/Smithsonian/OpenAccess/tree/master/metadata/objects

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/*.txt", help="Text files that are in Newline-delimited JSON")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/si/objects.csv", help="Output file")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILE)
makeDirectories([a.OUTPUT_FILE])
fileCount = len(filenames)

rows = []
print("Reading rows...")
for i, fn in enumerate(filenames):
    rows += readLDJSON(fn)
    printProgress(i+1, fileCount)

rowCount = len(rows)
print(f'Found {rowCount} rows')

print("Parsing rows...")
invalidRows = 0
outRows = []
for i, row in enumerate(rows):
    if "content" not in row or "id" not in row:
        invalidRows += 1
        continue

    content = row["content"]
    if "freetext" not in content or "descriptiveNonRepeating" not in content or "indexedStructured" not in content:
        invalidRows += 1
        continue

    combined = list(content["descriptiveNonRepeating"].items()) + list(content["indexedStructured"].items()) + list(content["freetext"].items())

    outRow = {
        "id": row["id"]
    }

    for key, value in combined:
        if key in outRow:
            continue

        # take the first value in list
        if isinstance(value, list):
            value = value[0]

        if isNumber(value) or isinstance(value, str):
            outRow[key] = value
            continue

        # assume this is an object
        if not isinstance(value, dict):
            print('Could not parse value:')
            pprint(value)
            continue

        if "content" in value:
            outRow[key] = value["content"]
            continue

        for vkey, vvalue in value.items():
            if vkey in outRow:
                continue

            if isNumber(vvalue) or isinstance(vvalue, str):
                outRow[vkey] = vvalue
                continue

            if "type" in vvalue:
                vkey = vvalue["type"]
                if vkey in outRow:
                    continue

            if "content" in vvalue:
                outRow[vkey] = vvalue["content"]

    outRows.append(outRow)

    printProgress(i+1, rowCount)

outRowCount = len(outRows)
print(f'Found {outRowCount} valid rows')
print(f'Found {invalidRows} invalid rows')

if a.PROBE:
    sys.exit()


print("Collecting field names...")
fieldNames = ["id", "record_link", "title", "date", "object_type", "topic", "place", "name"]
for i, row in enumerate(outRows):
    for key in row:
        if key not in fieldNames:
            fieldNames.append(key)
    printProgress(i+1, outRowCount)

print("Writing file...")
writeCsv(a.OUTPUT_FILE, outRows, headings=fieldNames)
