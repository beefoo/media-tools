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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/yt-search/*.json", help="Path to csv file")
parser.add_argument('-id', dest="ID_KEY", default="id", help="Key to Youtube Id")
parser.add_argument('-limit', dest="LIMIT", default=-1, type=int, help="Limit downloads; -1 for no limit")
parser.add_argument('-threads', dest="THREADS", default=2, type=int, help="Limit parallel downloads (limited to # of cores), -1 for max")
parser.add_argument('-out', dest="OUTPUT_DIR", default="media/downloads/yt/", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
a = parser.parse_args()

# Parse arguments
fnames = getFilenames(a.INPUT_FILE)

uIds = []
for fn in fnames:
    if fn.endswith(".csv"):
        _, rows = readCsv(fn, doParseNumbers=False)
        uIds += [row[a.ID_KEY] for row in rows]
    else:
        data = readJSON(fn)
        uIds.append(data[a.ID_KEY])

# Make sure output dirs exist
makeDirectories([a.OUTPUT_DIR])

if a.LIMIT > 0 and len(uIds) > a.LIMIT:
    uIds = uIds[:a.LIMIT]

def downloadMedia(uId):
    global a

    command = ['youtube-dl'] # We need -L because the URL redirects
    if not a.OVERWRITE:
        command += ['--no-overwrites']
    command += ['https://www.youtube.com/watch?v=%s' % uId]
    print(" ".join(command))

    try:
        finished = subprocess.check_call(command)
    except subprocess.CalledProcessError:
        error = "CalledProcessError: could not properly download %s" % uId
        print(error)
        return error

    fns = getFilenames("*%s*.*" % uId)
    if len(fns) < 1:
        error = "Error: could not find download %s" % uId
        print(error)
        return error

    fn = fns[0]
    size = os.path.getsize(fn)
    # Remove file if not downloaded properly
    if size < 43000:
        error = "Error: did not download asset of %s" % uId
        print(error)
        os.remove(fn)
        return error
     # Move the file to the target location
    # os.rename(basename, filepath)

    fileext = getFileExt(fn)
    filepath = a.OUTPUT_DIR + uId + fileext
    shutil.move(fn, filepath)
    os.remove(fn)

    return None

threads = getThreadCount(a.THREADS)
pool = ThreadPool(threads)
errors = pool.map(downloadMedia, uIds)
pool.close()
pool.join()

errors = [e for e in errors if e is not None]

print("-----")
if len(errors) > 0:
    print("Done with %s errors" % len(errors))
    pprint(errors)
else:
    print("Done.")
