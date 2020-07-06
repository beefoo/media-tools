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

a = parser.parse_args()

fieldNames, rows = readCsv(a.INPUT_FILE)
rows = addIndices(rows)

if "active" not in fieldNames:
    fieldNames.append("active")

for i, row in enumerate(rows):
    rows[i]["active"] = 0
    if row["priority"] == "":
        rows[i]["priority"] = 999

# group by drumkit
groups = groupList(rows, "drumkit")
for group in groups:
    # group by instrument
    instruments = [item for item in group["items"] if item["instrument"] != ""]
    groupByInstrument = groupList(instruments, "instrument")
    for instrumentGroup in groupByInstrument:
        sortedItems = sorted(instrumentGroup["items"], key=lambda item: item["priority"])
        highestPriorityItem = sortedItems[0]
        rows[highestPriorityItem["index"]]["active"] = 1

print("Updating active rows")
writeCsv(a.INPUT_FILE, rows, headings=fieldNames)

activeRows = [row for row in rows if row["active"] > 0]
groups = groupList(activeRows, "drumkit")

data = []

for group in groups:
    items = group["items"]
    id = items[0]["drumkit_id"]
    gdata = {"id": id, "name": group["drumkit"]}
    instruments = []
    for item in group["items"]:
        instrument = [item["instrument"]]
        filename = item["filename"]
        if len(a.FILE_EXTENSION) > 0 and not filename.endswith(a.FILE_EXTENSION):
            filename = replaceFileExtension(filename, a.FILE_EXTENSION)
        instrument.append(filename)
        instruments.append(instrument)
    gdata["instruments"] = instruments
    data.append(gdata)

jsonOut = {
    "drums": data,
    "itemHeadings": ["instrument", "filename"]
}

makeDirectories(a.OUTPUT_FILE)
writeJSON(a.OUTPUT_FILE, jsonOut)
