# -*- coding: utf-8 -*-

import argparse
import inspect
import os
import re
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.text_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-dir', dest="INPUT_DIR", default="path/to/data/", help="Input directory")
parser.add_argument('-keys', dest="KEYS", default="bird,crustacea,fish,flowers,insects_crawling,insects_flying,reptile,trees", help="List of keys")
parser.add_argument('-filter', dest="FILTER", default="valid>0&quality>0", help="Filter query")
parser.add_argument('-tmpl', dest="TEMPLATE", default="${title}", help="Template for printing")
parser.add_argument('-mkey', dest="META_KEY", default="filename", help="Key to match on in metadata file")
parser.add_argument('-skey', dest="SEGMENT_KEY", default="sourceFilename", help="Key to match on in segment file")
parser.add_argument('-format', dest="FORMAT", default="text", help="Either text or md")
a = parser.parse_args()

keys = [k.strip() for k in a.KEYS.strip().split(",")]

for key in keys:
    keyParts = key.split("_")
    metaKey = key if len(keyParts) < 2 else keyParts[0]
    metaFile = a.INPUT_DIR + "filtered_%s.csv" % metaKey
    segmentFile = a.INPUT_DIR + "segment_annotations_%s.csv" % key

    _, meta = readCsv(metaFile, verbose=False)
    _, segments = readCsv(segmentFile, verbose=False)

    if len(a.FILTER) > 0:
        segments = filterByQueryString(segments, a.FILTER)
        # print("%s segments after filtering" % len(segments))

    # filter out meta that isn't in sampledata
    ufilenames = set([s[a.SEGMENT_KEY] for s in segments])
    meta = [d for d in meta if d[a.META_KEY] in ufilenames]

    lookup = {}
    for d in meta:
        description = d["description"]
        linkMatch = re.search(r'href=[\'"]?([^\'" >]+)', description)
        url = "https://www.flickr.com/photos/biodivlibrary/%s/" % d["id"]
        if linkMatch:
            url = linkMatch.group(1)
            parts = description.split("<")
            description = parts[0].strip()

        if description in lookup:
            lookup[description].append(url)
        else:
            lookup[description] = [url]

    arr = []
    for description, urls in lookup.items():
        arr.append({
            "description": description,
            "urls": urls
        })
    arr = sorted(arr, key=lambda row: row["description"])

    keyTitle = key.title()
    if len(keyParts) > 1:
        keyTitle = keyParts[0].title() + f' ({keyParts[1].title()})'
    if a.FORMAT == "text":
        print("================")
        print(keyTitle)
        print("----------------")
        for row in arr:
            print(f'{row["description"]}')
            for url in row["urls"]:
                print(f' - {url}')
        print("\n")

    else:
        print(keyTitle)
        print("\n")
        for i, row in enumerate(arr):
            urlString = "(pages: "
            for j, url in enumerate(row["urls"]):
                if j > 0:
                    urlString += ", "
                urlString += f'[({j+1})]({url})'
            urlString += ")"
            print(f'{i+1}. {row["description"]} {urlString}')
        print("\n")
