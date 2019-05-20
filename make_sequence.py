# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_fedflixnara_subset_128x128.csv", help="Input sample csv file")
parser.add_argument('-dir', dest="MEDIA_DIR", default="media/downloads/ia_fedflixnara/", help="Media directory")
parser.add_argument('-uid', dest="UNIQUE_ID", default="ia_fedflixnara", help="Unique identifier")
parser.add_argument('-outframe', dest="OUTPUT_FRAME", default="tmp/%s_%s_frames/frame.%s.png", help="Output frames pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/%s_%s_%s.mp4", help="Output file pattern")
parser.add_argument('-cd', dest="CACHE_DIR", default="tmp/%s_cache/", help="Cache dir pattern")
parser.add_argument('-seq', dest="SEQUENCE", default="proliferation,waves,falling,orbits,shuffle,stretch,flow,splice", help="Comma separated list of compositions")
parser.add_argument('-db', dest="SEQUENCE_DB", default="0,0,0,0,0,0,0,0", help="Comma separated list of decibel adjustments; leave blank if no adjustments")
parser.add_argument('-pyv', dest="PYTHON_NAME", default="python3", help="Name of python command")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just spit out duration info and commands")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing?")
a = parser.parse_args()

SEQUENCE = a.SEQUENCE.strip().split(",")
SEQUENCE_DB = a.SEQUENCE_DB.strip().split(",")

# No DB adjustments needed
if len(SEQUENCE_DB) <= 0:
    SEQUENCE_DB = [0.0 for v in range(len(SEQUENCE))]

if len(SEQUENCE) != len(SEQUENCE_DB):
    print("Error: DB list must be the same length as sequence")
    sys.exit()

# Determine offsets
runningTotalMs = 0
offsets = []
for comp in SEQUENCE:
    offsets.append(runningTotalMs)
    command = [a.PYTHON_NAME, 'compositions/%s.py' % comp, '-in', a.INPUT_FILE, '-probe']
    print(" ".join(command))
    result = subprocess.check_output(command).strip()
    lines = [line.strip() for line in result.splitlines()]
    lastLine = lines[-1].decode("utf-8")
    compMs = int(lastLine.split(":")[-1].strip())
    runningTotalMs += compMs
    print("Running total: %s (%s)" % (runningTotalMs, formatSeconds(runningTotalMs/1000.0)))
    print("------")

# Now run the scripts
startTime = logTime()
for i, comp in enumerate(SEQUENCE):
    offset = offsets[i]
    db = SEQUENCE_DB[i]
    number = str(i+1).zfill(2)
    outfile = a.OUTPUT_FILE % (a.UNIQUE_ID, number, comp)
    command = [a.PYTHON_NAME, 'compositions/%s.py' % comp,
        '-in', a.INPUT_FILE,
        '-dir', a.MEDIA_DIR,
        '-out', outfile,
        '-cache',
        '-cd', a.CACHE_DIR % a.UNIQUE_ID,
        '-ckey', "%s_%s" % (a.UNIQUE_ID, comp),
        '-outframe', a.OUTPUT_FRAME % (a.UNIQUE_ID, comp, '%s'),
        '-io', str(offset),
        '-db', db,
        '-verifyc'
    ]
    if a.OVERWRITE:
        command.append('-overwrite')
    print(" ".join(command))
    if a.PROBE:
        continue
    finished = subprocess.check_call(command)
logTime(startTime, "Total execution time")
