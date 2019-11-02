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
parser.add_argument('-in', dest="INPUT_FILES", default="output/loc/pd_audio/items/*.json", help="File pattern for json files downloaded from download_metadata.py")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/loc/pd_audio/audio/", help="Directory to output files")
parser.add_argument('-dout', dest="OUTPUT_DATA_FILE", default="tmp/loc/lc_pd_audio.csv", help="File to write data to")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing media?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-threads', dest="THREADS", type=int, default=4, help="How many concurrent requests?")
parser.add_argument('-delay', dest="DELAY", type=int, default=1, help="How many seconds to delay requests (to avoid rate limiting)?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILES)

if a.PROBE:
    sys.exit()

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

def processItem(fn):
    global a

    item = readJSON(fn)
    if not item or "resources" not in item or len(item["resources"]) < 1:
        return

    resource = item["resources"][0]

    if os.path.isfile(filename) and not a.OVERWRITE:
        return "exists"

    data = getJSONFromURL(itemUrl + "?fo=json")
    if data is not False:
        writeJSON(filename, data, verbose=True)
        status = "success"

    return status

print("Downloading media...")
pool = ThreadPool(getThreadCount(a.THREADS))
pool.map(processItem, filenames)
pool.close()
pool.join()
print("Done.")
