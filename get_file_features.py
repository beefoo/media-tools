# -*- coding: utf-8 -*-

import argparse
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *
from lib.video_utils import *
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
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
parser.add_argument('-threads', dest="THREADS", default=3, type=int, help="Number of concurrent threads, -1 for all available")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing non-zero durations?")
parser.add_argument('-verbose', dest="VERBOSE", action="store_true", help="More details?")
parser.add_argument('-progressive', dest="PROGRESSIVE_SAVE", action="store_true", help="Save as files are read?")
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
rows = addIndices(rows)

# add keys
for key in keysToAdd:
    if key not in fieldNames:
        fieldNames.append(key)

progress = 0
def processRow(row):
    global a
    global rowCount
    global ACCURATE
    global progress

    if a.VERBOSE:
        print("Reading %s" % row["filename"])

    duration = row[a.DURATION_KEY] if a.DURATION_KEY in row else 0
    hasAudio = row["hasAudio"] if "hasAudio" in row else 0
    hasVideo = row["hasVideo"] if "hasVideo" in row else 0
    if duration == "" or duration <= 0 or a.OVERWRITE:
        types = getMediaTypes(row["filename"])
        hasAudio = 1 if "audio" in types else 0
        hasVideo = 1 if "video" in types else 0
        if hasAudio > 0 or hasVideo > 0:
            if hasAudio > 0 and hasVideo < 1:
                duration = getDurationFromAudioFile(row["filename"], ACCURATE)
            else:
                duration = getDurationFromFile(row["filename"], ACCURATE)
    row["filename"] = os.path.basename(row["filename"])
    row[a.DURATION_KEY] = duration
    row["hasAudio"] = hasAudio
    row["hasVideo"] = hasVideo
    progress += 1
    printProgress(progress, rowCount)
    return row

if a.PROGRESSIVE_SAVE or a.THREADS == 1:
    for i, row in enumerate(rows):
        rows[i] = processRow(row)
        if a.PROGRESSIVE_SAVE:
            writeCsv(OUTPUT_FILE, rows, headings=fieldNames)

else:
    print("Getting file features...")
    pool = ThreadPool(getThreadCount(a.THREADS))
    results = pool.map(processRow, rows)
    pool.close()
    pool.join()

rows = sorted(rows, key=lambda r: r["filename"])
writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
