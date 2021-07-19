# -*- coding: utf-8 -*-

# This only works for URLs that accept a ?format=json parameter (e.g. https://collection.cooperhewitt.org/objects/2318799170/?format=json)
# For above example, you need to run `ingesters/resolve_redirects.py` to resolve redirect URL before running this script

import argparse
import inspect
import os
from pprint import pprint
import sys
import time

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="output/si/objects.csv", help="Path to .csv file generated from ndjson_to_csv.py")
parser.add_argument('-url', dest="URL_PATTERN", default="{resolved_url}?format=json", help="URL pattern that should give you JSON content")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/si/objects/{id}.json", help="Output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print details?")
parser.add_argument('-delay', dest="DELAY", type=float, default=0.25, help="How many seconds to delay requests (to avoid rate limiting)?")
a = parser.parse_args()

fields, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

if not a.PROBE:
    makeDirectories([a.OUTPUT_FILE])

for i, row in enumerate(rows):
    url = a.URL_PATTERN.format(**row)
    filename = a.OUTPUT_FILE.format(**row)
    if not a.PROBE:
        if a.OVERWRITE or not os.path.isfile(filename):
            downloadBinaryFile(url, filename)
            if a.DELAY > 0:
                time.sleep(a.DELAY)
        printProgress(i+1, rowCount)
    else:
        print(f'{url} -> {filename}')

print('Done.')
