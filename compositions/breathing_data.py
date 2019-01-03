# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-data', dest="DATA_FILE", default="../media/downloads/m002.csv", help="Path to data file")
a = parser.parse_args()

# data was converted from .dat to .csv using the command:
# rdsamp -r m002 -c -t 600 -p -signal-list 0 2 3 -P > m002.csv
#   produce csv, 10 minutes, print seconds, limit to 3 signals, high precision
# https://physionet.org/physiotools/wag/rdsamp-1.htm
# https://physionet.org/physiotools/wfdb.shtml

signals = ["ecg", "resp", "scg"]
headings = ["s"] + signals
fieldnames, data = readCsv(a.DATA_FILE, readDict=False, encoding=False)

# reduce the data so there's one sample per millisecond
reducedData = []
ms = -1
for d in data:
    s = d[0]
    dms = roundInt(s * 1000)
    delta = dms - ms

    if delta > 1:
        print("error: delta is greater than 1 ms")
        sys.exit()

    if delta == 1:
        entry = {}
        for i, h in enumerate(headings):
            if i > 0:
                entry[h] = d[i]
        reducedData.append(entry)
        ms = dms


# write new file
writeCsv(a.DATA_FILE, reducedData, headings=signals)
