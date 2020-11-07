# -*- coding: utf-8 -*-

import argparse
import inspect
from moviepy.editor import VideoFileClip
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from floydlib import *
from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="", help="Input video csv file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="", help="Path to videos folder")
parser.add_argument('-layout', dest="INPUT_LAYOUT", default="", help="Path to layout svg file")
parser.add_argument('-width', dest="WIDTH", default=3840, type=int, help="Output width")
parser.add_argument('-height', dest="HEIGHT", default=2160, type=int, help="Output height")
parser.add_argument('-dur', dest="DURATION", default=60.0, type=float, help="Output duration in seconds")
parser.add_argument('-mdb', dest="MATCH_DB", default=-3.0, type=float, help="Each track should match this decibel level")
parser.add_argument('-out', dest="OUTPUT_DIR", default="", help="Path to output file")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing audio?")
a = parser.parse_args()

# Read files
fieldNames, rows = readCsv(a.INPUT_FILE)
rows = prependAll(rows, ("filename", a.MEDIA_DIRECTORY, "filepath"))

for i, row in enumerate(rows):
    videoDur = int(row["duration"] * 1000)
    start = parseTimeMs(row["start"])
    end = parseTimeMs(row["end"])
    if end <= 0:
        end = videoDur
    nstart = 1.0 * start / videoDur
    nend = 1.0 * end / videoDur
    rows[i]["start"] = start
    rows[i]["end"] = end
    rows[i]["nstart"] = nstart
    rows[i]["nend"] = nend
    rows[i]["clipDuration"] = end - start
    rows[i]["duration"] = videoDur

# Make sure output dirs exist
AUDIO_OUT = a.OUTPUT_DIR + 'audio/%s.mp3'
DATA_OUT = a.OUTPUT_DIR + 'data/states.json'
makeDirectories([AUDIO_OUT, DATA_OUT])

if a.OVERWRITE:
    removeFiles(AUDIO_OUT % "*")

durationMs = int(a.DURATION*1000)

# read svg layout file
layout = parseLayoutFile(a.INPUT_LAYOUT)
layoutLookup = createLookup(layout, "id")

dataOut = []
for row in rows:
    if row["state"] not in layoutLookup:
        continue

    shapeData = layoutLookup[row["state"]]
    points = [s["points"] for s in shapeData["shapes"]]

    # print(row["city"])
    # print(points)

    # normalize points
    npoints = []
    for i, polygon in enumerate(points):
        npolygon = []
        for j, point in enumerate(polygon):
            x, y = point
            nx, ny = (round(1.0 * x / a.WIDTH, 2), round(1.0 * y / a.HEIGHT, 2))
            npolygon.append([nx, ny])
        npoints.append(npolygon)

    item = {
        "city": row["city"],
        "state": row["state"],
        "date": row["dateFormatted"],
        "points": npoints
    }
    dataOut.append(item)

    audioFn = AUDIO_OUT % row["state"]
    if os.path.isfile(audioFn) and not a.OVERWRITE:
        continue

    audio = getAudio(row["filepath"])
    clipDur = min(row["clipDuration"], durationMs)
    clip = getAudioClip(audio, row["start"], clipDur)
    clip = applyAudioProperties(clip, {
        "matchDb": a.MATCH_DB
    }, sfx=False)
    clip.export(audioFn, format="mp3", bitrate="128k")
    print("Wrote to %s" % audioFn)

writeJSON(DATA_OUT, dataOut)

print("Done.")
