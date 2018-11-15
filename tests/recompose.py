# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import subprocess
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="../tmp/vivaldi_samples.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="../media/downloads/vivaldi/", help="Input directory")
parser.add_argument('-comps', dest="COMPOSITIONS", default="start,even,stagger,echo,pulse,dissolve,tpulse,pairs", help="List of compositions to make")
parser.add_argument('-interval', dest="INTERVAL", default=200, type=int, help="Interval")
parser.add_argument('-filter', dest="FILTER", default="filename=01_-_Vivaldi_Spring_mvt_1_Allegro.mp3", help="Query string")
parser.add_argument('-left', dest="PAD_LEFT", default="500", help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default="2000", help="Pad right in milliseconds")
parser.add_argument('-ss', dest="EXCERPT_START", default="0", help="Slice start in seconds")
parser.add_argument('-sd', dest="EXCERPT_DUR", default="120", help="Slice duration in seconds")
parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/recomposed_%s.mp3", help="Output media file")
parser.add_argument('-overwrite', dest="OVERWRITE", default="0", help="Overwrite existing audio?")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
COMPOSITIONS = args.COMPOSITIONS.split(",")
INTERVAL = args.INTERVAL
FILTER = args.FILTER
PAD_LEFT = args.PAD_LEFT
PAD_RIGHT = args.PAD_RIGHT
EXCERPT_START = args.EXCERPT_START
EXCERPT_DUR = args.EXCERPT_DUR
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = args.OVERWRITE

TMP_FILE = "../tmp/recompose.csv"
AUDIO_TMP_FILE = TMP_FILE.replace(".csv", "_audio.csv")

# Make sure output dir exist
outDirs = [os.path.dirname(TMP_FILE)]
for outDir in outDirs:
    if not os.path.exists(outDir):
        os.makedirs(outDir)

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Filter rows
rows = filterByQueryString(rows, FILTER)
rowCount = len(rows)
print("Found %s rows after filtering" % rowCount)

# Get filenames
filenames = list(set([row["filename"] for row in rows]))
filenamesOut = [{"filename": f} for f in filenames]

# filename,start,dur,tsne,power,hz,note,octave
rows = sortBy(rows, ("start", "asc"))
duration = rows[-1]["start"] + rows[-1]["dur"]

def compose(instructions, audiofiles, filename):
    writeCsv(TMP_FILE, instructions)
    writeCsv(AUDIO_TMP_FILE, audiofiles)
    command = ['python', '-W', 'ignore', '../mix.py',
        '-in', TMP_FILE,
        '-inaudio', AUDIO_TMP_FILE,
        '-dir', AUDIO_DIRECTORY,
        '-left', PAD_LEFT,
        '-right', PAD_RIGHT,
        '-ss', EXCERPT_START,
        '-sd', EXCERPT_DUR,
        '-overwrite', OVERWRITE,
        '-out', filename
    ]
    print("------")
    print(" ".join(command))
    finished = subprocess.check_call(command)

# place each sample evenly, ordered by clip start
if "start" in COMPOSITIONS:
    instructions = []
    for i, row in enumerate(rows):
        instructions.append({
            "ms": i * INTERVAL,
            "ifilename": filenames.index(row["filename"]),
            "start": row["start"],
            "dur": row["dur"]
        })
    compose(instructions, filenamesOut, OUTPUT_FILE % "start")

# only play the "even" samples
if "even" in COMPOSITIONS:
    instructions = []
    ms = 0
    for i, row in enumerate(rows):
        if i % 2 == 0:
            instructions.append({
                "ms": ms,
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"]
            })
            ms += INTERVAL
    compose(instructions, filenamesOut, OUTPUT_FILE % "even")

# staggered sequence, e.g. 1,0,3,2,5,4
if "stagger" in COMPOSITIONS:
    instructions = []
    for i, row in enumerate(rows):
        if i % 2 > 0:
            ms = (i - 1) * INTERVAL
        else:
            ms = (i + 1) * INTERVAL
        instructions.append({
            "ms": ms,
            "ifilename": filenames.index(row["filename"]),
            "start": row["start"],
            "dur": row["dur"]
        })
    compose(instructions, filenamesOut, OUTPUT_FILE % "stagger")

# echo each sample
if "echo" in COMPOSITIONS:
    instructions = []
    volumeStep = 0.1
    for i, row in enumerate(rows):
        ms = i * INTERVAL
        volume = 1.0
        while volume > 0.0:
            instructions.append({
                "ms": ms,
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "volume": volume
            })
            ms += row["dur"]
            volume -= volumeStep
    compose(instructions, filenamesOut, OUTPUT_FILE % "echo")

# pulse each sample
if "pulse" in COMPOSITIONS:
    instructions = []
    pulses = 32
    ms = 0
    overlap = 0.2
    for i, row in enumerate(rows):
        for pulse in range(pulses):
            progress = 1.0 * pulse / (pulses-1)
            volume = 0.5*math.sin(progress * math.pi)+0.5
            instructions.append({
                "ms": ms + pulse * (row["dur"] * (1.0-overlap)),
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "volume": volume
            })
        dur = row["dur"] * pulses - row["dur"] * overlap * (pulses-1)
        ms += int(round(dur * 0.5 + row["dur"] * 0.5))
    compose(instructions, filenamesOut, OUTPUT_FILE % "pulse")

