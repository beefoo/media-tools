# -*- coding: utf-8 -*-

import argparse
from bs4 import BeautifulSoup
import inspect
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
parser.add_argument('-in', dest="INPUT_FILE", default="output/fma_items.csv", help="Input csv file from html_to_csv.py")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/fma/items/%s.html", help="Directory to store raw html data")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
a = parser.parse_args()

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
}

# Make sure output dirs exist
makeDirectories([a.OUTPUT_FILE])

if a.OVERWRITE:
    removeFiles(a.OUTPUT_FILE % '*')

fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

for i, row in enumerate(rows):

    if "url" in row and len(row["url"]) > 0:
        filename = a.OUTPUT_FILE % row["id"]
        html = downloadFile(row["url"], filename, headers, overwrite=a.OVERWRITE)

    printProgress(i+1, rowCount)
