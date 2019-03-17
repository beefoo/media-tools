# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import shutil
import sys
import urllib

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/metadata.csv", help="Path to csv file")
parser.add_argument('-id', dest="ID_KEY", default="assetId", help="Key to retrieve identifier from")
parser.add_argument('-url', dest="URL", default="https://download.com/asset/%s.mp4", help="Url pattern")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/%s.mp4", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
a = parser.parse_args()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

# Get existing data
fieldNames, rows = readCsv(a.INPUT_FILE)
if "filename" not in fieldNames:
    fieldNames.append("filename")
fileCount = len(rows)

if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
    fileCount = len(rows)
    print("Found %s rows after filtering" % fileCount)

if a.LIMIT > 0:
    rows = rows[:a.LIMIT]

for i, row in enumerate(rows):
    url = a.URL % row[a.ID_KEY] if a.ID_KEY in row else False
    if not url:
        print("Could not find %s in row %s" % (a.ID_KEY, i+1))
        continue

    filepath = a.OUTPUT_DIR % row[a.ID_KEY]
    filename = os.path.basename(filepath)
    downloadBinaryFile(url, filepath, a.OVERWRITE)
    printProgress(i+1, fileCount)
