# -*- coding: utf-8 -*-

import inspect
import librosa
from librosa import display
from matplotlib import pyplot as plt
import numpy as np
import os
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *
from lib.math_utils import *

FILE_A = "../media/sample/chromatic_scale_piano_c4-b4.wav"
FILE_B = "../media/sample/drums.wav"

def getSamples(fn):
    y, sr = librosa.load(fn)
    samples = getAudioSamples(fn, y=y, sr=sr)
    for j, s in enumerate(samples):
        features = getFeatures(y, sr, s["start"], dur=s["dur"])
        samples[j].update(features)
    return samples

SAMPLES_A = getSamples(FILE_A)
SAMPLES_B = getSamples(FILE_B)

plt.figure(figsize=(20, 8))
plt.plot([s["clarity"] for s in SAMPLES_A], c="r", label=os.path.basename(FILE_A))
plt.plot([s["clarity"] for s in SAMPLES_B], c="b", label=os.path.basename(FILE_B))
plt.legend()
plt.show()
