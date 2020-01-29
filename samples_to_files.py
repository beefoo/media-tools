# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample_%s.mp3", help="Audio output pattern")
parser.add_argument('-dout', dest="OUTPUT_DATA_FILE", default="output/samples.csv", help="CSV output file")
parser.add_argument('-rvb', dest="REVERB", default=0, type=int, help="Reverberence (0-100)")
parser.add_argument('-mdb', dest="MATCH_DB", default=-9999, type=int, help="Match decibels, -9999 for none")
parser.add_argument('-fadein', dest="FADE_IN", default=0.1, type=float, help="Fade in as a percentage of clip duration")
parser.add_argument('-fadeout', dest="FADE_OUT", default=0.1, type=float, help="Fade out as a percentage of clip duration")
parser.add_argument('-maxd', dest="MAX_DUR", default=-1, type=int, help="Maximum duration in milliseconds, -1 for no limit")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing data?")
parser.add_argument('-index', dest="INDEX_STYLE", action="store_true", help="Filenames should be index style?")
parser.add_argument('-fkey', dest="FILE_KEY", default="", help="Use this key for naming files; blank if use index/default")
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

    newSamples = []

    samples = sorted(samples, key=lambda s: s["start"])
    fsampleCount = len(samples)

    print("Creating %s samples for %s..." % (len(samples), fn))
    for i, sample in enumerate(samples):
        sdur = min(sample["dur"], a.MAX_DUR) if a.MAX_DUR > 0 else sample["dur"]
        outfilename = ""
        if a.INDEX_STYLE:
            outfilename = a.OUTPUT_FILE % zeroPad(sample["index"], sampleCount)
        elif len(a.FILE_KEY) > 0:
            outfilename = a.OUTPUT_FILE % sample[a.FILE_KEY]
        else:
            basename = getBasename(fn) + "_" + zeroPad(i+1, fsampleCount+1) + "_" + formatSeconds(sample["start"]/1000.0, separator="-", retainHours=True)
            outfilename = a.OUTPUT_FILE % basename

        newSample = sample.copy()
        newSample["sourceFilename"] = os.path.basename(fn)
        newSample["sourceStart"] = sample["start"]
        newSample["filename"] = os.path.basename(outfilename)
        newSample["id"] = getBasename(outfilename)
        newSample["start"] = 0
        newSample["dur"] = sdur
        newSamples.append(newSample)

        if os.path.isfile(outfilename) and not a.OVERWRITE:
            continue

        clipAudio = getAudioClip(audio, sample["start"], sdur, audioDurationMs)
        clipAudio = applyAudioProperties(clipAudio, {
            "matchDb": a.MATCH_DB,
            "fadeIn": roundInt(sample["dur"] * a.FADE_IN),
            "fadeOut": roundInt(sample["dur"] * a.FADE_OUT),
            "reverb": a.REVERB
        })

        format = outfilename.split(".")[-1]
        clipAudio.export(outfilename, format=format)

    return newSamples

threads = getThreadCount(a.THREADS)
pool = ThreadPool(threads)
data = pool.map(samplesToFiles, params)
pool.close()
pool.join()

if len(a.OUTPUT_DATA_FILE) > 0:
    for h in ["id", "sourceFilename", "sourceStart"]:
        if h not in fieldNames:
            fieldNames.append(h)
    newSamples = flattenList(data)
    writeCsv(a.OUTPUT_DATA_FILE, newSamples, headings=fieldNames)