# pulse and stretch each sample
if "dissolve" in COMPOSITIONS:
    instructions = []
    stretchTo = 6.0
    pulses = 32
    ms = 0
    overlap = 0.2
    for i, row in enumerate(rows):
        for pulse in range(pulses):
            progress = 1.0 * pulse / (pulses-1)
            volume = 0.5*math.sin(progress * math.pi)+0.5
            easedProgress = 0.5*math.sin(progress * math.pi)+0.5
            instructions.append({
                "ms": ms + pulse * (row["dur"] * (1.0-overlap)),
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "volume": volume,
                "stretch": lerp((stretchTo, 1.0), easedProgress)
            })
        dur = row["dur"] * pulses - row["dur"] * overlap * (pulses-1)
        ms += int(round(dur * 0.5 + row["dur"] * 0.5))
    compose(instructions, filenamesOut, OUTPUT_FILE % "dissolve")

# tempo-pulse each sample
if "tpulse" in COMPOSITIONS:
    instructions = []
    pulses = 32
    ms = 0
    tempoRange = (0.5, 2.0)
    for i, row in enumerate(rows):
        delta = 0
        for pulse in range(pulses):
            progress = 1.0 * pulse / (pulses-1)
            volume = 0.5*math.sin(progress * math.pi)+0.5
            easedProgress = 0.5*math.sin(progress * math.pi)+0.5
            instructions.append({
                "ms": ms + delta,
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "volume": volume
            })
            tempo = lerp(tempoRange, easedProgress)
            delta += row["dur"] / tempo
        ms += int(round(delta * 0.5 + row["dur"] * 0.5))
    compose(instructions, filenamesOut, OUTPUT_FILE % "tpulse")

# pulse each sample in pairs
if "pairs" in COMPOSITIONS:
    instructions = []
    pulses = 32
    ms = 0
    overlap = 0.0
    for i, row in enumerate(rows):
        if i % 2 == 0:
            continue
        r1 = rows[i-1]
        r2 = row
        if r1["dur"] < r2["dur"]:
            r1 = row
            r2 = rows[i-1]

        for pulse in range(pulses):
            progress = 1.0 * pulse / (pulses-1)
            volume = 0.5*math.sin(progress * math.pi)+0.5
            ms1 = ms + pulse * (r1["dur"] * (1.0-overlap))
            ms2 = ms1 + (r1["dur"] * (1.0-overlap)) * 0.5
            instructions.append({
                "ms": ms1,
                "ifilename": filenames.index(r1["filename"]),
                "start": r1["start"],
                "dur": r1["dur"],
                "volume": volume
            })
            instructions.append({
                "ms": ms2,
                "ifilename": filenames.index(r2["filename"]),
                "start": r2["start"],
                "dur": r2["dur"],
                "volume": volume
            })
        dur = r1["dur"] * pulses - r1["dur"] * overlap * (pulses-1)
        ms += int(round(dur * 0.5 + r1["dur"] * 0.5))
    compose(instructions, filenamesOut, OUTPUT_FILE % "pairs")

if "counterpoint" in COMPOSITIONS:
    instructions = []
    # step 1: add bass
    # take low frequency instruments
    lowfreq = sortBy(rows, ("hz", "asc"))
    lowfreq = sortAndTrim(rows, [
        ("hz", "asc", 0.2),
        ("power", "asc", 0.5),
        ("dur", "desc", 0.5),
        ("hz", "asc", 1.0)
    ])
    count = 4
    lowfreq = lowfreq[:count]
    if len(lowfreq) < count:
        print("Warning: not enough lowfreq")
    stretchTo = 12000
    interval = 4000
    loops = int(round(1.0 * duration / (interval * count)))
    for loop in range(loops):
        ms = loop * (count * interval)
        for i, row in enumerate(lowfreq):
            stretch = max(stretchTo / row["dur"], 1.0)
            instructions.append({
                "ms": ms + i * interval,
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "stretch": stretch,
                "volume": 0.8
            })
    # step two: add short pulses
    short = sortAndTrim(rows, [
        ("power", "desc", 0.6),
        ("dur", "desc", 0.9),
        ("dur", "asc", 1.0)
    ])
    stretchTo = 6.0
    pulses = 32
    ms = 0
    overlap = 0.2
    for i, row in enumerate(short):
        for pulse in range(pulses):
            progress = 1.0 * pulse / (pulses-1)
            volume = (0.5*math.sin(progress * math.pi)+0.5) * 2
            easedProgress = 0.5*math.sin(progress * math.pi)+0.5
            instructions.append({
                "ms": roundInt(ms + pulse * (row["dur"] * (1.0-overlap))),
                "ifilename": filenames.index(row["filename"]),
                "start": row["start"],
                "dur": row["dur"],
                "volume": volume,
                "stretch": lerp((stretchTo, 1.0), easedProgress)
            })
        dur = row["dur"] * pulses - row["dur"] * overlap * (pulses-1)
        ms += int(round(dur * 0.5 + row["dur"] * 0.5))
    compose(instructions, filenamesOut, OUTPUT_FILE % "counterpoint")
