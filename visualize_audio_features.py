# -*- coding: utf-8 -*-

# https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html

import argparse
import audioread
from lib.audio_utils import *
from lib.collection_utils import *
from lib.color_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import librosa
import librosa.display
import matplotlib.pyplot as plt
import os
from PIL import Image, ImageDraw
import numpy as np
from pprint import pprint
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/sample/LivingSt1958.mp4", help="Input file")
parser.add_argument('-ss', dest="AUDIO_START", default=0.0, type=float, help="Start in seconds")
parser.add_argument('-sd', dest="AUDIO_DUR", default=-1.0, type=float, help="Duration of audio clip in seconds; -1 for the rest of the audio")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/viz/viz_%s.png", help="Output file pattern")
parser.add_argument('-width', dest="WIDTH", default=1200, type=int, help="Width of output images")
parser.add_argument('-height', dest="HEIGHT", default=400, type=int, help="Height of output images")
parser.add_argument('-log', dest="USE_LOG", action="store_true", help="Use log for spectrogram?")
a = parser.parse_args()

makeDirectories(a.OUTPUT_FILE)

# get audio data
y, sr = loadAudioData(a.INPUT_FILE)
start = roundInt(a.AUDIO_START * 1000)
totalDur = int(getDurationFromAudioData(y, sr) * 1000)
dur = roundInt(a.AUDIO_DUR * 1000)
if dur <= 0:
    dur = totalDur - start
# analyze just the sample
i0 = int(round(start / 1000.0 * sr))
i1 = int(round((start+dur) / 1000.0 * sr))
y = y[i0:i1]

# init plot
dpi = 96.0
axisLabelPadding = 6
figWidth = a.WIDTH / dpi
figHeight = a.HEIGHT / dpi
fontSize = 18
titleFontSize = fontSize * 1.2
plt.style.use('bmh')

# 1. onset detection
fig = plt.figure(figsize=(figWidth, figHeight), dpi=dpi, tight_layout=True)
ax = fig.add_subplot(1, 1, 1)
# ax.set_title('Onsets on audio waveform', fontsize=titleFontSize)
ax.set_xlabel('Time', fontsize=fontSize, labelpad=axisLabelPadding)
ax.set_ylabel('Amplitude', fontsize=fontSize, labelpad=axisLabelPadding)
fft = 2048
hop_length = 512
n_mels = 138
fmin = 0
fmax = 8192
max_size = 3
lag = 2
delta = 0.07
min_dur = 0.05
mels = librosa.feature.melspectrogram(y, sr=sr, n_fft=fft, hop_length=hop_length, fmin=fmin, fmax=fmax, n_mels=n_mels)
odf = librosa.onset.onset_strength(S=librosa.power_to_db(mels, ref=np.max), sr=sr, hop_length=hop_length, lag=lag, max_size=max_size)
onsets = librosa.onset.onset_detect(onset_envelope=odf, sr=sr, hop_length=hop_length, backtrack=True, delta=delta)
times = [1.0 * hop_length * onset / sr for onset in onsets]
filteredTimes = []
for i, t in enumerate(times):
    if i > 0:
        prev = filteredTimes[-1]
        dur = t - prev
        if dur > min_dur:
            filteredTimes.append(t)
    else:
        filteredTimes.append(t)
waveplot = librosa.display.waveplot(y, sr=sr, ax=ax, x_axis=None)
ymin, ymax = ax.get_ylim()
# Turn off tick labels
ax.set_yticks([])
ax.set_yticklabels([])
# Add onsets and legend
ax.vlines(filteredTimes, ymin, ymax, color='r', label='Onsets')
ax.legend()
fig.savefig(a.OUTPUT_FILE % "01_onsets")

# 1. Make spectrogram image
# fft = 2048
# hop_length = 512
# n_mels = 138
# fmin = 0
# fmax = 8192

# mels = librosa.feature.melspectrogram(y, sr=sr, n_fft=fft, hop_length=hop_length, fmin=fmin, fmax=fmax, n_mels=n_mels)
# logMels = np.log(mels + 1e-9)
# nmels = (logMels - logMels.min()) / (logMels.max() - logMels.min())
# nmels = np.flip(nmels, axis=0)
# spectrogramPixels = getColorGradientMatrix(nmels, name="inferno", easingFunction="cubicIn")
# spectrogramImg = Image.fromarray(spectrogramPixels, mode="RGB")
# # spectrogramPixels = nmels * 255
# # spectrogramImg = Image.fromarray(spectrogramPixels.astype(np.uint8), mode="L")
# spectrogramImg.save(a.OUTPUT_FILE % "01_spectrogram")

# D = librosa.amplitude_to_db(np.abs(librosa.stft(y, hop_length=hop_length)), ref=np.max)
# im = librosa.display.specshow(D, y_axis='log', sr=sr, hop_length=hop_length, x_axis='time')
# fig = im.get_figure()
# fig.savefig(a.OUTPUT_FILE % "01_spectrogram_alt")
