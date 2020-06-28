# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.io_utils import *
from lib.processing_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input media directory")
parser.add_argument('-fkey', dest="FILENAME_KEY", default="clipFilename", help="Key for filename")
parser.add_argument('-skey', dest="START_KEY", default="", help="Key for start in milliseconds")
parser.add_argument('-dkey', dest="DUR_KEY", default="", help="Key for duration in milliseconds")
parser.add_argument('-width', dest="IMAGE_WIDTH", default=800, type=int, help="Width of image")
parser.add_argument('-height', dest="IMAGE_HEIGHT", default=100, type=int, help="Height of image")
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of threads")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/waveforms/%s.png", help="Output directory")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing images?")
a = parser.parse_args()

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

makeDirectories([a.OUTPUT_DIR])

def sampleToWaveform(s):
    global a
    filename = a.MEDIA_DIRECTORY + s[a.FILENAME_KEY]
    imageFilename = a.OUTPUT_DIR % getBasename(filename)

    if os.path.isfile(imageFilename) and not a.OVERWRITE:
        print("Already exists: %s" % imageFilename)
        return

    if not os.path.isfile(filename):
        print("No file found at %s" % filename)
        return

    audio = getAudio(filename)
    if len(a.START_KEY) and len(a.DUR_KEY):
        audio = getAudioClip(audio, s[a.START_KEY], s[a.DUR_KEY], clipFadeIn=0, clipFadeOut=0)
    audioToWaveform(audio, a.IMAGE_WIDTH, a.IMAGE_HEIGHT, imageFilename)
    print("Wrote to %s" % imageFilename)

pool = ThreadPool(getThreadCount(a.THREADS))
results = pool.map(sampleToWaveform, samples)
pool.close()
pool.join()
