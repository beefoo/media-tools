# -*- coding: utf-8 -*-

import argparse
from lib import stretchSound
from matplotlib import pyplot as plt
import numpy as np
import os
from pprint import pprint
from pydub import AudioSegment
import scipy.io.wavfile
import sys

filename = "audio/downloads/vivaldi/08_-_Vivaldi_Autumn_mvt_2_Adagio_molto.mp3"
fformat = filename.split(".")[-1]
audio = AudioSegment.from_file(filename, format=fformat)
audio = audio[100171:(100171+511)]
audio = stretchSound(audio, 2.5342024722763226)

baseAudio = AudioSegment.silent(duration=10000, frame_rate=audio.frame_rate)
baseAudio = baseAudio.set_channels(audio.channels)
baseAudio = baseAudio.set_sample_width(audio.sample_width)
baseAudio = baseAudio.overlay(audio, position=500)
baseAudio.export("output/stretch_test.mp3", format="mp3")

# def showAudioPlot(y, figsize=(30,3), downsample=100):
#     # plot the raw waveform
#     plt.figure(figsize=figsize)
#     plt.plot(y[::downsample])
#     plt.xlim([0, len(y)/downsample])
#     plt.show()
#     # plt.close()
#
# def dubRead(filename):
#     fformat = filename.split(".")[-1]
#     audio = AudioSegment.from_file(filename, format=fformat)
#     channels = audio.channels
#     frame_rate = audio.frame_rate
#     samples = np.array(audio.get_array_of_samples())
#     samples = samples.astype(np.int16)
#     samples = samples * (1.0/32768.0)
#     samples = samples.reshape(2, len(samples)/2, order='F')
#     print("PyDub = channels: %s, frame rate: %s" % (channels, frame_rate))
#     print(samples.shape)
#     print(type(samples[0][0]))
#     # print("Shape: %s" % samples.shape)
#
#     return frame_rate, samples
#
# def sciRead(filename):
#     audio = scipy.io.wavfile.read(filename)
#     frame_rate = int(audio[0])
#     samples = audio[1]*(1.0/32768.0)
#     samples = samples.transpose()
#
#     channels = len(samples.shape)
#     # print(audio[1][0])
#     print("Scipy = channels: %s, frame rate: %s" % (channels, frame_rate))
#     print(samples.shape)
#     print(type(samples[0][0]))
#
#     return frame_rate, samples
#
#
#     # smp = wavedata[1]*(1.0/32768.0)
#     # smp = smp.transpose()
#     # if len(smp.shape)==1: #convert to stereo
#     #     smp=tile(smp,(2,1))
#
# filename = "audio/sample/bird.wav"
# sr, smp = dubRead(filename)
# # showAudioPlot(smp[0])
# sr, smp = sciRead(filename)
# # showAudioPlot(smp[0])
#
# audio = paulStretch(sr, smp, 2.0, windowsize_seconds=0.25, onset_level=10.0)

# print(audio.shape)
# showAudioPlot(audio)

# audio = audio[:1000]
#
