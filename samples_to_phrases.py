# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-min', dest="MIN_DUR", default=4, type=float, help="Minumum phrase duration in seconds")
parser.add_argument('-max', dest="MAX_DUR", default=30, type=float, help="Maximum phrase duration in seconds")
parser.add_argument('-mins', dest="MIN_SAMPLES", default=8, type=int, help="At least this many samples per phrase")
parser.add_argument('-msd', dest="MAX_SAMPLE_DUR", default=5, type=float, help="Maximum sample duration in seconds")
parser.add_argument('-clarity', dest="CLARITY_THRESHOLD", default=0.4, type=float, help="Mean should be above this clarity")
parser.add_argument('-power', dest="POWER_THRESHOLD", default=0.125, type=float, help="Mean be above this power")
parser.add_argument('-buffer', dest="BUFFER_SIZE", default=4, type=int, help="Analyze this many samples")
parser.add_argument('-maxc', dest="MIN_PHRASE_CLARITY", default=30.0, type=float, help="Minimum clarity of a phrase")
parser.add_argument('-maxp', dest="MAX_PHRASES", default=-1, type=int, help="Maximum phrases to retrieve; -1 for all")
parser.add_argument('-maxs', dest="MAX_SAMPLES", default=-1, type=int, help="Maximum samples to retrieve; -1 for all")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/phrases.csv", help="Output csv file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just show details?")
a = parser.parse_args()
aa = vars(a)

aa["MIN_DUR"] = roundInt(a.MIN_DUR * 1000)
aa["MAX_DUR"] = roundInt(a.MAX_DUR * 1000)
aa["MAX_SAMPLE_DUR"] = roundInt(a.MAX_SAMPLE_DUR * 1000)

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_FILE)

# samples = addIndices(samples)
samples = addNormalizedValues(samples, "clarity", "nclarity")
samples = addNormalizedValues(samples, "power", "npower")

def getPhraseDur(samples):
    start = samples[0]["start"]
    dur = samples[-1]["start"] + samples[-1]["dur"] - start
    return (start, dur)

def getPhraseFeatures(samples, clarityKey="clarity", powerKey="power"):
    # weights = [s["dur"] for s in samples]
    # clarity = np.average([s[clarityKey] for s in samples], weights=weights)
    # power = np.average([s[powerKey] for s in samples], weights=weights)
    clarity = np.median([s[clarityKey] for s in samples])
    power = np.median([s[powerKey] for s in samples])
    return (clarity, power)

def addPhrase(phrases, phrase):
    global a

    count = len(phrase)
    if count < a.MIN_SAMPLES:
        return phrases

    # remove samples at the end that don't reach threshold
    for i in range(count):
        index = count - i - 1
        s = phrase[index]
        if s["nclarity"] >= a.CLARITY_THRESHOLD and s["npower"] >= a.POWER_THRESHOLD:
            break
        else:
            phrase.pop()

    # not enough samples
    if len(phrase) < a.MIN_SAMPLES:
        return phrases

    start, dur = getPhraseDur(phrase)
    # check for valid duration
    if a.MIN_DUR <= dur:
        clarity, power = getPhraseFeatures(phrase)
        mdur = np.median([s["dur"] for s in phrase])
        phrases.append({
            "filename": phrase[0]["filename"],
            "start": start,
            "dur": dur,
            "count": len(phrase),
            "clarity": round(clarity, 3),
            "power": round(power, 3),
            "medianDur": roundInt(mdur),
            "samples": phrase
        })

    return phrases

phrases = []
currentPhrase = []

for i, s in enumerate(samples):
    # sample is too long; check for phrase and continue
    if s["dur"] > a.MAX_SAMPLE_DUR:
        phrases = addPhrase(phrases, currentPhrase)
        currentPhrase = []
        continue

    # the first sample in a phrase must pass our criteria
    if len(currentPhrase) < 1:
        if s["nclarity"] >= a.CLARITY_THRESHOLD and s["npower"] >= a.POWER_THRESHOLD:
            currentPhrase.append(s)
        continue

    # check if current phrase is too long
    start, dur = getPhraseDur(currentPhrase)
    if dur >= a.MAX_DUR:
        phrases = addPhrase(phrases, currentPhrase)
        currentPhrase = []

    # add sample to current phrase
    currentPhrase.append(s)

    # we need to collect enough samples to analyze
    if len(currentPhrase) < a.BUFFER_SIZE:
        continue

    buffer = currentPhrase[:]
    if len(currentPhrase) > a.BUFFER_SIZE:
        buffer = currentPhrase[-a.BUFFER_SIZE:]

    clarity, power = getPhraseFeatures(buffer, "nclarity", "npower")

    # we've reached the end of a phrase, add it
    if clarity < a.CLARITY_THRESHOLD or power < a.POWER_THRESHOLD:
        phrases = addPhrase(phrases, currentPhrase)
        currentPhrase = []

# Add the last phrase
phrases = addPhrase(phrases, currentPhrase)
if len(phrases) < 1:
    print("No phrases found")
    sys.exit()

# Filter based on clarity
phrases = [p for p in phrases if p["clarity"] >= a.MIN_PHRASE_CLARITY]
if len(phrases) < 1:
    print("No phrases with clarity > %s" % a.MIN_PHRASE_CLARITY)
    sys.exit()

phrases = sorted(phrases, key=lambda s: -s["clarity"])

if a.MAX_PHRASES > 0 and len(phrases) > a.MAX_PHRASES:
    phrases = phrases[:a.MAX_PHRASES]

if a.MAX_SAMPLES > 0:
    sampleTotal = 0
    validPhrases = []
    for p in phrases:
        sampleTotal += p["count"]
        if sampleTotal > a.MAX_SAMPLES:
            break
        validPhrases.append(p)
    phrases = validPhrases[:]

phrases = addIndices(phrases, "rank", 1)
phrases = sorted(phrases, key=lambda s: s["start"])
print("Found %s valid phrases" % len(phrases))

if a.PROBE:
    runningTotal = 0
    runningDur = 0
    for i, phrase in enumerate(phrases):
        runningTotal += phrase["count"]
        runningDur += phrase["dur"]
        print("%s. %s -> %s dur[%s] count[%s] clarity[%s] power[%s] total[%s] running[%s] rank[%s]" % (i+1, formatSeconds(phrase["start"]/1000.0), formatSeconds(phrase["start"]/1000.0+phrase["dur"]/1000.0), formatSeconds(phrase["dur"]/1000.0), phrase["count"], round(phrase["clarity"], 2), round(phrase["power"], 2), runningTotal, formatSeconds(runningDur/1000.0), phrase["rank"]))
    sys.exit()

headings = ["filename", "start", "dur", "count", "clarity", "power", "medianDur"]
writeCsv(a.OUTPUT_FILE, phrases, headings=headings)
print("Done.")
