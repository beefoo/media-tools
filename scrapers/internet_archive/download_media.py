# -*- coding: utf-8 -*-

# python download_media.py -in "../../tmp/ia_politicaladarchive.csv" -id archive_id -out "../../media/landscapes/downloads/ia_politicaladarchive/"

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
parser.add_argument('-id', dest="ID_KEY", default="identifier", help="Key to retrieve IA identifier from")
parser.add_argument('-deriv', dest="DERIVATIVE", default="mp4", help="Derivative to download")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-out', dest="OUTPUT_DIR", default="../../media/downloads/internet_archive/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE.strip()
ID_KEY = args.ID_KEY
DERIVATIVE = args.DERIVATIVE
LIMIT = args.LIMIT
OUTPUT_DIR = args.OUTPUT_DIR.strip()
OVERWRITE = args.OVERWRITE > 0

# Make sure output dirs exist
makeDirectories(OUTPUT_DIR)

# Get existing data
fieldNames, rows = readCsv(INPUT_FILE)
errors = []

for i, row in enumerate(rows):
    if LIMIT > 0 and i >= LIMIT:
        break
    id = row[ID_KEY]
    filename = "%s.%s" % (id, DERIVATIVE)
    url = "https://archive.org/download/%s/%s" % (id, filename)
    filepath = OUTPUT_DIR + filename
    if os.path.isfile(filepath) and not OVERWRITE:
        print("Already downloaded %s" % filename)
        continue
    command = ['curl', '-O', '-L', url] # We need -L because the URL redirects
    print(" ".join(command))
    finished = subprocess.check_call(command)
    size = os.path.getsize(filename)
    # Remove file if not downloaded properly
    if size < 43000:
        print("Error: could not properly download %s" % url)
        os.remove(filename)
        errors.append(url)
     # Move the file to the target location
    else:
        os.rename(filename, filepath)

if len(errors) > 0:
    print("Done with %s errors" % len(errors))
    pprint(errors)
else:
    print("Done.")
