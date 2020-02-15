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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-blist', dest="BLACK_LIST", default="", help="CSV file for blacklist of entries")
parser.add_argument('-wlist', dest="WHITE_LIST", default="", help="CSV file for whitelist of entries")
parser.add_argument('-key', dest="KEY", default="id", help="Key to match on")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="File to output results; leave empty to update input file")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.INPUT_FILE

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

if len(a.BLACK_LIST) > 0:
    _, blist = readCsv(a.BLACK_LIST)
    bids = set([item[a.KEY] for item in blist])
    rows = [item for item in rows if item[a.KEY] not in bids]
    rowCount = len(rows)
    print("%s rows after blacklist filtering" % rowCount)

if len(a.WHITE_LIST) > 0:
    _, wlist = readCsv(a.WHITE_LIST)
    wids = set([item[a.KEY] for item in wlist])
    rows = [item for item in rows if item[a.KEY] in wids]
    rowCount = len(rows)
    print("%s rows after whitelist filtering" % rowCount)

if a.PROBE:
    sys.exit()

writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
