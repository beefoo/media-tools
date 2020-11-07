# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from PIL import Image
from pprint import pprint
import sys

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/images.csv", help="Input file pattern")
parser.add_argument('-dir', dest="INPUT_DIR", default="tmp/", help="Directory of media files")
parser.add_argument('-key', dest="FILENAME_KEY", default="filename", help="The column with the filename")
parser.add_argument('-nkey', dest="NEW_KEY", default="is_valid", help="The new column to add")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show the stats")
a = parser.parse_args()

fieldNames, rows = readCsv(a.INPUT_FILE)

if a.NEW_KEY not in fieldNames:
    fieldNames.append(a.NEW_KEY)

valid = 0
invalid = 0
for i, row in enumerate(rows):
    w = 0
    h = 0
    try:
        im = Image.open(a.INPUT_DIR + row[a.FILENAME_KEY])
        w, h = im.size
    except IOError:
        print("IO error: %s" % a.INPUT_DIR + row[a.FILENAME_KEY])
    is_valid = w > 0 and h > 0
    rows[i][a.NEW_KEY] = is_valid
    if is_valid > 0:
        valid += 1
    else:
        invalid += 1

print("%s valid, %s invalid" % (valid, invalid))

if not a.PROBE:
    writeCsv(a.INPUT_FILE, rows, headings=fieldNames)
