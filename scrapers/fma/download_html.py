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

# input
parser = argparse.ArgumentParser()
parser.add_argument('-url', dest="URL", default="https://freemusicarchive.org/search?music-filter-public-domain=1", help="URL to scrape")
parser.add_argument('-dir', dest="HTML_DIR", default="output/fma/page-%s.html", help="Directory to store raw html data")
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
makeDirectories([a.HTML_DIR])

if a.OVERWRITE:
    removeFiles(a.HTML_DIR % '*')

page = 1
zeroPadding = 4
nextUrl = a.URL
while True:

    filename = a.HTML_DIR % str(page).zfill(zeroPadding)
    fileExists = os.path.isfile(filename) and not a.OVERWRITE
    html = downloadFile(nextUrl, filename, headers, overwrite=a.OVERWRITE)
    # print(html)
    # break

    nextUrl = ""
    bs = BeautifulSoup(html, "html.parser")
    container = bs.find("div", {"class": "pagination-full"})

    if not container:
        break

    paginationLinks = container.find_all("a")

    if not paginationLinks or len(paginationLinks) < 1:
        break

    for link in paginationLinks:
        if link.string.strip().lower().startswith("next") and link.has_attr("href"):
            nextUrl = link.get("href").strip()
            break

    if len(nextUrl) < 1:
        break

    page += 1

    if not fileExists:
        time.sleep(1)

print("Done")
