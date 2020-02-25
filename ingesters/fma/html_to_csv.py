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
parser.add_argument("-in", dest="INPUT_FILE", default="output/fma/page-*.html", help="Input file pattern")
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
        return []

    bs = BeautifulSoup(contents, "html.parser")
    container = bs.find("div", {"class": "playlist"})

    if not container:
        print("No items in %s" % fn)
        return []

    results = container.find_all("div", {"class": "play-item"})
    items = []

    for row in results:
        item = {}

        # id
        item["id"] = row.get("class")[-1].replace("tid-", "fma-")
        item["filename"] = item["id"] + ".mp3"

        # contributors
        artist = row.find("span", {"class", "ptxt-artist"})
        if artist:
            artistLink = artist.find("a")
            if artistLink:
                item["contributorsUrls"] = artistLink.get("href").strip()
                item["contributors"] = artistLink.string.strip()
            else:
                item["contributors"] = artist.string.strip()

        # title
        title = row.find("span", {"class", "ptxt-track"})
        if title:
            titleLink = title.find("a")
            if titleLink:
                item["url"] = titleLink.get("href").strip()
                item["title"] = titleLink.string.strip()
            else:
                item["title"] = title.string.strip()

        # asset
        assetLink = row.find("a", {"class", "icn-arrow"})
        if assetLink:
            item["assetUrl"] = assetLink.get("href")

        # subjects
        genres = row.find("span", {"class", "ptxt-genre"})
        if genres:
            genreLinks = genres.find_all("a")
            genreStrings = [link.string.strip() for link in genreLinks]
            if len(genreStrings) > 0:
                item["subjects"] = " | ".join(genreStrings)

        items.append(item)
    return items

print("Parsing %s files..." % len(filenames))
pool = ThreadPool(a.THREADS)
results = pool.map(parseHTMLFile, filenames)
pool.close()
pool.join()

items = flattenList(results)
# items = sorted(items, key=lambda item: item["title"])

writeCsv(a.OUTPUT_FILE, items, ["id", "filename", "url", "title", "assetUrl", "contributors", "contributorsUrls", "subjects"])
