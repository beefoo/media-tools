# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="projects/citizen_dj/data/drum_machines.csv", help="Input samples csv file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/drum_machines.json", help="Output json file")
parser.add_argument('-ext', dest="FILE_EXTENSION", default=".mp3", help="Change file extension if necessary; leave blank for no change")
parser.add_argument('-props', dest="PROPS", default="filename,instrument_key,instrument,priority", help="Comma-separated list of properties to take")

a = parser.parse_args()
PROPS = a.PROPS.strip().split(",")

_, rows = readCsv(a.INPUT_FILE)

groups = groupList(rows, "drumkit")
data = []

for group in groups:
    gdata = {"name": group["drumkit"]}
    instruments = []
    for item in group["items"]:
        instrument = []
        for p in PROPS:
            value = item[p]
            if p=="filename" and len(a.FILE_EXTENSION) > 0 and not value.endswith(a.FILE_EXTENSION):
                value = replaceFileExtension(value, a.FILE_EXTENSION)
            elif p=="priority" and value == "":
                value = 999
            instrument.append(value)
        instruments.append(instrument)
    gdata["instruments"] = instruments
    data.append(gdata)

jsonOut = {
    "drums": data,
    "itemHeadings": PROPS
}

makeDirectories(a.OUTPUT_FILE)
writeJSON(a.OUTPUT_FILE, jsonOut)
