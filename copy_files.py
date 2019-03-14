# -*- coding: utf-8 -*-

import argparse
from lib.collection_utils import *
from lib.io_utils import *
import os
import re
import shutil
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sampler/double-bass.csv", help="Input file")
parser.add_argument('-dir', dest="INPUT_DIR", default="media/downloads/double-bass/", help="Input file")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-out', dest="OUT_DIR", default="media/sampler/double-bass/", help="Output directory")
a = parser.parse_args()

# get files
fieldNames, rows = readCsv(a.INPUT_FILE)
makeDirectories([a.OUT_DIR])

# filter if necessary
if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
rowCount = len(rows)

for row in rows:
    fileFrom = a.INPUT_DIR + row["filename"]
    fileTo = a.OUT_DIR + row["filename"]
    shutil.copyfile(fileFrom, fileTo)
print("Done.")
