# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/items.csv", help="Input file")
parser.add_argument('-fkey', dest="FILENAME_KEY", default="filename", help="Filename key")
parser.add_argument('-dir', dest="FILE_DIRECTORY", default="path/to/files/", help="Path to files")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/filtered_images_by_file.csv", help="File to output results")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

rowsOut = [row for row in rows if a.FILENAME_KEY in row and str(row[a.FILENAME_KEY]).strip() != "" and os.path.isfile(a.FILE_DIRECTORY + str(row[a.FILENAME_KEY]).strip())]

writeCsv(a.OUTPUT_FILE, rowsOut, headings=fieldNames)
