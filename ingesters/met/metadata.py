# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import os
from pprint import pprint
import re
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/MetObjects.csv", help="CSV file downloaded from https://github.com/metmuseum/openaccess")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/met/objects/%s.json", help="JSON output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-delay', dest="DELAY", type=int, default=1, help="How many seconds to delay requests (to avoid rate limiting)?")
a = parser.parse_args()

fieldNames, items = readCsv(a.INPUT_FILE)
itemCount = len(items)

# Make sure output dirs exist
if not a.PROBE:
    makeDirectories(a.OUTPUT_FILE)

def processItem(item):
    global a

    if "Object ID" not in item:
        return "error"

    itemId = item["Object ID"]

    if itemId == "":
        return "error"

    filename = a.OUTPUT_FILE % itemId
    status = "error"

    if os.path.isfile(filename) and not a.OVERWRITE:
        return "exists"

    if a.PROBE:
        return "success"

    itemUrl = "https://collectionapi.metmuseum.org/public/collection/v1/objects/%s" % itemId
    data = getJSONFromURL(itemUrl)
    if data is not False:
        writeJSON(filename, data, verbose=True)
        status = "success"

    return status

for i, item in enumerate(items):
    status = processItem(item)
    printProgress(i+1, itemCount)
    if status == "exists" or a.PROBE:
        continue
    elif status == "error":
        if a.PROBE:
            print("Error for row: %s" % (i+1))
        time.sleep(5)
    else:
        time.sleep(a.DELAY)
