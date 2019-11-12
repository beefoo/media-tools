# -*- coding: utf-8 -*-

import argparse
import inspect
import math
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import numpy as np
import os
from pprint import pprint
import subprocess
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/items.csv", help="Input file")
parser.add_argument('-dir', dest="PHRASE_DIR", default="output/phrases/", help="Phrase data directory")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
a = parser.parse_args()

# Read files
fieldNames, items = readCsv(a.INPUT_FILE)

if 'phrases' not in fieldNames:
    fieldNames.append('phrases')

items = addIndices(items)

for i, item in enumerate(items):
    items[i]["phrasefilename"] = a.PHRASE_DIR + item["filename"] + ".csv"

def getItemPhrases(item):
    global a
    phrases = 0

    if os.path.isfile(item['phrasefilename']):
        _, fphrases = readCsv(item['phrasefilename'])
        phrases = len(fphrases)

    item['phrases'] = phrases
    return item

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(getItemPhrases, items)
pool.close()
pool.join()

results = sorted(results, key=lambda r: r['index'])

writeCsv(a.INPUT_FILE, results, headings=fieldNames)
print("Done.")
