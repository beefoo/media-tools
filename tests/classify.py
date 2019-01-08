# -*- coding: utf-8 -*-

import argparse
import inspect
import os
import pickle
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *

CLASSIFICATIONS = [
    "../media/classifications/orchestra.p",
    "../media/classifications/speech.p"
]
TESTS = [
    "../media/downloads/orchestra.wav",
    "../media/downloads/gov.archives.arc.1257658_male.mp3"
]

classificationData = {}
for c in CLASSIFICATIONS:
    key = os.path.basename(c)
    classificationData[key] = pickle.load(open(c, 'rb'))

for fn in TESTS:
    sampleAnalysis = analyzeAudio(fn, findSamples=True)
    basename = os.path.basename(fn)
    print("-----\n%s:" % basename)

    for c in classificationData:
        groupAnalysis = classificationData[c]
        for i, a in enumerate(groupAnalysis):
            similarity = getAudioSimilarity(sampleAnalysis, [a])
            print("%s: (%s) %s" % (c, i+1, similarity))
