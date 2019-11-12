# -*- coding: utf-8 -*-
import inspect
import os
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.collection_utils import *

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

def getLocItemData(a):
    fieldNames, files = readCsv(a.INPUT_FILE)
    filenames = getFilenames(a.INPUT_PAGES_FILES)

    filters = []
    if len(a.FILTER) > 0:
        filters = parseFilterString(a.FILTER.strip())

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
