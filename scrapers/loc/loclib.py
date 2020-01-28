# -*- coding: utf-8 -*-
import inspect
import os
from pprint import pprint
import re
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

def isValidFile(f, filters, itemLookup):
    valid = True
    if str(f["id"]) in itemLookup:
        if len(filters) > 0:
            metadata = itemLookup[str(f["id"])]
            for key, value, mode in filters:
                if key not in metadata:
                    valid = False
                    break
                if value not in metadata[key]:
                    valid = False
                    break
    else:
        valid = False

    return valid

def getLocItemId(apiItem):
    itemUrl = apiItem["id"]

    # url must follow pattern: http://www.loc.gov/item/{item id}/
    urlPattern = re.compile(r"https?://www\.loc\.gov/item/([^/]+)/")
    match = urlPattern.match(itemUrl)

    # if url pattern does not match, check a.k.a.
    if not match and "aka" in apiItem:
        for akaUrl in apiItem["aka"]:
            match = urlPattern.match(akaUrl)
            if match:
                itemUrl = akaUrl
                break

    if not match:
        print("Could not find valid URL for %s" % itemUrl)
        return (None, None)

    itemId = match.group(1)
    return (itemId, itemUrl)

def getLocItemData(a):
    fieldNames, files = readCsv(a.INPUT_FILE)
    filenames = getFilenames(a.INPUT_PAGES_FILES)

    filters = []
    if len(a.FILTER) > 0:
        filters = parseFilterString(a.FILTER.strip())

    for i, f in enumerate(files):
        files[i]['duration'] = f['duration'] if f['duration'] != '' else 0
        files[i]['hasAudio'] = f['hasAudio'] if f['hasAudio'] != '' else 0

    # Filter out invalid files
    files = filterWhere(files, [("duration", 0, ">"), ("hasAudio", 0, ">")])
    fileCount = len(files)

    items = []
    for fn in filenames:
        items += readJSON(fn)
    itemCount = len(items)
    print("Read %s items" % itemCount)

    itemLookup = {}
    for i, item in enumerate(items):
        itemUrl = item["id"]
        itemId = itemUrl.strip("/").split("/")[-1]
        itemLookup[str(itemId)] = item

    print("Total items retrieved from query: %s" % itemCount)
    print("Total items with valid audio: %s (%s%%)" % (fileCount, round(1.0*fileCount / itemCount * 100.0, 2)))

    files = [f for f in files if isValidFile(f, filters, itemLookup)]
    fileCount = len(files)
    print("Total items after filtering: %s (%s%%)" % (fileCount, round(1.0*fileCount / itemCount * 100.0, 2)))

    return (files, fieldNames, itemLookup, itemCount)
