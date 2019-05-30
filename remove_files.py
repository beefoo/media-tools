# -*- coding: utf-8 -*-

import argparse
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
import os
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/ia_politicaladarchive/", help="Input dir")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details")
a = parser.parse_args()

# get unique video files
print("Reading file...")
fieldNames, rows = readCsv(a.INPUT_FILE)
# rows = prependAll(rows, ("filename", a.MEDIA_DIRECTORY))

files = getFilenames(a.MEDIA_DIRECTORY + "*")

ufiles = set(row["filename"] for row in rows)
deleted = 0
kept = 0
for file in files:
    bfile = os.path.basename(file)
    if bfile not in ufiles:
        print("Deleting %s" % file)
        if not a.PROBE:
            os.remove(file)
        deleted += 1
    elif os.path.isfile(a.MEDIA_DIRECTORY + bfile):
        kept += 1
        print("Keep %s" % file)
print("Deleted %s files, kept %s files" % (deleted, kept))
