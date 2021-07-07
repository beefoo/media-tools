# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/metadata.csv", help="Path to csv file")
parser.add_argument('-url', dest="URL_KEY", default="record_link", help="Key to retrieve url from")
parser.add_argument('-new', dest="NEW_URL_KEY", default="resolved_url", help="New key to store resolved URL")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Path to csv file; leave blank to update INPUT_FILE")
parser.add_argument('-delay', dest="DELAY", type=float, default=0.25, help="How many seconds to delay requests (to avoid rate limiting)?")
parser.add_argument('-progressive', dest="PROGRESSIVE_DOWNLOAD", action="store_true", help="Save results as you get them?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing values?")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

if a.NEW_URL_KEY not in fieldNames:
    fieldNames.append(a.NEW_URL_KEY)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

for i, row in enumerate(rows):
    url = row[a.URL_KEY]
    existingValue = row[a.NEW_URL_KEY] if a.NEW_URL_KEY in row else ""
    newURL = False
    if existingValue != "" and not a.OVERWRITE:
        continue
    if isinstance(url, str) and url != "":
        newURL = resolveRedirect(url)
        print(f' {url} -> {newURL}')
    if not newURL:
        print(f' Invalid URL: {newURL}')
        newURL = ""
    rows[i][a.NEW_URL_KEY] = newURL
    if a.PROGRESSIVE_DOWNLOAD:
        writeCsv(OUTPUT_FILE, rows, headings=fieldNames, verbose=False)
    printProgress(i+1, rowCount)
    if a.DELAY > 0:
        time.sleep(a.DELAY)

if not a.PROGRESSIVE_DOWNLOAD:
    print("Writing file...")
    writeCsv(OUTPUT_FILE, rows, headings=fieldNames)

print("Done.")
