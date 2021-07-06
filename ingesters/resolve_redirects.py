# -*- coding: utf-8 -*-

# python3 ingesters/resolve_redirects/

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
parser.add_argument('-delay', dest="DELAY", type=int, default=1, help="How many seconds to delay requests (to avoid rate limiting)?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output debug info")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

for i, row in enumerate(rows):
    url = row[a.URL_KEY]
    newURL = False
    if isinstance(url, str) and url != "":
        newURL = resolveRedirect(url)
        print(f' {url} -> {newURL}')
    if not newURL:
        print(f' Invalid URL: {newURL}')
        newURL = ""
    rows[i][a.NEW_URL_KEY] = newURL
    printProgress(i+1, rowCount)
    if a.DELAY > 0:
        time.sleep(a.DELAY)

if a.PROBE:
    sys.exit()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

if a.NEW_URL_KEY not in fields:
    fieldNames.append(a.NEW_URL_KEY)

print("Writing file...")
writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
