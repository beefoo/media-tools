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
parser.add_argument('-max', dest="MAX_DUR", default=-1, type=float, help="Maximum phrase duration in seconds")
parser.add_argument('-mins', dest="MIN_SAMPLES", default=8, type=int, help="At least this many samples per phrase")
parser.add_argument('-msd', dest="MAX_SAMPLE_DUR", default=5, type=float, help="Maximum sample duration in seconds")
parser.add_argument('-clarity', dest="CLARITY_THRESHOLD", default=0.4, type=float, help="Mean should be above this clarity")
parser.add_argument('-power', dest="POWER_THRESHOLD", default=0.125, type=float, help="Mean be above this power")
parser.add_argument('-buffer', dest="BUFFER_SIZE", default=4, type=int, help="Analyze this many samples")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/phrases.csv", help="Output csv file")
a = parser.parse_args()
aa = vars(a)

aa["MIN_DUR"] = roundInt(a.MIN_DUR * 1000)
aa["MAX_DUR"] = roundInt(a.MAX_DUR * 1000)
aa["MAX_SAMPLE_DUR"] = roundInt(a.MAX_SAMPLE_DUR * 1000)

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)

# samples = addIndices(samples)
samples = addNormalizedValues(samples, "clarity", "nclarity")
samples = addNormalizedValues(samples, "power", "npower")

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

    start = phrase[0]["start"]
    dur = phrase[-1]["start"] + phrase[-1]["dur"] - start
    maxDur = a.MAX_DUR if a.MAX_DUR > 0 else dur
    # check for valid duration
    if a.MIN_DUR <= dur <= maxDur:
        phrases.append({
            "start": start,
            "dur": dur,
            "count": len(phrase),
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

    # add sample to current phrase
    currentPhrase.append(s)

    # we need to collect enough samples to analyze
    if len(currentPhrase) < a.BUFFER_SIZE:
        continue

    buffer = currentPhrase[:]
    if len(currentPhrase) > a.BUFFER_SIZE:
        buffer = currentPhrase[-a.BUFFER_SIZE:]

    # weight the averages based on duration of sample
    weights = [b["dur"] for b in buffer]
    meanClarity = np.average([b["nclarity"] for b in buffer], weights=weights)
    meanPower = np.average([b["npower"] for b in buffer], weights=weights)

    # we've reached the end of a phrase, add it
    if meanClarity < a.CLARITY_THRESHOLD or meanPower < a.POWER_THRESHOLD:
        phrases = addPhrase(phrases, currentPhrase)
        currentPhrase = []

# Add the last phrase
phrases = addPhrase(phrases, currentPhrase)

for phrase in phrases:
    print("%s -> %s (%s)" % (formatSeconds(phrase["start"]/1000.0), formatSeconds(phrase["start"]/1000.0+phrase["dur"]/1000.0), phrase["count"]))
