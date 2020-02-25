# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
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
parser.add_argument('-in', dest="INPUT_FILE", default="scrapers/internet_archive/data/politicaladarchive_2016.csv", help="Path to csv file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="CSV output file")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE.strip()
OUTPUT_FILE = args.OUTPUT_FILE.strip()

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

fieldNames, rows = readCsv(INPUT_FILE)

clinton = filterWhere(rows, [
    ("candidates", "Hillary Clinton", "~="),
    ("candidates", "Donald Trump", "!~="),
    ("race", "PRES", "==")
])
trump = filterWhere(rows, [
    ("candidates", "Donald Trump", "~="),
    ("candidates", "Hillary Clinton", "!~="),
    ("race", "PRES", "==")
])
all = clinton + trump

print("%s Clinton + %s Trump = %s" % (len(clinton), len(trump), len(all)))
writeCsv(OUTPUT_FILE, all, fieldNames)
