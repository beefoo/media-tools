# -*- coding: utf-8 -*-

import argparse
import flickr_api
import inspect
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import shutil
import subprocess
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-key', dest="API_KEY", default="", help="Your Flickr API key")
parser.add_argument('-secret', dest="API_SECRET", default="", help="Your Flickr API secret")
parser.add_argument('-user', dest="USER", default="biodivlibrary", help="Name of user")
parser.add_argument('-props', dest="PROPERTY_LIST", default="id,title,description,license,views,tags,taken", help="List of properties to retrieve")
parser.add_argument('-sizes', dest="SIZE_LIST", default="Small,Medium,Large,Original", help="List of image sizes to retrieve: https://www.flickr.com/services/api/flickr.photos.getSizes.html")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/biodivlibrary_page_%s.csv", help="Output file")
parser.add_argument('-page', dest="START_PAGE", default=1, type=int, help="Page to start on")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
a = parser.parse_args()

PROPS = [p.strip() for p in a.PROPERTY_LIST.split(",")]
SIZE_LIST = [p.strip() for p in a.SIZE_LIST.split(",")]
IS_MULTI_OUTPUT = ("%" in a.OUTPUT_FILE)

flickr_api.set_keys(api_key = a.API_KEY, api_secret = a.API_SECRET)

# Make sure output dirs exist
makeDirectories([a.OUTPUT_FILE])

user = flickr_api.Person.findByUserName(a.USER)
rows = []
fieldNames = PROPS[:]
for sizeLabel in SIZE_LIST:
    fieldNames += ["width%s" % sizeLabel, "height%s" % sizeLabel, "imageUrl%s" % sizeLabel, "sourceUrl%s" % sizeLabel]
rowLookup = None

if not a.OVERWRITE and os.path.isfile(a.OUTPUT_FILE) and not IS_MULTI_OUTPUT:
    fieldNames, rows = readCsv(a.OUTPUT_FILE)
    rowLookup = createLookup(rows, "id")

userInfo = user.getInfo()
print("Downloading data for %s photos" % userInfo["photos_info"]["count"])
if a.PROBE:
    sys.exit()

page = a.START_PAGE
errors = []
while True:
    print("Retrieving page %s..." % page)
    outputFile = a.OUTPUT_FILE
    if IS_MULTI_OUTPUT:
        rows = []
        outputFile = outputFile % page
        if os.path.isfile(outputFile) and not a.OVERWRITE:
            page += 1
            continue

    photos = user.getPublicPhotos(per_page = 500, page=page)
    page += 1

    if not photos or len(photos) < 1:
        break

    photoCount = len(photos)
    print("%s photos found" % photoCount)

    for i, photo in enumerate(photos):

        try:
            info = photo.getInfo()
            sizes = photo.getSizes()
        except flickr_api.flickrerrors.FlickrServerError:
            error = "Error for photo %s on page %s" % (i+1, page-1)
            print(error)
            errors.append(error)
            time.sleep(5)
            continue

        printProgress(i+1, photoCount)

        if rowLookup is not None and info["id"] in rowLookup:
            continue

        meta = {}
        for p in PROPS:
            value = info[p]
            if p == "tags":
                value = " | ".join([tag["text"] for tag in value])
            elif p == "description":
                value = value.replace("\n", " ")
            meta[p] = value

        # print(sizes)
        for key, size in sizes.items():
            if size["label"] in SIZE_LIST:
                meta["width%s" % size["label"]] = size["width"]
                meta["height%s" % size["label"]] = size["height"]
                meta["imageUrl%s" % size["label"]] = size["source"]
                meta["sourceUrl%s" % size["label"]] = size["url"]

        rows.append(meta)

    writeCsv(outputFile, rows, fieldNames)

pprint(errors)
print("Done.")
