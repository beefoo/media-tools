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

FILE_A = "../media/sample/tone_scale.wav"
FILE_B = "../media/sample/telephone_noise.wav"

def getSamples(fn):
    y, sr = librosa.load(fn)
    samples = getAudioSamples(fn, y=y, sr=sr)
    for j, s in enumerate(samples):
        features = getFeatures(y, sr, s["start"], dur=s["dur"])
        samples[j].update(features)
    return samples

SAMPLES_A = getSamples(FILE_A)
SAMPLES_B = getSamples(FILE_B)

print(SAMPLES_A[0]["flatness"])
print(SAMPLES_B[0]["flatness"])

plt.figure(figsize=(20, 8))
plt.plot([s["flatness"] for s in SAMPLES_A], c="r", label="Tone-like (low value)")
plt.plot([s["flatness"] for s in SAMPLES_B], c="b", label="Noise-like (high value)")
plt.show()
