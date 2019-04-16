# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample_%s.mp3", help="CSV output file")
parser.add_argument('-rvb', dest="REVERB", default=80, type=int, help="Reverberence (0-100)")
parser.add_argument('-mdb', dest="MATCH_DB", default=-16, type=int, help="Match decibels, -9999 for none")
parser.add_argument('-fadein', dest="FADE_IN", default=0.2, type=float, help="Fade in as a percentage of clip duration")
parser.add_argument('-fadeout', dest="FADE_OUT", default=0.5, type=float, help="Fade out as a percentage of clip duration")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-threads', dest="THREADS", default=1, type=int, help="Number of threads")
a = parser.parse_args()

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

samples = addIndices(samples)
samples = prependAll(samples, ("filename", a.MEDIA_DIRECTORY))

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

# group by filename
params = groupList(samples, "filename")
fileCount = len(params)

def samplesToFiles(p):
    global sampleCount
    global a

    fn = p["filename"]
    samples = p["items"]
    audio = getAudio(fn)
    audioDurationMs = len(audio)

    print("Creating %s samples for %s..." % (len(samples), fn))
    for sample in samples:
        clipAudio = getAudioClip(audio, sample["start"], sample["dur"], audioDurationMs)
        clipAudio = applyAudioProperties(clipAudio, {
            "matchDb": a.MATCH_DB,
            "fadeIn": roundInt(sample["dur"] * a.FADE_IN),
            "fadeOut": roundInt(sample["dur"] * a.FADE_OUT),
            "reverb": a.REVERB
        })
        outfilename = a.OUTPUT_FILE % zeroPad(sample["index"], sampleCount)
        format = outfilename.split(".")[-1]
        clipAudio.export(outfilename, format=format)

threads = getThreadCount(a.THREADS)
pool = ThreadPool(threads)
pool.map(samplesToFiles, params)
pool.close()
pool.join()
