# -*- coding: utf-8 -*-

import argparse
import csv
import inspect
import json
import math
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import shutil
import subprocess
import sys
import urllib

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/internet_archive_metadata.csv", help="Path to csv file")
parser.add_argument('-id', dest="ID_KEY", default="identifier", help="Key to retrieve IA identifier from")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-threads', dest="THREADS", default=2, type=int, help="Limit parallel downloads (limited to # of cores), -1 for max")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/internet_archive/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE.strip()
ID_KEY = args.ID_KEY
LIMIT = args.LIMIT
THREADS = min(args.THREADS, multiprocessing.cpu_count()) if args.THREADS > 0 else multiprocessing.cpu_count()
OUTPUT_DIR = args.OUTPUT_DIR.strip()
OVERWRITE = args.OVERWRITE

# Make sure output dirs exist
makeDirectories(OUTPUT_DIR)

# Get existing data
fieldNames, rows = readCsv(INPUT_FILE)
if "filename" not in fieldNames:
    fieldNames.append("filename")
errors = []

if LIMIT > 0:
    rows = rows[:LIMIT]

for i, row in enumerate(rows):
    rows[i]["index"] = i

def downloadMedia(row):
    global rows
    global fieldNames

    id = row[ID_KEY]
    filename = ""
    i = row["index"]

    if "filename" not in row or len(row["filename"]) <= 0:
        error = "No files for %s" % id
        print(error)
        return error

    filename = row["filename"]
    encodedFilename = urllib.parse.quote(filename)
    url = "https://archive.org/download/%s/%s" % (id, encodedFilename)
    filepath = OUTPUT_DIR + filename
    if os.path.isfile(filepath) and not OVERWRITE:
        print("Already downloaded %s" % filename)
        return None
    if "/" in filename:
        makeDirectories(filepath)
    command = ['curl', '-O', '-L', url] # We need -L because the URL redirects
    print(" ".join(command))
    basename = os.path.basename(encodedFilename)
    try:
        finished = subprocess.check_call(command)
    except subprocess.CalledProcessError:
        error = "CalledProcessError: could not properly download %s" % url
        print(error)
        if os.path.isfile(basename):
            os.remove(basename)
        return error
    size = os.path.getsize(basename)
    # Remove file if not downloaded properly
    if size < 43000:
        error = "Error: could not properly download %s" % url
        print(error)
        os.remove(basename)
        return error
     # Move the file to the target location
    # os.rename(basename, filepath)
    shutil.move(basename, filepath)

    return None

pool = ThreadPool(THREADS)
errors = pool.map(downloadMedia, rows)
pool.close()
pool.join()

errors = [e for e in errors if e is not None]

print("-----")
if len(errors) > 0:
    print("Done with %s errors" % len(errors))
    pprint(errors)
else:
    print("Done.")
