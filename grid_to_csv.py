# -*- coding: utf-8 -*-

import argparse
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-props', dest="PROPS", default="gridX,gridY", help="Grid props")
a = parser.parse_args()

# Parse arguments
PROPX, PROPY = tuple([p for p in a.PROPS.strip().split(",")])
OUTPUT_FILE = a.INPUT_FILE.replace(".csv", "_grid.csv")

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

# Sort by grid
samples = sorted(samples, key=lambda s: (s[PROPY], s[PROPX]))

# Group rows by y property
rows = groupList(samples, PROPY)
rows = sorted(rows, key=lambda r: r[PROPY])

# format cols
csvRows = []
for row in rows:
    cols = sorted(row["items"], key=lambda c: c[PROPX])
    cols = ["%s %s" % (col["filename"], formatSeconds(col["start"]/1000.0)) for col in cols]
    csvRows.append(cols)

writeCsv(OUTPUT_FILE, csvRows, headings=None)
