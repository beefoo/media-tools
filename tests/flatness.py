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

files = [
    "../media/sample/chromatic_scale_piano_c4-b4.wav",
    "../media/sample/drums.wav",
    "../media/sample/bird.wav",
    "../media/sample/telephone_noise.wav",
    "../media/sample/tone_scale.wav",
    "../media/classifications/orchestra/gov.archives.arc.24348.mp3",
    "../media/classifications/speech/gov.archives.arc.45021_male.mp3"
]

def getSamples(fn):
    y, sr = librosa.load(fn)
    samples = getAudioSamples(fn, y=y, sr=sr)
    for j, s in enumerate(samples):
        features = getFeatures(y, sr, s["start"], dur=s["dur"])
        samples[j].update(features)
    return samples

plt.figure(figsize=(20, 8))

for i, fn in enumerate(files):
    samples = getSamples(fn)
    plt.plot([s["clarity"] for s in samples], label=os.path.basename(fn))

plt.legend()
plt.show()
