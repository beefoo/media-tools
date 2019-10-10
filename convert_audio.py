# -*- coding: utf-8 -*-

import argparse
from lib.io_utils import *
from lib.processing_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import shutil
import subprocess
import sys
import tarfile

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/*.ext1", help="Input file pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="path/to/%s.ext2", help="Output file pattern")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing wavs?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILE)
if len(filenames) < 1:
    print("No files found")
    sys.exit()

makeDirectories(a.OUTPUT_FILE)

def convertFile(p):
    global a

    fileFrom, fileTo = p

    if os.path.isfile(fileTo) and not a.OVERWRITE:
        return

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'panic', '-y', '-i', fileFrom, fileTo]
    # print(" ".join(command))
    finished = subprocess.check_call(command)

props = []
for fn in filenames:
    basename = getBasename(fn)
    outfn = a.OUTPUT_FILE % basename
    props.append((fn, outfn))

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(convertFile, props)
pool.close()
pool.join()

print("Done.")
