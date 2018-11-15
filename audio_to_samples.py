# -*- coding: utf-8 -*-

# Looks for samples (clips) in arbitrary media based on audio

import argparse
import csv
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
import librosa
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from os.path import join
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/sample/bird.wav", help="Input file pattern")
parser.add_argument('-samples', dest="SAMPLES", default=-1, type=int, help="Max samples to produce per media file, -1 for all")
parser.add_argument('-min', dest="MIN_DUR", default=50, type=int, help="Minimum sample duration in ms")
parser.add_argument('-max', dest="MAX_DUR", default=-1, type=int, help="Maximum sample duration in ms, -1 for no max")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples.csv", help="CSV output file")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
args = parser.parse_args()

# Parse arguments
INPUT_FILES = args.INPUT_FILES
SAMPLES = args.SAMPLES if args.SAMPLES > 0 else None
MIN_DUR = args.MIN_DUR
MAX_DUR = args.MAX_DUR
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = args.OVERWRITE > 0

# Audio config
FFT = 2048
HOP_LEN = FFT/4

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Read files
files = getFilenames(INPUT_FILES)
fileCount = len(files)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

progress = 0
# files = files[:1]

def getSamples(fn):
    global progress
    global fileCount

    sampleData = getAudioSamples(fn, min_dur=MIN_DUR, max_dur=MAX_DUR, fft=FFT, hop_length=HOP_LEN)

    # if too many samples
    if SAMPLES is not None and len(sampleData) > SAMPLES:
        sampleData = sampleData[:SAMPLES]

    progress += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/fileCount*100,1))
    sys.stdout.flush()

    return sampleData

pool = ThreadPool()
data = pool.map(getSamples, files)
pool.close()
pool.join()

# Flatten the data
data = [item for sublist in data for item in sublist]
print("Found %s samples in total." % len(data))

print("Writing data to file...")
headings = ["filename", "start", "dur"]
rowCount = 0
with open(OUTPUT_FILE, 'wb') as f:
    writer = csv.writer(f)
    writer.writerow(headings)
    for entry in data:
        writer.writerow([entry[key] for key in headings])
print("Wrote %s rows to %s" % (len(data), OUTPUT_FILE))
