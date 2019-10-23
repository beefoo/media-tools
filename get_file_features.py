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
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/ia_politicaladarchive.csv", help="Input file pattern")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/downloads/ia_politicaladarchive/", help="Input dir")
parser.add_argument('-dk', dest="DURATION_KEY", default="duration", help="Key for duration")
parser.add_argument('-fast', dest="FAST_NOT_ACCURATE", action="store_true", help="Check duration accurately by opening it? (takes longer)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output csv file; leave blank if same as input")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing non-zero durations?")
a = parser.parse_args()

# Parse arguments
INPUT_FILE = a.INPUT_FILE
OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else INPUT_FILE
ACCURATE = (not a.FAST_NOT_ACCURATE)

keysToAdd = [a.DURATION_KEY, "hasAudio", "hasVideo"]

makeDirectories(OUTPUT_FILE)

# get unique video files
print("Reading files...")
fieldNames, rows, rowCount = getFilesFromString(a)
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
    if duration <= 0 or duration == "" or a.OVERWRITE:
        types = getMediaTypes(row["filename"])
        hasAudio = 1 if "audio" in types else 0
        hasVideo = 1 if "video" in types else 0
        if hasAudio > 0 or hasVideo > 0:
            if hasAudio > 0 and hasVideo < 1:
                duration = getDurationFromAudioFile(row["filename"])
            else:
                duration = getDurationFromFile(row["filename"], ACCURATE)
    rows[i]["filename"] = os.path.basename(row["filename"])
    rows[i][a.DURATION_KEY] = duration
    rows[i]["hasAudio"] = hasAudio
    rows[i]["hasVideo"] = hasVideo
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*i/(rowCount-1)*100,1))
    sys.stdout.flush()

writeCsv(INPUT_FILE, rows, headings=fieldNames)
