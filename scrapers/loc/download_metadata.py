# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
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
parser.add_argument('-in', dest="INPUT_FILES", default="output/loc/pd_audio/page_*.json", help="File pattern for json files downloaded from download_query.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/loc/pd_audio/items/%s.json", help="JSON output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-threads', dest="THREADS", type=int, default=4, help="How many concurrent requests?")
parser.add_argument('-delay', dest="DELAY", type=int, default=1, help="How many seconds to delay requests (to avoid rate limiting)?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILES)

# Make sure output dirs exist
if not a.PROBE:
    makeDirectories(a.OUTPUT_FILE)

def processItem(item):
    global a

    itemUrl = item["id"]

    # url must follow pattern: http://www.loc.gov/item/{item id}/
    urlPattern = re.compile(r"https?://www\.loc\.gov/item/([^/]+)/")
    match = urlPattern.match(itemUrl)

    # if url pattern does not match, check a.k.a.
    if not match and "aka" in item:
        for akaUrl in item["aka"]:
            match = urlPattern.match(akaUrl)
            if match:
                itemUrl = akaUrl
                break

    if not match:
        print("Could not find valid URL for %s" % itemUrl)
        return "error"

    itemId = match.group(1)
    filename = a.OUTPUT_FILE % itemId
    status = "error"

    if os.path.isfile(filename) and not a.OVERWRITE:
        return "exists"

    if a.PROBE:
        return "success"

    data = getJSONFromURL(itemUrl + "?fo=json")
    if data is not False:
        writeJSON(filename, data, verbose=True)
        status = "success"

    return status

print("Reading query data...")
items = []
for fn in filenames:
    items += readJSON(fn)
itemCount = len(items)
print("Read %s items" % itemCount)

# Don't do threading to avoid rate limit error
# print("Downloading metadata...")
# pool = ThreadPool(getThreadCount(a.THREADS))
# pool.map(processItem, items)
# pool.close()
# pool.join()
# print("Done.")

for i, item in enumerate(items):
    status = processItem(item)
    printProgress(i+1, itemCount)
    if status == "exists" or a.PROBE:
        continue
    elif status == "error":
        time.sleep(5)
    else:
        time.sleep(a.DELAY)
