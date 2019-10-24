# -*- coding: utf-8 -*-

# https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html

import argparse
from lib.audio_utils import *
from lib.cache_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import librosa
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
from skimage.measure import block_reduce
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/features.p", help="Output file")
parser.add_argument('-threads', dest="THREADS", default=4, type=int, help="Number of threads")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rowCount = len(rows)

rows = addIndices(rows)
rows = prependAll(rows, ("filename", a.AUDIO_DIRECTORY))

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

# find unique filepaths
print("Matching samples to files...")
filenames = list(set([row["filename"] for row in rows]))
params = [{
    "samples": [row for row in rows if row["filename"]==fn],
    "filename": fn
} for fn in filenames]
fileCount = len(params)
progress = 0

# Adapted from: https://github.com/kylemcdonald/AudioNotebooks/blob/master/Samples%20to%20Fingerprints.ipynb
def getFingerPrint(y, sr, start, dur, n_fft=2048, hop_length=512, window=None, use_logamp=False):
    # take at most one second
    dur = min(dur, 1000)

    # analyze just the sample
    i0 = int(round(start / 1000.0 * sr))
    i1 = int(round((start+dur) / 1000.0 * sr))
    y = y[i0:i1]

    reduce_rows = 10 # how many frequency bands to average into one
    reduce_cols = 1 # how many time steps to average into one
    crop_rows = 32 # limit how many frequency bands to use
    crop_cols = 32 # limit how many time steps to use

    if not window:
        window = np.hanning(n_fft)
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop_length, window=window)
    amp = np.abs(S)
    if reduce_rows > 1 or reduce_cols > 1:
        amp = block_reduce(amp, (reduce_rows, reduce_cols), func=np.mean)
    if amp.shape[1] < crop_cols:
        amp = np.pad(amp, ((0, 0), (0, crop_cols-amp.shape[1])), 'constant')
    amp = amp[:crop_rows, :crop_cols]
    if use_logamp:
        amp = librosa.logamplitude(amp**2)
    amp -= amp.min()
    if amp.max() > 0:
        amp /= amp.max()
    amp = np.flipud(amp) # for visualization, put low frequencies on bottom
    return amp

def processFile(p):
    global progress
    global rowCount

    fingerprints = []

    # load audio
    fn = getAudioFile(p["filename"])
    y, sr = librosa.load(fn, sr=None)
    for sample in p["samples"]:
        fingerprint = getFingerPrint(y, sr, sample["start"], sample["dur"])
        fingerprints.append({
            "index": sample["index"],
            "fingerprint": fingerprint
        })
        progress += 1
        printProgress(progress, rowCount)

    return fingerprints

print("Processing fingerprints...")
data = []
if a.THREADS == 1:
    for p in params:
        processFile(p)
else:
    threads = getThreadCount(a.THREADS)
    pool = ThreadPool(threads)
    data = pool.map(processFile, params)
    pool.close()
    pool.join()

data = flattenList(data)
data = sorted(data, key=lambda d: d["index"])
fingerprints = [d["fingerprints"] for d in data]
saveCacheFile(a.OUTPUT_FILE, fingerprints, overwrite=True)
print("Done.")
