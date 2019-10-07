# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.io_utils import *
from lib.video_utils import *
import os
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/ia_politicaladarchive/", help="Input dir")
parser.add_argument('-fk', dest="FILENAME_KEY", default="filename", help="Key to retrieve filename")
parser.add_argument('-dk', dest="DURATION_KEY", default="duration", help="Key for duration")
parser.add_argument('-fast', dest="FAST_NOT_ACCURATE", action="store_true", help="Check duration accurately by opening it? (takes longer)")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing non-zero durations?")
a = parser.parse_args()

# Parse arguments
INPUT_FILE = a.INPUT_FILE
MEDIA_DIRECTORY = a.MEDIA_DIRECTORY
FILENAME_KEY = a.FILENAME_KEY
ACCURATE = (not a.FAST_NOT_ACCURATE)

keysToAdd = [a.DURATION_KEY, "hasAudio", "hasVideo"]

# get unique video files
print("Reading file...")
fieldNames, rows = readCsv(INPUT_FILE)
rowCount = len(rows)
print("Found %s rows" % rowCount)

# add keys
for key in keysToAdd:
    if key not in fieldNames:
        fieldNames.append(key)

print("Getting file features...")
for i, row in enumerate(rows):
    duration = row[a.DURATION_KEY] if a.DURATION_KEY in row else 0
    hasAudio = row["hasAudio"] if "hasAudio" in row else 0
    hasVideo = row["hasVideo"] if "hasVideo" in row else 0
    if FILENAME_KEY in row and len(row[FILENAME_KEY]) > 0 and (duration <= 0 or duration == "" or a.OVERWRITE):
        filepath = MEDIA_DIRECTORY + row[FILENAME_KEY]
        types = getMediaTypes(filepath)
        hasAudio = 1 if "audio" in types else 0
        hasVideo = 1 if "video" in types else 0
        if hasAudio and not hasVideo:
            duration = getDurationFromAudioFile(filepath)
        else:
            duration = getDurationFromFile(filepath, ACCURATE)
    rows[i][a.DURATION_KEY] = duration
    rows[i]["hasAudio"] = hasAudio
    rows[i]["hasVideo"] = hasVideo
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*i/(rowCount-1)*100,1))
    sys.stdout.flush()

writeCsv(INPUT_FILE, rows, headings=fieldNames)
