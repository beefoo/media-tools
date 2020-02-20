# -*- coding: utf-8 -*-

import argparse
import os
import re
import shutil
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sampler/double-bass.csv", help="Input file")
parser.add_argument('-dir', dest="INPUT_DIR", default="media/downloads/double-bass/", help="Input file")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-out', dest="OUT_DIR", default="media/sampler/double-bass/", help="Output directory")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output details?")
a = parser.parse_args()

# get files
fieldNames, rows = readCsv(a.INPUT_FILE)

# filter if necessary
if len(a.FILTER) > 0:
    rows = filterByQueryString(rows, a.FILTER)
rowCount = len(rows)

filenames = unique([row["filename"] for row in rows])
print("%s files to move" % len(filenames))
if a.PROBE:
    sys.exit()

makeDirectories([a.OUT_DIR])

for fn in filenames:
    fileFrom = a.INPUT_DIR + fn
    fileTo = a.OUT_DIR + fn
    shutil.copyfile(fileFrom, fileTo)

print("Done.")
