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
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/loc/lc_pd_audio.csv", help="File to write data to")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-threads', dest="THREADS", type=int, default=4, help="How many concurrent requests?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILES)
addFieldnames = ["id", "url", "assetUrl", "filename", "title", "contributors", "date", "subjects"]
fieldNames = addFieldnames[:]
rows = []
rowLookup = None

if not a.OVERWRITE and os.path.isfile(a.OUTPUT_FILE):
    print("Existing file found.")
    existingFieldNames, rows = readCsv(a.OUTPUT_FILE)
    fieldNames = unionLists(addFieldnames, existingFieldNames)
    rowLookup = createLookup(rows, "id")

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

def readItem(fn):
    global a
    global rowLookup

    item = readJSON(fn)
    hasExistingData = rowLookup is not None

    if not item or "resources" not in item or len(item["resources"]) < 1:
        return None

    itemMeta = item["item"]
    itemUrl = itemMeta["id"]
    itemId = itemUrl.strip("/").split("/")[-1]

    returnData = {}
    if hasExistingData and itemId in rowLookup:
        returnData = rowLookup[itemId]

    assetUrl = None
    for resource in item["resources"]:
        if "files" in resource:
            for rf in resource["files"]:
                for rff in rf:
                    if "download" in rff:
                        assetUrl = rff["download"]
                        break
                if assetUrl is not None:
                    break
        if assetUrl is not None:
            break

    if assetUrl is None:
        print("Could not find download asset for %s" % itemId)
        return None

    if assetUrl.startswith('//'):
        assetUrl = "https:" + assetUrl

    fileExt = getFileExt(assetUrl)
    destFn = itemId + fileExt
    contributors = [] if "contributor_names" not in itemMeta or len(itemMeta["contributor_names"]) < 1 else itemMeta["contributor_names"]
    contributors = " | ".join(contributors)
    date = "" if "date" not in itemMeta else itemMeta["date"]
    subjects = [] if "subject" not in itemMeta or len(itemMeta["subject"]) < 1 else itemMeta["subject"]
    subjects = " | ".join(subjects)
    newData = {
        "id": itemId,
        "url": itemUrl,
        "assetUrl": assetUrl,
        "filename": destFn,
        "title": itemMeta["title"],
        "contributors": contributors,
        "date": date,
        "subjects": subjects
    }
    returnData.update(newData)
    return returnData

print("Reading metadata...")
pool = ThreadPool(getThreadCount(a.THREADS))
rows = pool.map(readItem, filenames)
pool.close()
pool.join()

# Filter out invalid data
rows = [row for row in rows if row is not None]
print("Found %s valid items with assets" % len(rows))

# print(fieldNames)

if a.PROBE:
    sys.exit()

# fieldNames.remove('contributor')

writeCsv(a.OUTPUT_FILE, rows, headings=fieldNames)
