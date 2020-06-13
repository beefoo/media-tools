# -*- coding: utf-8 -*-

import argparse
import inspect
import multiprocessing
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import shutil
import subprocess
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/file.csv", help="Path to csv file")
parser.add_argument('-url', dest="URL_KEY", default="url", help="Key to Twitter URL")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-threads', dest="THREADS", default=2, type=int, help="Limit parallel downloads (limited to # of cores), -1 for max")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/twitter/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just print commands?")
a = parser.parse_args()

fieldNames, rows = readCsv(a.INPUT_FILE)

# Make sure output dirs exist
makeDirectories([a.OUTPUT_DIR])

if a.LIMIT > 0 and len(rows) > a.LIMIT:
    rows = rows[:a.LIMIT]

def downloadMedia(row):
    global a

    url = row[a.URL_KEY]
    id = url.split("/")[-1] if "id" not in row else row["id"]

    command = ['youtube-dl'] # We need -L because the URL redirects
    if id is not None:
        command += ['-o', id+'.%(ext)s']
    if not a.OVERWRITE:
        command += ['--no-overwrites']
    command += [url]
    print(" ".join(command))
    if a.PROBE:
        return None

    try:
        finished = subprocess.check_call(command)
    except subprocess.CalledProcessError:
        error = "CalledProcessError: could not properly download %s" % id
        print(error)
        return error

    fns = getFilenames("*%s*.*" % id)
    if len(fns) < 1:
        error = "Error: could not find download %s" % id
        print(error)
        return error

    fn = fns[0]
    size = os.path.getsize(fn)
    # Remove file if not downloaded properly
    if size < 43000:
        error = "Error: did not download asset of %s" % id
        print(error)
        os.remove(fn)
        return error
     # Move the file to the target location
    # os.rename(basename, filepath)

    fileext = getFileExt(fn)
    filepath = a.OUTPUT_DIR + id + fileext
    shutil.move(fn, filepath)
    os.remove(fn)

    return None

threads = getThreadCount(a.THREADS)
pool = ThreadPool(threads)
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
