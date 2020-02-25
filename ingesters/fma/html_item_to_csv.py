# -*- coding: utf-8 -*-

import argparse
from bs4 import BeautifulSoup
import inspect
import math
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.collection_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument("-in", dest="INPUT_FILE", default="output/fma/items/*.html", help="Input file pattern")
parser.add_argument("-out", dest="OUTPUT_FILE", default="output/fma_items.csv", help="Output csv file")
parser.add_argument("-threads", dest="THREADS", default=4, type=int, help="Number of concurrent threads, -1 for all available")
a = parser.parse_args()

fieldNames = []

# Make sure output dirs exist
makeDirectories([a.OUTPUT_FILE])
filenames = getFilenames(a.INPUT_FILE)
# filenames = filenames[:10]

def parseHTMLFile(fn):
    contents = ""
    with open(fn, "r", encoding="utf8", errors="replace") as f:
        contents = f.read()

    if len(contents) < 1:
        print("%s is empty" % fn)
        return None

    bs = BeautifulSoup(contents, "html.parser")
    item = {
        "id": getBasename(fn),
        "date": "",
        "license": ""
    }

    # Look for recorded date in track info
    statLabels = bs.find_all("span", {"class": "stathd"})
    for label in statLabels:
        labelText = label.string.strip().lower()
        if "recorded" not in labelText:
            continue
        labelParent = label.parent
        statValue = labelParent.find("b")
        if statValue:
            item["date"] = statValue.string.strip()
            break
        statValue = labelParent.find("div", {"class": "stat-item"})
        if statValue:
            item["date"] = statValue.string.strip()
            break

    # Look for license
    licenseLink = bs.find("a", {"rel": "license"})
    if licenseLink:
        item["license"] = licenseLink.get("href").strip()

    return item

print("Parsing %s files..." % len(filenames))
pool = ThreadPool(a.THREADS)
results = pool.map(parseHTMLFile, filenames)
pool.close()
pool.join()

items = [item for item in results if item is not None]
items = sorted(items, key=lambda item: item["id"])

writeCsv(a.OUTPUT_FILE, items, ["id", "date", "license"])
