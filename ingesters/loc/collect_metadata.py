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
from loclib import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="output/loc/pd_audio/items/*.json", help="File pattern for json files downloaded from download_metadata.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/loc/lc_pd_audio.csv", help="File to write data to")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-streaming', dest="ALLOW_STREAMING", action="store_true", help="Should we download streaming media if no download option is available?")
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
if not a.PROBE:
    makeDirectories(a.OUTPUT_FILE)

def readItem(fn):
    global a
    global rowLookup

    item = readJSON(fn)
    hasExistingData = rowLookup is not None

    if "item" not in item:
        print("No item meta in %s" % fn)
        return None

    itemMeta = item["item"]
    itemId, itemUrl = getLocItemId(itemMeta)
    if itemId is None or itemUrl is None:
        return None

    if not item or "resources" not in item or len(item["resources"]) < 1:
        print("No resources found for %s" % itemUrl)
        return None

    # ignore playlists
    if "number_playlist_qty" in item and len(item["number_playlist_qty"]) > 0:
        print("%s is a playlist; skipping..." % itemUrl)
        return None

    returnData = {}
    if hasExistingData and itemId in rowLookup:
        returnData = rowLookup[itemId]

    assetUrl = None
    downloadableAssetUrl = None
    # validTypes = [".mp3", ".mp4", ".wav", ".mov", ".avi", ".ogg", ".ogv", ".mkv", ".wma"]
    validTypes = [".mp3", ".mp4", ".wav", ".ogg", ".ogv", ".mkv", ".wma"]
    for resource in item["resources"]:
        if "files" in resource:
            for rf in resource["files"]:
                for rff in rf:
                    if "download" in rff:
                        assetUrl = rff["download"]
                        downloadableAssetUrl = assetUrl
                        break
                    # if there's no download option, take the streaming option
                    if a.ALLOW_STREAMING and "derivatives" in rff and len(rff["derivatives"]) > 0 and assetUrl is None:
                        for deriv in rff["derivatives"]:
                            if "derivativeUrl" in deriv:
                                derivativeUrl = deriv["derivativeUrl"]
                                if derivativeUrl:
                                    ext = getFileExt(derivativeUrl)
                                    if ext in validTypes:
                                        assetUrl = derivativeUrl
                                        break
                    elif a.ALLOW_STREAMING and "url" in rff and assetUrl is None:
                        ext = getFileExt(rff["url"])
                        if ext in validTypes:
                            assetUrl = rff["url"]
                            break

                if downloadableAssetUrl is not None:
                    break

        if downloadableAssetUrl is not None:
            break

    if assetUrl is None:
        print("Could not find download asset for %s" % fn)
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
