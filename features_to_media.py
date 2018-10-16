# -*- coding: utf-8 -*-

# python features_to_media.py -in tmp/samples_features.csv -sort hz -out output/sort_hz.mp3

import argparse
import csv
from lib import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
import numpy as np
from pprint import pprint
from pydub import AudioSegment
import sys
import time


# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples_tsne.csv", help="Input file")
parser.add_argument('-dir', dest="AUDIO_DIRECTORY", default="audio/sample/", help="Input file")
parser.add_argument('-sort', dest="SORT_BY", default="tsne", help="Key to sort by (tsne, hz, pow, dur)")
parser.add_argument('-left', dest="PAD_LEFT", default=2000, type=int, help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default=2000, type=int, help="Pad right in milliseconds")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sort_tsne.mp3", help="Output media file")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
AUDIO_DIRECTORY = args.AUDIO_DIRECTORY
SORT_BY = args.SORT_BY
PAD_LEFT = args.PAD_LEFT
PAD_RIGHT = args.PAD_RIGHT
OUTPUT_FILE = args.OUTPUT_FILE

# Audio config
CLIP_FADE_IN_DUR = 100
CLIP_FADE_OUT_DUR = 100
SAMPLE_WIDTH = 2
FRAME_RATE = 44100
CHANNELS = 2

# Read files
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# Sort rows and add sequence
rows = sorted(rows, key=lambda k: k[SORT_BY])
ms = PAD_LEFT
for i, row in enumerate(rows):
    rows[i]["path"] = AUDIO_DIRECTORY + row["filename"]
    rows[i]["sequenceStart"] = ms
    ms += row["dur"]
sequenceDuration = ms + PAD_RIGHT
print("Total time: %s" % time.strftime('%H:%M:%S', time.gmtime(sequenceDuration/1000)))

# Make sure output dir exist
outDir = os.path.dirname(OUTPUT_FILE)
if not os.path.exists(outDir):
    os.makedirs(outDir)

# make one track per audio file
filepaths = list(set([row["path"] for row in rows]))

# Build track parameters
trackParams = [{
    "duration": sequenceDuration,
    "frameRate": FRAME_RATE,
    "samples": [row for row in rows if row["path"]==fp],
    "path": fp
} for fp in filepaths]
trackCount = len(trackParams)

progress = 0
def makeTrack(p):
    global progress
    global trackCount

    duration = p["duration"]
    frameRate = p["frameRate"]
    filepath = p["path"]
    samples = p["samples"]

    filepath = getAudioFile(filepath)
    fformat = filepath.split(".")[-1].lower()
    audio = AudioSegment.from_file(filepath, format=fformat)

    # convert to stereo
    if audio.channels != CHANNELS:
        print("Notice: changed %s to %s channels" % (filepath, CHANNELS))
        audio = audio.set_channels(CHANNELS)
    # convert sample width
    if audio.sample_width != SAMPLE_WIDTH:
        print("Warning: sample width changed to %s from %s in %s" % (SAMPLE_WIDTH, audio.sample_width, filepath))
        audio = audio.set_sample_width(SAMPLE_WIDTH)
    # convert sample rate
    if audio.frame_rate != frameRate:
        print("Warning: frame rate changed to %s from %s in %s" % (frameRate, audio.frame_rate, filepath))
        audio = audio.set_frame_rate(frameRate)

    # build audio
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=frameRate)
    baseAudio = baseAudio.set_channels(CHANNELS)
    baseAudio = baseAudio.set_sample_width(SAMPLE_WIDTH)
    for i, sample in enumerate(samples):
        # retrieve clip of audio
        clipStart = sample["start"]
        clipEnd = sample["start"] + sample["dur"]
        clip = audio[clipStart:clipEnd]

        # add a fade in/out to avoid clicking
        fadeInDur = min(CLIP_FADE_IN_DUR, sample["dur"]/2)
        fadeOutDur = min(CLIP_FADE_OUT_DUR, sample["dur"]/2)
        clip = clip.fade_in(fadeInDur).fade_out(fadeOutDur)

        baseAudio = baseAudio.overlay(clip, position=sample["sequenceStart"])

    progress += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/trackCount*100,1))
    sys.stdout.flush()

    return baseAudio

print("Building %s tracks..." % len(trackParams))
pool = ThreadPool()
tracks = pool.map(makeTrack, trackParams)
pool.close()
pool.join()

print("Combining tracks...")
baseAudio = AudioSegment.silent(duration=sequenceDuration, frame_rate=FRAME_RATE)
baseAudio = baseAudio.set_channels(CHANNELS)
baseAudio = baseAudio.set_sample_width(SAMPLE_WIDTH)
for track in tracks:
    baseAudio = baseAudio.overlay(track)

print("Writing to file...")
format = OUTPUT_FILE.split(".")[-1]
f = baseAudio.export(OUTPUT_FILE, format=format)
print("Wrote to %s" % OUTPUT_FILE)
