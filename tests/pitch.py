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
    {
        "filename": "../media/sample/chromatic_scale_bells_c6-c7.wav",
        "scale": ["C6", "C#6", "D6", "D#6", "E6", "F6", "F#6", "G6", "G#6", "A6", "A#6", "B6", "C7"],
        "source": "https://freesound.org/people/InspectorJ/sounds/339823/"
    },{
        "filename": "../media/sample/chromatic_scale_piano_c4-b4.wav",
        "scale": ["C4", "C#4", "D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4"],
        "source": "https://freesound.org/people/Nerkamitilia/sounds/369930/"
    }

]

plt.figure(figsize=(27, 8))
fileCount = len(files)
n_mels = 138
fmin = 27.5
fmax = 16000.0
fft=2048
hop_length=512
colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']
colorCount = len(colors)

for i, f in enumerate(files):
    fn = f["filename"]
    scale = f["scale"]
    print("Loading %s..." % fn)

    y, sr = librosa.load(fn)

    print("Duration: %s" % formatSeconds(getDuration(y, sr)))

    samples = getAudioSamples(fn, y=y, sr=sr)
    print("Found %s samples, expected %s" % (len(samples), len(scale)))

    for j, s in enumerate(samples):
        features = getFeatures(y, sr, s["start"], dur=s["dur"])
        samples[j].update(features)

        if j < len(scale):
            actualNote = scale[j]
            note = features["note"] + str(features["octave"])
            equality = "==" if actualNote == note else "!="
            print("%s %s %s" % (note, equality, actualNote))

    # plot the rmse and thresholded rmse
    plt.subplot(2, fileCount, i*2+1)
    S = librosa.stft(y, n_fft=fft, hop_length=hop_length)
    e = librosa.feature.rmse(S=S)[0]
    plt.plot(e)

    # highlight onsets
    for j, s in enumerate(samples):
        frame = msToFrame(s["start"], sr)
        x = 1.0 * frame / hop_length
        plt.axvline(x=x, color="red")
        frame = msToFrame(s["start"]+s["dur"], sr)
        x = 1.0 * frame / hop_length
        plt.axvline(x=x, color="green")

    plt.subplot(2, fileCount, i*2+2)
    # plot spectogram
    S = librosa.feature.melspectrogram(y, sr=sr, n_fft=fft, hop_length=hop_length, fmin=fmin, fmax=fmax, n_mels=n_mels)
    librosa.display.specshow(librosa.power_to_db(S, ref=np.max), y_axis='mel', fmax=fmax, x_axis='time')

    # highlight notes
    for j, s in enumerate(samples):
        x = [s["start"]/1000.0, (s["start"]+s["dur"])/1000.0]
        y = [s["hz"], s["hz"]]
        plt.plot(x, y, color="green")
        # for k, hz in enumerate(s["harmonics"]):
        #     if k >= 3:
        #         break
        #     y = [hz, hz]
        #     color = colors[k % colorCount]
        #     plt.plot(x, y, color=color)

plt.tight_layout()
plt.show()
