# -*- coding: utf-8 -*-

# python -W ignore mix_audio.py -in "../latitude/output/mix.csv" -inaudio "../latitude/output/mix_audio.csv" -dir "media/downloads/vivaldi/" -sd 60

import argparse
import math
from lib.audio_mixer import *
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
import os
from pprint import pprint
from pydub import AudioSegment
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="data/mix.csv", help="Input sequence csv file")
parser.add_argument('-inaudio', dest="INPUT_AUDIO_FILE", default="data/mix_audio.csv", help="Input audio csv file")
parser.add_argument('-dir', dest="AUDIO_DIR", default="media/sample/", help="Input audio directory")
parser.add_argument('-left', dest="PAD_LEFT", default=1000, type=int, help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default=3000, type=int, help="Pad right in milliseconds")
parser.add_argument('-ss', dest="EXCERPT_START", default=0, type=float, help="Slice start in seconds")
parser.add_argument('-sd', dest="EXCERPT_DUR", default=-1, type=float, help="Slice duration in seconds")
parser.add_argument('-fx', dest="SOUND_FX", default=1, type=int, help="Apply sound effects? (takes longer)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample_mix.mp3", help="Output audio file")
parser.add_argument('-overwrite', dest="OVERWRITE", default=1, type=int, help="Overwrite existing audio?")
args = parser.parse_args()

INPUT_FILE = args.INPUT_FILE
INPUT_AUDIO_FILE = args.INPUT_AUDIO_FILE
AUDIO_DIR = args.AUDIO_DIR
PAD_LEFT = args.PAD_LEFT
PAD_RIGHT = args.PAD_RIGHT
EXCERPT_START = int(round(args.EXCERPT_START * 1000))
EXCERPT_DUR = int(round(args.EXCERPT_DUR * 1000))
SOUND_FX = (args.SOUND_FX > 0)
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = (args.OVERWRITE > 0)

MIN_VOLUME = 0.01
MAX_VOLUME = 10.0

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# Read input file
fieldnames, audioFiles = readCsv(INPUT_AUDIO_FILE)
fieldnames, instructions = readCsv(INPUT_FILE)
print("%s audio files found" % len(audioFiles))
print("%s instructions found" % len(instructions))

# Make excerpt
instructions = [i for i in instructions if i["ms"] >= EXCERPT_START]
if EXCERPT_DUR > 0:
    EXCERPT_END = EXCERPT_START + EXCERPT_DUR
    instructions = [i for i in instructions if i["ms"] <= EXCERPT_END]

instructions = sorted(instructions, key=lambda k: k['ms'])

# Add features
for i, step in enumerate(instructions):
    instructions[i]["filename"] = AUDIO_DIR + audioFiles[step["ifilename"]]["filename"]
    instructions[i]["volume"] = 1.0 if "volume" not in step else lim(step["volume"], (MIN_VOLUME, MAX_VOLUME))
    instructions[i]["ms"] = step["ms"] - EXCERPT_START + PAD_LEFT

# determine duration
last = instructions[-1]
duration = last["ms"] + last["dur"] + PAD_RIGHT
print("Creating audio file with duration %ss" % formatSeconds(duration/1000))

mixAudio(instructions, duration=duration, outfilename=OUTPUT_FILE, sfx=SOUND_FX)
