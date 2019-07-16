# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.math_utils import *
from lib.io_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="projects/global_lives/data/ia_globallives_subset.csv", help="Input video csv file")
a = parser.parse_args()

headings, rows = readCsv(a.INPUT_FILE)
collections = groupList(rows, "collection")
filenames = groupList(rows, "filename")

for f in filenames:
    items = f["items"]
    if len(items) > 1:
        print("%s has %s duplicate filenames" % (f["filename"], len(items)))

def getGaps(items):
    seconds = np.zeros(24*3600, dtype=int)
    for item in items:
        seconds[item["start"]:item["end"]] = 1
    gapStart = gapEnd = None
    gaps = []
    for i, s in enumerate(seconds):
        if s < 1:
            if gapStart is None:
                gapStart = i
                gapEnd = i
            else:
                gapEnd = i
        elif s > 0 and gapEnd is not None:
            gapDur = gapEnd - gapStart
            if gapDur > 0:
                gaps.append((gapStart, gapEnd, gapDur))
            gapStart = gapEnd = None
    return gaps

print("=====")
for c in collections:
    items = c["items"]
    gaps = getGaps(items)
    if len(gaps) > 0:
        print("\n--" + c["collection"] + "--")
        for g in gaps:
            gapStart, gapEnd, gapDur = g
            print("  Gap from %s to %s (%s)" % (formatSeconds(gapStart), formatSeconds(gapEnd), formatSeconds(gapDur)))
