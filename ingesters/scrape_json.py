# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-url', dest="URL", default="", help="Base URL for GET requests")
parser.add_argument('-rkey', dest="RESULTS_KEY", default="results.content", help="Key that contains the list of results")
parser.add_argument('-tkey', dest="TOTAL_KEY", default="results.count", help="Key that has the total amount of items")
parser.add_argument('-npkey', dest="NEXT_PAGE_KEY", default="results.nextCursorMark", help="Key that contains the next page value")
parser.add_argument('-pp', dest="PAGE_PARAMETER", default="initialCursorMark", help="Parameter to send the next page value in")
parser.add_argument('-cp', dest="COUNT_PARAMETER", default="count", help="Parameter to send the results per page")
parser.add_argument('-count', dest="COUNT", default=50, type=int, help="Results per page")
parser.add_argument('-dir', dest="JSON_DIR", default="tmp/json/page.%s.json", help="Directory to save JSON responses")
parser.add_argument('-skeys', dest="KEYS_TO_SAVE", default="assetId", help="Comma separated list of keys to save")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/scrapeResults.csv", help="File to write results to")
a = parser.parse_args()

KEYS_TO_SAVE = a.KEYS_TO_SAVE.split(",")

# Make sure output dirs exist
makeDirectories(a.JSON_DIR)

if len(a.URL) < 1:
    print("Please enter a URL")

def getItemData(a, data, keys):
    itemData = getNestedValue(data, a.RESULTS_KEY)
    returnData = []
    if itemData and len(itemData) > 0:
        for item in itemData:
            d = {}
            for k in keys:
                d[k] = replaceWhitespace(item[k]) if k in item else ""
            returnData.append(d)
    return returnData

def getPageData(a, page, param=None):
    # Retrieve first page data
    pageFilename = a.JSON_DIR % str(page)
    pageData = {}
    if not os.path.isfile(pageFilename) or a.OVERWRITE:
        url = a.URL + "&" + a.COUNT_PARAMETER + "=" + str(a.COUNT)
        if param is not None:
            url += "&" + a.PAGE_PARAMETER + "=" + str(param)
        pageData = getJSONFromURL(url)
        writeJSON(pageFilename, pageData)
    else:
        pageData = readJSON(pageFilename)

    return pageData

firstPageData = getPageData(a, 1)
totalCount = int(getNestedValue(firstPageData, a.TOTAL_KEY))
pages = ceilInt(1.0 * totalCount / a.COUNT) - 1 # exclude the first page
print("Found %s results in %s pages" % (totalCount, pages))

nextPageValue = getNestedValue(firstPageData, a.NEXT_PAGE_KEY)
nextPageValue = nextPageValue.replace("+", "%2B")
dataToSave = getItemData(a, firstPageData, KEYS_TO_SAVE)

for i in range(pages):
    page = i + 2
    data = getPageData(a, page, param=nextPageValue)
    dataToSave += getItemData(a, data, KEYS_TO_SAVE)
    nextPageValue = getNestedValue(data, a.NEXT_PAGE_KEY)
    nextPageValue = nextPageValue.replace("+", "%2B")

writeCsv(a.OUTPUT_FILE, dataToSave, KEYS_TO_SAVE)
