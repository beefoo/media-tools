# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import os
from pprint import pprint
import subprocess
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="../../tmp/internet_archive_metadata.csv", help="Path to csv file")
parser.add_argument('-deriv', dest="DERIVATIVE", default="mp4", help="Derivative to download")
parser.add_argument('-limit', dest="LIMIT", default=100, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-out', dest="OUTPUT_DIR", default="../../media/downloads/internet_archive/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE.strip()
DERIVATIVE = args.DERIVATIVE
LIMIT = args.LIMIT
OUTPUT_DIR = args.OUTPUT_DIR.strip()
OVERWRITE = args.OVERWRITE > 0

# Make sure output dirs exist
makeDirectories(OUTPUT_DIR)

# Get existing data
fieldNames, rows = readCsv(INPUT_FILE)

for i, row in enumerate(rows):
    if LIMIT > 0 and i > LIMIT:
        break
    id = row["identifier"]
    filename = "%s.%s" % (id, DERIVATIVE)
    url = "https://archive.org/download/%s/%s" % (id, filename)
    filepath = OUTPUT_DIR + filename
    if os.path.isfile(filepath) and not OVERWRITE:
        print("Already downloaded %s" % filename)
        continue
    command = ['curl', '-o', '-L', filepath, url]
    print(" ".join(command))
    finished = subprocess.check_call(command)

print("Done.")
