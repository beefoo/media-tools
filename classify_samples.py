# -*- coding: utf-8 -*-

# Adapted from: https://github.com/googlecreativelab/aiexperiments-drum-machine/blob/master/scripts/analysis.py

import argparse
from lib.audio_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import os
import pickle
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/samples.csv", help="Input file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/samples_classified.csv", help="CSV output file")
parser.add_argument('-groups', dest="GROUPS", default="orchestra,speech", help="Comma-separated list of groups")
parser.add_argument('-rdir', dest="REF_DIR", default="media/classifications/", help="Directory where reference files are")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
a = parser.parse_args()

GROUPS = a.GROUPS.strip().split(",")
OVERWRITE = a.OVERWRITE > 0

# Read files
fieldNames, samples = readCsv(a.INPUT_FILE)
sampleCount = len(samples)

for group in GROUPS:
    if group not in set(fieldNames):
        fieldNames.append(group)

# Make sure output dirs exist
makeDirectories([a.REF_DIR, a.OUTPUT_FILE])

# Analyze reference audio
analysis = {}
for group in GROUPS:
    refDir = a.REF_DIR + group + "/"
    analysisFile = a.REF_DIR + group + ".p"
    analysisData = []
    if os.path.isfile(analysisFile) and not OVERWRITE:
        analysisData = pickle.load(open(analysisFile, 'rb'))
        print("Loaded %s analysis from file" % group)

    if len(analysisData) <= 0:
        refFilenames = getFilesInDir(refDir)
        for fn in refFilenames:
            analysisData.append(analyzeAudio(fn, findSamples=True))
        pickle.dump(analysisData, open(analysisFile, 'wb'))
        print("Wrote %s analysis to file" % group)

    analysis[group] = analysisData

print("Calculating similarities...")
# Find the similarity of each sample to each group
for i, s in enumerate(samples):
    fn = a.MEDIA_DIRECTORY + s["filename"]
    sampleAnalysis = analyzeAudio(fn, start=s["start"])

    for group in GROUPS:
        groupAnalysis = analysis[group]
        similarity = getAudioSimilarity(sampleAnalysis, groupAnalysis)
        samples[i][group] = similarity

    # progressively save
    writeCsv(a.OUTPUT_FILE, samples, headings=fieldNames)
    printProgress(i+1, sampleCount)
