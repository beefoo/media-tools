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
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/*.h2drumkit", help="Input file pattern")
parser.add_argument('-out', dest="OUTPUT_DIR", default="tmp/h2drumkit/", help="Path to output directory")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing wavs?")
a = parser.parse_args()

filenames = getFilenames(a.INPUT_FILE)
print("Found %s files" % len(filenames))
if len(filenames) < 1:
    sys.exit()


makeDirectories(a.OUTPUT_DIR)

def flacToWav(flacfile, wavfile):
    if os.path.isfile(wavfile) and not a.OVERWRITE:
        return

    command = ['ffmpeg', '-hide_banner', '-loglevel', 'panic', '-y', '-i', flacfile, wavfile]
    # print(" ".join(command))
    finished = subprocess.check_call(command)

def drumKitToWavs(filename):
    basename = getBasename(filename)
    # Create a temporary extract folder
    extractPath = a.OUTPUT_DIR + basename + "/"
    makeDirectories(extractPath)
    print("Extracting %s..." % filename)
    tnames = []

    with tarfile.open(filename) as tar:
        tnames = tar.getnames()
        tar.extractall(extractPath)

    print("Converting flac to wav...")
    for tname in tnames:
        if not tname.endswith(".flac"):
            continue
        flacfile = extractPath + tname
        flacbasename = getBasename(tname)
        wavfile = a.OUTPUT_DIR + basename + "__" + flacbasename + ".wav"
        flacToWav(flacfile, wavfile)

    # Delete temporary dir
    shutil.rmtree(extractPath)

# filenames = [filenames[0]]

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(drumKitToWavs, filenames)
pool.close()
pool.join()

print("Done.")
