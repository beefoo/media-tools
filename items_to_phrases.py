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
parser.add_argument('-dir', dest="SAMPLE_FILE_DIRECTORY", default="tmp/ia_fedflixnara_samples/", help="Directory to where the .csv files with sample data is found")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/phrases/", help="Output csv file")
parser.add_argument('-params', dest="PARAMS", default="", help="Parameters in query string format")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
parser.add_argument('-pyv', dest="PYTHON_NAME", default="python3", help="Name of python command")
a = parser.parse_args()

# Read files
fieldNames, items = readCsv(a.INPUT_FILE)

for i, item in enumerate(items):
    items[i]["samplefilename"] = a.SAMPLE_FILE_DIRECTORY + item["filename"] + ".csv"
    items[i]["phrasefilename"] = a.OUTPUT_DIR + item["filename"] + ".csv"

def getItemPhrases(item):
    global a

    if not a.OVERWRITE and os.path.isfile(item['phrasefilename']):
        print("%s already exists" % item['phrasefilename'])
        return

    command = [a.PYTHON_NAME, 'samples_to_phrases.py',
               '-in', item["samplefilename"],
               '-out', item["phrasefilename"]]

    if len(a.PARAMS) > 0:
        params = parseQueryString(a.PARAMS)
        for key in params:
            command += ['-'+key, str(params[key])]

    if a.PROBE:
        command += ['-probe']

    printCommand(command)
    finished = subprocess.check_call(command)

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(getItemPhrases, items)
pool.close()
pool.join()

print("Done.")
