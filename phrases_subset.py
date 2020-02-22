# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import random
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/manifest.csv", help="Input csv file")
parser.add_argument('-sdir', dest="SAMPLE_INPUT_DIR", default="tmp/samples/", help="Directory of input sample files (if reading from a manifest .csv file)")
parser.add_argument('-pdir', dest="PHRASE_INPUT_DIR", default="tmp/phrases/", help="Directory of input sample files (if reading from a manifest .csv file)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/combined_samples.csv", help="Write the result to file")

parser.add_argument('-sort', dest="SORT", default="clarity=desc", help="Query string to sort phrases by")
parser.add_argument('-filter', dest="FILTER", default="", help="Query string to filter by")
parser.add_argument('-lim', dest="LIMIT", default=-1, type=int, help="Target total sample count, -1 for everything")
parser.add_argument('-limp', dest="LIMIT_PHRASES_PER_FILE", default=-1, type=int, help="Limit number of phrases to take per file, -1 for everything")
parser.add_argument('-lims', dest="LIMIT_SAMPLES_PER_PHRASE", default=-1, type=int, help="Limit number of samples to take per phrase, -1 for everything")

parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show the stats")
a = parser.parse_args()

# Read files
fieldNames, files = readCsv(a.INPUT_FILE)
if "phrases" not in fieldNames:
    fieldNames.append("phrases")

samples = []
phrases = []
sampleFieldnames = []
for i, f in enumerate(files):
    _fieldNames, fsamples = readCsv(a.SAMPLE_INPUT_DIR + f["filename"] + ".csv")
    sampleFieldnames = unionLists(sampleFieldnames, _fieldNames)
    _, fphrases = readCsv(a.PHRASE_INPUT_DIR + f["filename"] + ".csv")
    # files[i]["fsamples"] = fsamples
    # files[i]["fphrases"] = fphrases
    samples += fsamples
    phrases += fphrases

if "phrase" not in sampleFieldnames:
    sampleFieldnames.append("phrase")

fileCount = len(files)
print("Found %s files" % fileCount)
phraseCount = len(phrases)
print("Found %s phrases" % phraseCount)
sampleCount = sum([p["count"] for p in phrases])
print("Found %s samples" % sampleCount)

for i, p in enumerate(phrases):
    phrases[i]["end"] = p["start"] + p["dur"]

for i, s in enumerate(samples):
    samples[i]["end"] = s["start"] + s["dur"]

if a.LIMIT_PHRASES_PER_FILE > 0:
    phrasesByFilename = groupList(phrases, 'filename')
    limitedPhrases = []
    for i, group in enumerate(phrasesByFilename):
        if group['count'] > a.LIMIT_PHRASES_PER_FILE:
            groupPhrases = sortByQueryString(group['items'], a.SORT)
            limitedPhrases += groupPhrases[:a.LIMIT_PHRASES_PER_FILE]
        else:
            limitedPhrases += group['items']
    phrases = limitedPhrases

phrases = sortByQueryString(phrases, a.SORT)

if len(a.FILTER) > 0:
    phrases = filterByQueryString(phrases, a.FILTER)
    phraseCount = len(phrases)
    print("Found %s phrases after filtering" % phraseCount)

print("Collecting samples...")
validSamples = []
for i, p in enumerate(phrases):
    psamples = [s for s in samples if s["filename"]==p["filename"] and s["start"] >= p["start"] and s["end"] <= p["end"]]
    if a.LIMIT_SAMPLES_PER_PHRASE > 0 and len(psamples) > a.LIMIT_SAMPLES_PER_PHRASE:
        psamples = sorted(psamples, key=lambda s: s['start'])
        psamples = psamples[:a.LIMIT_SAMPLES_PER_PHRASE]
    for j, s in enumerate(psamples):
        psamples[j]["phrase"] = i
    validSamples += psamples
    if a.LIMIT > 0 and len(validSamples) > a.LIMIT:
        break

sampleCount = len(validSamples)
print("Found %s valid samples" % sampleCount)

if a.LIMIT > 0 and sampleCount < a.LIMIT:
    print("** Try increasing -limp or -lims to get more valid samples **")

elif a.LIMIT > 0 and (sampleCount-50) > a.LIMIT:
    print("** Try reducing -limp or -lims to get your valid sample count closer to %s **" % a.LIMIT)

validFileCount = len(unique([s["filename"] for s in validSamples]))
print("Found %s unique files" % validFileCount)

# get phrase counts
for i, file in enumerate(files):
    files[i]['phrases'] = len(unique([s["phrase"] for s in validSamples if s["filename"]==file["filename"]]))

if a.PROBE:
    counts = getCounts(validSamples, "filename")
    breakPoint = False
    breakCount = 0
    for value, count in counts:
        breakCount += count
        if a.LIMIT > 0 and breakCount > a.LIMIT and not breakPoint:
            print('------ breakpoint %s' % a.LIMIT)
            breakPoint = True
        print("%s (%s%%)\t %s" % (count, round(1.0*count / sampleCount * 100.0, 2), value))
    sys.exit()

writeCsv(a.OUTPUT_FILE, validSamples, headings=sampleFieldnames)
writeCsv(a.INPUT_FILE, files, headings=fieldNames)
