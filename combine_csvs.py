# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/*.csv", help="Input csv files")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/combined.csv", help="Output csv file")
a = parser.parse_args()
# Parse arguments

filenames = getFilenames(a.INPUT_FILE)
totalFiles = len(filenames)

fieldNames = []
rows = []
print("Reading files...")
for i, fn in enumerate(filenames):
    # Read files
    _fieldNames, _rows = readCsv(fn)
    fieldNames += _fieldNames
    rows += _rows
    printProgress(i+1, totalFiles)

fieldNames = sorted(unique(fieldNames))

makeDirectories(a.OUTPUT_FILE)
writeCsv(a.OUTPUT_FILE, rows, headings=fieldNames)
