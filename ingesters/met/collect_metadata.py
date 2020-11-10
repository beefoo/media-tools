# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import os
from pprint import pprint
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/objects.csv", help="Input .csv file with obj ids")
parser.add_argument('-fields', dest="FIELD_LIST", default="primaryImage,primaryImageSmall", help="Fields to add")
parser.add_argument('-objs', dest="OBJECTS", default="path/to/objects/%s.json", help="File pattern for json files downloaded from metadata.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="File to write data to; blank to update input file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
a = parser.parse_args()

fieldNames, items = readCsv(a.INPUT_FILE)
itemCount = len(items)

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

# Make sure output dirs exist
if not a.PROBE:
    makeDirectories(OUTPUT_FILE)

addFieldnames = [field.strip() for field in a.FIELD_LIST.split(",")]
fieldNames = unionLists(fieldNames, addFieldnames)

for i, item in enumerate(items):
    id = item["Object ID"]
    objFile = a.OBJECTS % id
    if os.path.isfile(objFile):
        data = readJSON(objFile)
        for field in addFieldnames:
            if field in data:
                items[i][field] = data[field]
            else:
                print("Field %s not found in %s" % (field, id))
    else:
        print("No file found for %s" % objFile)
    printProgress(i+1, itemCount)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, items, headings=fieldNames)
