# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import os
from pprint import pprint
import re
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-key', dest="COLUMN_KEY", default="filename", help="Column key to match against")
parser.add_argument('-find', dest="FIND_PATTERN", default="(.*)\.wav", help="Find pattern")
parser.add_argument('-rkey', dest="UPDATE_COLUMN_KEY", default="", help="Column key to replace; leave blank if the same column key")
parser.add_argument('-repl', dest="REPLACE_PATTERN", default="\\1.mp3", help="Replace pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="CSV output file; leave blank if update the same file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show info?")
a = parser.parse_args()

# Parse arguments
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE
FIND_PATTERN = a.FIND_PATTERN.strip()
REPLACE_PATTERN = a.REPLACE_PATTERN.strip()
UPDATE_COLUMN_KEY = a.UPDATE_COLUMN_KEY.strip() if len(a.UPDATE_COLUMN_KEY) > 0 else a.COLUMN_KEY

# Read data
headings, rows = readCsv(a.INPUT_FILE)

if UPDATE_COLUMN_KEY not in headings:
    headings.append(UPDATE_COLUMN_KEY)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

for i, row in enumerate(rows):
    value = row[a.COLUMN_KEY]
    newValue = re.sub(FIND_PATTERN, REPLACE_PATTERN, value)
    rows[i][UPDATE_COLUMN_KEY] = newValue
    if a.PROBE:
        print(newValue)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings)
