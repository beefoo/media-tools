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

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-query', dest="QUERY_URL", default="https://www.loc.gov/audio/?fa=access-restricted:false%7Conline-format:audio&q=%22No+known+restrictions%22+OR+%22No+known+copyright+restriction%22+OR+%22Library+is+not+aware+of+any+copyrights%22&st=gallery&fo=json", help="Query. See reference: https://libraryofcongress.github.io/data-exploration/")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/loc/pd_audio/page_%s.json", help="JSON output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-delay', dest="DELAY", type=int, default=1, help="How many seconds to delay requests (to avoid rate limiting)?")
a = parser.parse_args()

page = 1
firstPage = getJSONFromURL(a.QUERY_URL)
pages = int(firstPage["pagination"]["total"])
totalItems = int(firstPage["pagination"]["of"])
print("Found %s results in %s pages" % (totalItems, pages))

if a.PROBE:
    sys.exit()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

def processQueryUrl(p):
    global a
    url, filename, data = p

    if os.path.isfile(filename) and not a.OVERWRITE:
        return

    if data is None:
        data = getJSONFromURL(url)

    if data and "results" in data and data["results"]:
        writeJSON(filename, data["results"], verbose=True)

props = []

for i in range(pages):
    page = i + 1
    filename = a.OUTPUT_FILE % zeroPad(page, pages)
    url = a.QUERY_URL + "&sp=%s" % page
    data = None
    if page == 1:
        data = firstPage
    props.append((url, filename, data))

pageCount = len(props)
for i, p in enumerate(props):
    processQueryUrl(p)
    printProgress(i+1, pageCount)
    time.sleep(a.DELAY)

# pool = ThreadPool(getThreadCount(a.THREADS))
# results = pool.map(processQueryUrl, props)
# pool.close()
# pool.join()
# print("Done.")
