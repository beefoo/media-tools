# -*- coding: utf-8 -*-

# python3 projects/citizen_dj/composition_stretch.py

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

from djlib import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="SAMPLE_FILE", default="E:/Dropbox/citizen_dj/sampledata/loc-edison/00694094.wav.csv", help="Input sample file")
parser.add_argument('-dir', dest="MEDIA_DIR", default="E:/Dropbox/citizen_dj/music_production/audio/loc-edison/", help="Directory of media files")
parser.add_argument('-filter', dest="FILTER", default="start>=234754&start<=245574", help="Filter query string")
parser.add_argument('-bpm', dest="TARGET_BPM", type=int, default=119, help="Target beats per minute")
parser.add_argument('-repeat', dest="REPEAT", type=int, default=6, help="Repeat the last measure this many times")
parser.add_argument('-db', dest="MASTER_DB", type=float, default=10.0, help="Repeat the last measure this many times")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/edison_intro_start.wav", help="Output file")
a = parser.parse_args()

fieldnames, samples = readCsv(a.SAMPLE_FILE)

samples = filterByQueryString(samples, a.FILTER)
sampleCount = len(samples)
print("%s samples after filtering" % sampleCount)
samples = sorted(samples, key=lambda sample: sample['start'])
targetBeatMs = 60.0 / a.TARGET_BPM * 1000

if sampleCount <= 4:
    print("Need more samples!")
    sys.exit()

samplesStart = samples[:-4]
samplesEnd = samples[-4:]

instructions = []
ms = 0

sample = samplesStart[0]
dur = samplesStart[-1]['start'] - sample['start'] + samplesStart[-1]['dur']
instructions.append({
    "ms": roundInt(ms),
    "filename": a.MEDIA_DIR + sample["filename"],
    "start": sample["start"],
    "dur": dur
})
ms += dur


for i in range(a.REPEAT):
    progress = 1.0 * i / (a.REPEAT-1)
    intervalMs = roundInt(progress*targetBeatMs)
    for j in range(4):
        sample = samples[-(4-j)]
        dur = sample['dur']
        step = {
            "ms": roundInt(ms),
            "filename": a.MEDIA_DIR + sample["filename"],
            "start": sample["start"],
            "dur": dur
        }
        if dur < intervalMs:
            # step["stretchTo"] = targetBeatMs
            dur = intervalMs
        instructions.append(step)
        ms += dur

totalDuration = ms

mixAudio(instructions, totalDuration, a.OUTPUT_FILE, masterDb=a.MASTER_DB)
