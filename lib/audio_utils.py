import librosa
import os
from pprint import pprint
from pydub import AudioSegment

def getAudioSamples(fn, min_dur=50, max_dur=-1, fft=2048, hop_length=512):
    basename = os.path.basename(fn)

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
