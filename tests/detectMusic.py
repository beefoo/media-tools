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
    "../media/sample/drums.wav"
]

plt.figure(figsize=(27, 8))

for i, fn in enumerate(files):
    y, sr = librosa.load(fn)
    print("Duration: %s" % formatSeconds(getDuration(y, sr)))
    y_harmonic, y_percussive = librosa.effects.hpss(y, margin=4)

    # show spectrogram
    plt.subplot(2, 3, i*3+1)
    S = librosa.feature.melspectrogram(y, sr=sr)
    librosa.display.specshow(librosa.power_to_db(S, ref=np.max), y_axis='mel', x_axis='time')

    # show harmonic spectrogram
    plt.subplot(2, 3, i*3+2)
    S = librosa.feature.melspectrogram(y_harmonic, sr=sr)
    librosa.display.specshow(librosa.power_to_db(S, ref=np.max), y_axis='mel', x_axis='time')

    # show harmonic spectrogram
    plt.subplot(2, 3, i*3+3)
    # S = librosa.feature.melspectrogram(y_percussive, sr=sr)
    # librosa.display.specshow(librosa.power_to_db(S, ref=np.max), y_axis='mel', x_axis='time')
    contrast = librosa.feature.spectral_contrast(y=y_harmonic, sr=sr)
    librosa.display.specshow(contrast, x_axis='time')

plt.tight_layout()
plt.show()
