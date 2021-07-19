# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys
import time

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
parser.add_argument('-in', dest="INPUT_FILE", default="output/si/objects.csv", help="Path to .csv file generated from ndjson_to_csv.py")
parser.add_argument('-json', dest="JSON_FILES", default="output/si/objects/{id}.json", help="JSON files generated from download_item_metadata.py")
parser.add_argument('-fields', dest="FIELDS", default="provenance,dimensions,description,images", help="List of fields to add from json")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Path to output file; leave blank to update input file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
fields, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

newFields = [f.strip() for f in a.FIELDS.split(",")]
for field in newFields:
    if field not in fields and field not in ("images"):
        fields.append(field)
    else:
        print(f'Info: {field} already exists in {a.INPUT_FILE}')

for i, row in enumerate(rows):
    filename = a.JSON_FILES.format(**row)
    jsonData = readJSON(filename)
    if "object" not in jsonData:
        continue
    jsonObject = jsonData["object"]
    for field in newFields:
        if field not in jsonObject:
            continue
        value = jsonObject[field]
        if not value:
            continue
        if isinstance(value, list):
            value = value[0]
        # special case for images
        if field == "images":
            for key in value:
                imgField = f'image_{key}'
                rows[i][imgField] = value[key]['url']
                if imgField not in fields:
                    fields.append(imgField)
            continue
        if not isinstance(value, (str, int, float)):
            print(f'Warning: invalid type for {field} in {filename}:')
            print(value)
            continue
        rows[i][field] = value

    printProgress(i+1, rowCount)

if a.PROBE:
    sys.exit()

makeDirectories([OUTPUT_FILE])
writeCsv(OUTPUT_FILE, rows, headings=fields)
