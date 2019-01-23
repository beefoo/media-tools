# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/movies.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="duration,samples", help="Comma-separated list of properties")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
PROPS = [p for p in args.PROPS.strip().split(",")]

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)

def formatTime(s):
    h = int(s / 3600)
    s = s % 3600
    m = int(s / 60)
    s = s % 60
    s = roundInt(s)
    return str(h) + ":" + str(m).zfill(2) + ":" + str(s).zfill(2)

for prop in PROPS:
    d = [r[prop] for r in rows if prop in r and r[prop] > 0]
    print("-----\n" + prop + ":")
    total = sum(d)
    if "dur" in prop:
        print("Total: %s" % formatTime(total))
    else:
        print("Total: %s" % "{:,}".format(total))
    median = roundInt(np.median(d))
    if "dur" in prop:
        print("Median: %s" % formatSeconds(median))
    else:
        print("Median: %s" % "{:,}".format(median))
