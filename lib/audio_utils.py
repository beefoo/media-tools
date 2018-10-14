import librosa
import math
from math_utils import weighted_mean
import numpy as np
import os
from pprint import pprint
import re
import subprocess

def getAudioFile(fn):
    format = fn.split(".")[-1]
    # if this is an .mp4, convert to .mp3
    if format == "mp4":
        target = fn.replace(".mp4", ".mp3")
        if not os.path.isfile(target):
            command = ['ffmpeg',
                '-i', fn,
                '-ar', '44100', # for defining sample rate
                '-q:a', '0', # for variable bitrate
                '-map', 'a', target]
            print(" ".join(command))
            finished = subprocess.check_call(command)
        fn = target
    return fn

def getAudioSamples(fn, min_dur=50, max_dur=-1, fft=2048, hop_length=512):
    basename = os.path.basename(fn)
    fn = getAudioFile(fn)

    # load audio
    y, sr = librosa.load(fn)
    y /= y.max()
    ylen = len(y)
    duration = int(round(ylen / sr * 1000))

    # retrieve onsets
    onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
    times = [int(round(1.0 * hop_length * onset / sr * 1000)) for onset in onsets]

    # add the end of the audio
    times.append(duration-1)

    samples = []
    for i, t in enumerate(times):
        prev = times[i-1] if i > 0 else 0
        dur = t - prev
        if dur >= min_dur and (max_dur <= 0 or dur <= max_dur):
            samples.append({
                "filename": basename,
                "start": prev,
                "dur": dur
            })

    return samples

def getFeatures(y, sr, start, dur, fft=2048, hop_length=512):
    # analyze just the sample
    i0 = int(round(start / 1000.0 * sr))
    i1 = int(round((start+dur) / 1000.0 * sr))
    y = y[i0:i1]

    stft = librosa.feature.rmse(S=librosa.stft(y, n_fft=fft, hop_length=hop_length))[0]
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]

    power = round(weighted_mean(stft), 2)
    hz = round(weighted_mean(rolloff), 2)
    note = "-"

    if math.isinf(power):
        power = -1

    try:
        note = librosa.hz_to_note(hz)
    except OverflowError:
        hz = -1

    # parse note
    octave = -1
    matches = re.match("([A-Z]\#?b?)(\-?[0-9]+)", note)
    if matches:
        note = matches.group(1)
        octave = int(matches.group(2))

    return {
        "power": power,
        "hz": hz,
        "note": note,
        "octave": octave
    }


# Taken from: https://github.com/ml4a/ml4a-guides/blob/master/notebooks/audio-tsne.ipynb
def getFeatureVector(y, sr, start, dur):

    # take at most one second
    dur = min(dur, 1000)

    # analyze just the sample
    i0 = int(round(start / 1000.0 * sr))
    i1 = int(round((start+dur) / 1000.0 * sr))
    y = y[i0:i1]

    S = librosa.feature.melspectrogram(y, sr=sr, n_mels=128)
    log_S = librosa.amplitude_to_db(S, ref=np.max)
    mfcc = librosa.feature.mfcc(S=log_S, n_mfcc=13)
    delta_mfcc = librosa.feature.delta(mfcc, mode='nearest')
    delta2_mfcc = librosa.feature.delta(mfcc, order=2, mode='nearest')
    feature_vector = np.concatenate((np.mean(mfcc,1), np.mean(delta_mfcc,1), np.mean(delta2_mfcc,1)))
    feature_vector = (feature_vector-np.mean(feature_vector))/np.std(feature_vector)
    return feature_vector
