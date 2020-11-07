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
parser.add_argument('-asset', dest="ASSET_URL", default="", help="Key to retrieve asset url from")
parser.add_argument('-id', dest="ID_KEY", default="assetId", help="Key to retrieve identifier from")
parser.add_argument('-url', dest="URL_PATTERN", default="https://download.com/asset/%s.mp4", help="Url pattern if applicable")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-sort', dest="SORT", default="", help="Query string to sort by")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output debug info")
a = parser.parse_args()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

filenames = [a.INPUT_FILE]
if "*" in a.INPUT_FILE:
    filenames = getFilenames(a.INPUT_FILE)
    filenames = sorted(filenames)
    print("Found %s files" % len(filenames))

downloads = 0
nofileCount = 0
for filename in filenames:

    if a.LIMIT > 0 and downloads >= a.LIMIT:
        print("Reached download limit.")
        break

    # Get existing data
    fieldNames, rows = readCsv(filename)
    if "filename" not in fieldNames:
        print("Filename not provided; will use ID for this")
    fileCount = len(rows)

    if len(a.SORT) > 0:
        rows = sortByQueryString(rows, a.SORT)
        print("Sorted: %s" % a.SORT)

    if len(a.FILTER) > 0:
        rows = filterByQueryString(rows, a.FILTER)
        fileCount = len(rows)
        print("Found %s rows after filtering" % fileCount)

    for i, row in enumerate(rows):
        url = ""
        if len(a.ASSET_URL) < 1:
            url = a.URL_PATTERN % row[a.ID_KEY] if a.ID_KEY in row else ""
        else:
            url = row[a.ASSET_URL]

        if len(url) < 1:
            print("Could not find url for item %s" % row[a.ID_KEY])
            continue

        ext = getFileExt(url)
        filename = row[a.ID_KEY] + ext if "filename" not in row else row["filename"]
        filepath = a.OUTPUT_DIR + filename
        if a.PROBE:
            if not os.path.isfile(filepath):
                nofileCount += 1
                downloads += 1
        else:
            downloadBinaryFile(url, filepath, a.OVERWRITE)
            downloads += 1
            total = fileCount
            if a.LIMIT > 0:
                total = a.LIMIT
            printProgress(i+1, total)

        if a.LIMIT > 0 and downloads >= a.LIMIT:
            break

if a.PROBE:
    print("%s files to download" % nofileCount)
