import array
import audioop
import librosa
import math
from lib.collection_utils import *
from lib.math_utils import *
from lib.processing_utils import *
import numpy as np
import os
from PIL import Image
from pprint import pprint
import pydub
from pydub import AudioSegment
from pysndfx import AudioEffectsChain
import re
import subprocess
import sys

def addFx(sound, effects, pad=3000, fade_in=100, fade_out=100):
    # Add padding
    if pad > 0:
        sound += AudioSegment.silent(duration=pad, frame_rate=sound.frame_rate)

    # convert pydub sound to np array
    samples = np.array(sound.get_array_of_samples())
    samples = samples.astype(np.int16)

    chain = AudioEffectsChain()
    for effect, value in effects:
        if effect == "reverb":
            chain.reverb(reverberance=value)
        elif effect == "distortion":
            chain.overdrive(gain=value)
        elif effect == "highpass":
            chain.highpass(value)
        elif effect == "lowpass":
            chain.lowpass(value)
        elif effect == "bass":
            chain.lowshelf(gain=value)
        elif effect == "echo":
            echoStr = "echo 0.8 0.9"
            amount = value
            count = 1
            # check if we have echo count indicated
            if isinstance(value, tuple):
                amount, count = value
            for i in range(count):
                # amount between 10 (robot) and 1000 (mountains)
                echoStr += " %s 0.3" % amount
            chain.custom(echoStr)

    # apply reverb effect
    fx = (chain)
    y = fx(samples)

    # convert it back to an array and create a new sound clip
    newData = array.array(sound.array_type, y)
    newSound = sound._spawn(newData)
    dur = len(newSound)
    newSound = newSound.fade_in(min(fade_in, dur)).fade_out(min(fade_out, dur))
    return newSound

def analyzeAudio(fn, start=0, dur=250, findSamples=False):
    y, sr = loadAudioData(fn)
    if findSamples:
        samples, y, sr = getAudioSamples(fn, y=y, sr=sr)
        if len(samples) > 0:
            print("Found %s samples for %s" % (len(samples), fn))
            start = samples[0]["start"]
        else:
            print("No samples for %s" % fn)
    start = start / 1000.0
    dur = dur / 1000.0
    i0 = max(0, roundInt(start * sr))
    i1 = min(i0 + roundInt(dur * sr), len(y)-1)
    y = y[i0:i1]

    centroid = scaleAudioData(librosa.feature.spectral_centroid(y=y, sr=sr))
    bandwidth = scaleAudioData(librosa.feature.spectral_bandwidth(y=y, sr=sr))
    return np.asarray([centroid, bandwidth])

def applyAudioProperties(audio, props, sfx=True, fxPad=3000):
    p = props
    if "matchDb" in p and p["matchDb"] > -9999:
        maxMatchDb = p["maxMatchDb"] if "maxMatchDb" in p else -1
        audio = matchDb(audio, p["matchDb"], maxMatchDb)
    if "maxDb" in p and p["maxDb"] > -9999:
        audio = maxDb(audio, p["maxDb"])
    if "reverse" in p and p["reverse"]:
        audio = audio.reverse()
    if "db" in p and p["db"] != 0.0:
        audio = audio.apply_gain(p["db"])
    if "pan" in p and p["pan"] != 0.0:
        audio = audio.pan(p["pan"])
    if "fadeIn" in p and p["fadeIn"] > 0:
        audio = audio.fade_in(p["fadeIn"])
    if "fadeOut" in p and p["fadeOut"] > 0:
        audio = audio.fade_out(p["fadeOut"])
    if sfx:
        if "stretch" in p and p["stretch"] > 1.0:
            audio = stretchSound(audio, p["stretch"])
        elif "stretchTo" in p and p["stretchTo"] > p["dur"]:
            stretchAmount = 1.0 * p["stretchTo"] / p["dur"]
            audio = stretchSound(audio, stretchAmount)
        effects = []
        for effect in ["reverb", "distortion", "highpass", "lowpass"]:
            if effect in p and p[effect] > 0:
                effects.append((effect, p[effect]))
        if len(effects) > 0:
            audio = addFx(audio, effects, pad=fxPad)
    return audio

def audioFingerprintsToImage(fingerprints, filename, cols, rows, width, height, bgcolors=None):
    pixels = np.zeros((height, width), dtype=np.uint8)
    bgpixels = None
    if bgcolors is not None:
        bgpixels = np.zeros((height, width, 3), dtype=np.uint8)
    cellW = int(1.0 * width / cols)
    cellH = int(1.0 * height / rows)
    for row in range(rows):
        for col in range(cols):
            index = row * cols + col
            fingerprint = np.round(np.array(fingerprints[index]) * 255.0)
            fingerprint = fingerprint.astype(np.uint8)
            fh, fw = fingerprint.shape
            if fh != cellH or fw != cellW:
                fingerprint = resizeMatrix(fingerprint, (cellH, cellW))
            x0 = col * cellW
            x1 = x0 + cellW
            y0 = row * cellH
            y1 = y0 + cellH
            pixels[y0:y1, x0:x1] = fingerprint
            if bgpixels is not None:
                bgpixels[y0:y1, x0:x1] = bgcolors[index]
    im = Image.fromarray(pixels, mode="L")
    if bgpixels is not None:
        bgIm = Image.fromarray(bgpixels, mode="RGB")
        overlayIm = Image.new(mode="RGB", size=(height, height), color=(0, 0, 0))
        im = Image.composite(bgIm, overlayIm, im)
    im.save(filename)
    # if dmismatch:
    #     print("Warning: fingerprint dimensions differs from cell dimensions")

# Note: sample_width -> bit_depth conversions: 1->8, 2->16, 3->24, 4->32
# 24/32 bit depth and 48K sample rates are industry standards
def getAudio(filename, sampleWidth=4, sampleRate=48000, channels=2, verbose=True):
    # A hack: always read files at 16-bit depth because Sox does not support more than that
    sampleWidth = 2
    audiofilename = getAudioFile(filename)
    # fformat = audiofilename.split(".")[-1].lower()
    # audio = AudioSegment.from_file(audiofilename, format=fformat)
    try:
        audio = AudioSegment.from_file(audiofilename)
    # https://github.com/jiaaro/pydub/issues/415
    except pydub.exceptions.CouldntDecodeError:
        audio = AudioSegment.from_file_using_temporary_files(audiofilename)

    # convert to stereo
    if audio.channels != channels:
        if verbose:
            print("Warning: channels changed to %s from %s in %s" % (channels, audio.channels, filename))
        audio = audio.set_channels(channels)
    # convert sample width
    if audio.sample_width != sampleWidth:
        if verbose:
            print("Warning: sample width changed to %s from %s in %s" % (sampleWidth, audio.sample_width, filename))
        audio = audio.set_sample_width(sampleWidth)
    # convert sample rate
    if audio.frame_rate != sampleRate:
        if verbose:
            print("Warning: frame rate changed to %s from %s in %s" % (sampleRate, audio.frame_rate, filename))
        audio = audio.set_frame_rate(sampleRate)
    return audio

def getAudioClip(audio, clipStart, clipDur, audioDurationMs=None, clipFadeIn=10, clipFadeOut=10):
    audioDurationMs = audioDurationMs if audioDurationMs is not None else len(audio)
    clipEnd = None
    if clipDur > 0:
        clipEnd = clipStart + clipDur
    else:
        clipEnd = audioDurationMs
    # check bounds
    clipStart = lim(clipStart, (0, audioDurationMs))
    clipEnd = lim(clipEnd, (0, audioDurationMs))
    if clipStart >= clipEnd:
        return None

    newClipDur = clipEnd - clipStart
    clip = audio[clipStart:clipEnd]

    # add a fade in/out to avoid clicking
    fadeInDur = min(clipFadeIn, newClipDur)
    fadeOutDur = min(clipFadeOut, newClipDur)
    clip = clip.fade_in(fadeInDur).fade_out(fadeOutDur)

    return clip

def getAudioFile(fn, samplerate=48000):
    # format = fn.split(".")[-1]
    # # if this is an .mp4, convert to .mp3
    # if format == "mp4":
    #     target = fn.replace(".mp4", ".mp3")
    #     if not os.path.isfile(target):
    #         command = ['ffmpeg',
    #             '-i', fn,
    #             '-ar', str(samplerate), # for defining sample rate
    #             '-q:a', '0', # for variable bitrate
    #             '-map', 'a', target]
    #         print(" ".join(command))
    #         finished = subprocess.check_call(command)
    #     fn = target
    return fn

def getAudioSamples(fn, min_dur=50, max_dur=-1, fft=2048, hop_length=512, backtrack=True, superFlux=True, y=None, sr=None, delta=0.07):
    basename = os.path.basename(fn)
    fn = getAudioFile(fn)
    duration = 0

    # load audio
    if y is None or sr is None:
        try:
            y, sr = loadAudioData(fn)
            duration = int(getDurationFromAudioData(y, sr) * 1000)
        except audioop.error:
            duration = 0
            y = None
            sr = None

    # maxVal = y.max()
    # if maxVal != 0:
    #     y /= maxVal

    if duration <= 0:
        return ([], y, sr)

    # retrieve onsets using superflux method
    # https://librosa.github.io/librosa/auto_examples/plot_superflux.html#sphx-glr-auto-examples-plot-superflux-py
    # http://dafx13.nuim.ie/papers/09.dafx2013_submission_12.pdf
    if superFlux:
        lag = 2
        n_mels = 138
        fmin = 27.5
        fmax = 16000.0
        max_size = 3
        S = librosa.feature.melspectrogram(y, sr=sr, n_fft=fft, hop_length=hop_length, fmin=fmin, fmax=fmax, n_mels=n_mels)
        odf = librosa.onset.onset_strength(S=librosa.power_to_db(S, ref=np.max), sr=sr, hop_length=hop_length, lag=lag, max_size=max_size)
        onsets = librosa.onset.onset_detect(onset_envelope=odf, sr=sr, hop_length=hop_length, backtrack=backtrack, delta=delta)

    # retrieve onsets using default method
    else:
        onsets = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length, backtrack=backtrack, delta=delta)

    times = [int(round(1.0 * hop_length * onset / sr * 1000)) for onset in onsets]
    # add the end of the audio
    times.append(duration-1)

    samples = []
    for i, t in enumerate(times):
        if i > 0:
            prev = times[i-1]
            dur = t - prev
            if max_dur > 0 and dur > max_dur:
                dur = max_dur
            if dur >= min_dur:
                samples.append({
                    "filename": basename,
                    "start": prev,
                    "dur": dur
                })

    return (samples, y, sr)

def getAudioSimilarity(test, references):
    refCount = len(references)
    if refCount <= 0:
        print("Warning: no references found.")
        return 0
    sumValue = 0
    for ref in references:
        refDistance = np.linalg.norm(test - ref)
        sumValue += refDistance
    return 1.0 * sumValue / refCount

def getDurationFromAudioData(y, sr):
    ylen = len(y)
    return 1.0 * ylen / sr

def getDurationFromAudioFile(fn, accurate=False):
    duration = 0
    if os.path.isfile(fn):
        if accurate:
            try:
                y, sr = loadAudioData(getAudioFile(fn))
                duration = int(getDurationFromAudioData(y, sr) * 1000)
            except audioop.error:
                duration = 0
        else:
            command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', fn]
            try:
                duration = subprocess.check_output(command).strip()
            except subprocess.CalledProcessError:
                duration = 0
            duration = float(duration)
    return duration

def getFeatures(y, sr, start, dur=100, fft=2048, hop_length=512):
    if dur <= 0:
        return {
            "power": -1,
            "hz": -1,
            "clarity": -1,
            "note": "-",
            "octave": -1
        }
    # analyze just the sample
    y = getFrameRange(y, start, start+dur, sr)

    power = getPower(y, fft=fft, hop_length=hop_length)
    hz, clarity, harmonics = getPitch(y, sr, fft=fft)
    # rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    # flatness = librosa.feature.spectral_flatness(y=y)[0]

    # flatness = round(weightedMean(flatness, weights=stft), 5)
    # hz = round(weightedMean(rolloff, weights=stft), 2)
    hz = round(hz, 2)
    clarity = round(clarity, 2)
    note = pitchToNote(hz)

    # parse note
    octave = -1
    matches = re.match("([A-Z]\#?b?)(\-?[0-9]+)", note)
    if matches:
        note = matches.group(1)
        octave = int(matches.group(2))

    return {
        "power": power,
        "hz": hz,
        "clarity": clarity,
        # "flatness": flatness,
        "note": note,
        "octave": octave,
        "harmonics": len(harmonics)
    }

def getFeaturesFromSamples(filename, samples, y=None, sr=None):
    # load audio
    sampleCount = len(samples)
    if sampleCount < 1:
        return samples
    print("Getting features from %s samples in %s..." % (sampleCount, filename))

    # load audio
    if y is None or sr is None:
        fn = getAudioFile(filename)
        y, sr = loadAudioData(fn)

    features = []
    for i, sample in enumerate(samples):
        sfeatures = sample.copy()
        sfeatures.update(getFeatures(y, sr, sample["start"], sample["dur"]))
        features.append(sfeatures)

        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(i+1)/sampleCount*100,1))
        sys.stdout.flush()

    return features

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

def getFrameRange(y, ms0, ms1, sr):
    i0 = msToFrame(ms0, sr)
    i1 = msToFrame(ms1, sr)
    if i1 >= len(y):
        delta = i1 - len(y) + 1
        i1 -= delta
        i0 -= delta
    i0 = max(i0, 0)
    i1 = max(i1, 0)
    # print("%s%% to %s%%" % (round(1.0*i0/len(y)*100, 5), round(1.0*i1/len(y)*100, 5)))
    return y[i0:i1]

def getPitch(y, sr, fft=2048):
    y = librosa.effects.harmonic(y, margin=4) # increase margin for higher filtering of noise (probably between 1 and 8)
    y = np.nan_to_num(y)
    pitches, magnitudes = librosa.core.piptrack(y=y, sr=sr, n_fft=fft)

    # get sum of mags at each time
    magFrames = magnitudes.sum(axis=0) # get the sum of bins at each time frame
    t = magFrames.argmax()

    # get peaks at time t
    magBins = magnitudes[:, t]
    peaks = findPeaks(magBins, findMinima=False, height=np.median(magBins), distance=18)

    # for i, p in enumerate(peaks):
    #     if i > 0:
    #         prev = peaks[i-1]
    #         print(p - prev)

    bindIndex = 0
    # assign the first peak (the lowest pitch) in the harmonic
    if len(peaks) > 0:
        binIndex = peaks[0]
    else:
        binIndex = magnitudes[:, t].argmax()
    pitch = pitches[binIndex, t]

    contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
    clarity = np.mean(contrast[:, t])
    harmonics = pitches[peaks, t]

    return pitch, clarity, harmonics

def getPower(y, fft=2048, hop_length=512):
    stft = getStft(y, n_fft=fft, hop_length=hop_length)
    power = round(weightedMean(stft), 2)
    if math.isinf(power):
        power = -1
    return power

def getPowerFromSamples(samples, fft=2048, hop_length=512):
    samples = addIndices(samples, "_i")
    filenames = groupList(samples, "filename")
    filecount = len(filenames)
    for i, f in enumerate(filenames):
        fsamples = f["items"]
        fn = getAudioFile(f["filename"])
        print("  Reading %s..." % fn)
        y, sr = loadAudioData(fn)
        print("  Getting %s samples from %s" % (len(fsamples), fn))
        for s in fsamples:
            sy = getFrameRange(y, s["start"], s["start"]+s["dur"], sr)
            spower = getPower(sy, fft=fft, hop_length=hop_length)
            samples[s["_i"]]["power"] = spower
        printProgress(i+1, filecount, "  ")
    return samples

def getPowerFromTimecodes(timecodes, method="max"):
    # add indices
    for i, t in enumerate(timecodes):
        if "index" not in t:
            timecodes[i]["index"] = i
    # get unique filenames
    filenames = list(set([t["filename"] for t in timecodes]))
    powerData = {}
    # get features for each timecode in file
    for filename in filenames:
        y, sr = loadAudioData(getAudioFile(filename))
        duration = int(getDurationFromAudioData(y, sr) * 1000)
        stft = getStft(y)
        maxStft = 1
        if method=="mean":
            maxStft = np.mean(stft)
        else:
            maxStft = max(stft)
        stftLen = len(stft)
        fileTimecodes = [t for t in timecodes if t["filename"]==filename]
        # len(y) = hop_length * len(stft)
        for t in fileTimecodes:
            p = 1.0 * t["t"] / duration
            p = lim(p)
            j = roundInt(p * (stftLen-1))
            power = lim(1.0 * stft[j] / maxStft)
            powerData[t["index"]] = power
    return powerData

def getStft(y, n_fft=2048, hop_length=512):
    return librosa.feature.rmse(S=librosa.stft(y, n_fft=n_fft, hop_length=hop_length))[0]

def loadAudioData(fn, sr=None):
    return librosa.load(fn, sr=sr)

def makeBlankAudio(duration, fn, sampleWidth=4, sampleRate=48000, channels=2):
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=sampleRate)
    baseAudio = baseAudio.set_channels(channels)
    baseAudio = baseAudio.set_sample_width(sampleWidth)
    format = fn.split(".")[-1]
    baseAudio.export(fn, format=format)
    print("Created blank audio: %s" % fn)

def matchDb(audio, targetDb, maxMatchDb=None):
    deltaDb = targetDb - audio.dBFS
    if maxMatchDb is not None:
        deltaDb = min(deltaDb, maxMatchDb)
    return audio.apply_gain(deltaDb)

def maxDb(audio, db):
    deltaDb = db - audio.dBFS
    if deltaDb < 0:
        audio = audio.apply_gain(deltaDb)
    return audio

def msToFrame(ms, sr):
    return int(round(ms / 1000.0 * sr))

# Adapted from: https://github.com/paulnasca/paulstretch_python/blob/master/paulstretch_newmethod.py
def paulStretch(samplerate, smp, stretch, windowsize_seconds=0.25, onset_level=10.0):
    nchannels=smp.shape[0]

    def optimize_windowsize(n):
        orig_n=n
        while True:
            n=orig_n
            while (n%2)==0:
                n/=2
            while (n%3)==0:
                n/=3
            while (n%5)==0:
                n/=5

            if n<2:
                break
            orig_n+=1
        return orig_n

    #make sure that windowsize is even and larger than 16
    windowsize=int(windowsize_seconds*samplerate)
    if windowsize<16:
        windowsize=16
    windowsize=optimize_windowsize(windowsize)
    windowsize=int(windowsize/2)*2
    half_windowsize=int(windowsize/2)

    #correct the end of the smp
    nsamples=smp.shape[1]
    end_size=int(samplerate*0.05)
    if end_size<16:
        end_size=16

    smp[:,nsamples-end_size:nsamples]*=np.linspace(1,0,end_size)


    #compute the displacement inside the input file
    start_pos=0.0
    displace_pos=windowsize*0.5

    #create Hann window
    window=0.5-np.cos(np.arange(windowsize,dtype='float')*2.0*np.pi/(windowsize-1))*0.5

    old_windowed_buf=np.zeros((2,windowsize))
    hinv_sqrt2=(1+np.sqrt(0.5))*0.5
    hinv_buf=2.0*(hinv_sqrt2-(1.0-hinv_sqrt2)*np.cos(np.arange(half_windowsize,dtype='float')*2.0*np.pi/half_windowsize))/hinv_sqrt2

    freqs=np.zeros((2,half_windowsize+1))
    old_freqs=freqs

    num_bins_scaled_freq=32
    freqs_scaled=np.zeros(num_bins_scaled_freq)
    old_freqs_scaled=freqs_scaled

    displace_tick=0.0
    displace_tick_increase=1.0/stretch
    if displace_tick_increase>1.0:
        displace_tick_increase=1.0
    extra_onset_time_credit=0.0
    get_next_buf=True

    sdata = np.array([])
    while True:
        if get_next_buf:
            old_freqs=freqs
            old_freqs_scaled=freqs_scaled

            #get the windowed buffer
            istart_pos=int(np.floor(start_pos))
            buf=smp[:,istart_pos:istart_pos+windowsize]
            if buf.shape[1]<windowsize:
                buf=np.append(buf,np.zeros((2,windowsize-buf.shape[1])),1)
            buf=buf*window

            #get the amplitudes of the frequency components and discard the phases
            freqs=abs(np.fft.rfft(buf))

            #scale down the spectrum to detect onsets
            freqs_len=freqs.shape[1]
            if num_bins_scaled_freq<freqs_len:
                freqs_len_div=freqs_len//num_bins_scaled_freq
                new_freqs_len=freqs_len_div*num_bins_scaled_freq
                freqs_scaled=np.mean(np.mean(freqs,0)[:new_freqs_len].reshape([num_bins_scaled_freq,freqs_len_div]),1)
            else:
                freqs_scaled=np.zeros(num_bins_scaled_freq)


            #process onsets
            m=2.0*np.mean(freqs_scaled-old_freqs_scaled)/(np.mean(abs(old_freqs_scaled))+1e-3)
            if m<0.0:
                m=0.0
            if m>1.0:
                m=1.0
            # if plot_onsets:
            #     onsets.append(m)
            if m>onset_level:
                displace_tick=1.0
                extra_onset_time_credit+=1.0

        cfreqs=(freqs*displace_tick)+(old_freqs*(1.0-displace_tick))

        #randomize the phases by multiplication with a random complex number with modulus=1
        ph=np.random.uniform(0,2*np.pi,(nchannels,cfreqs.shape[1]))*1j
        cfreqs=cfreqs*np.exp(ph)

        #do the inverse FFT
        buf=np.fft.irfft(cfreqs)

        #window again the output buffer
        buf*=window

        #overlap-add the output
        output=buf[:,0:half_windowsize]+old_windowed_buf[:,half_windowsize:windowsize]
        old_windowed_buf=buf

        #remove the resulted amplitude modulation
        output*=hinv_buf

        #clamp the values to -1..1
        output[output>1.0]=1.0
        output[output<-1.0]=-1.0

        #write the output to wav file
        # outfile.writeframes(int16(output.ravel(1)*32767.0).tostring())
        sdata = np.append(sdata, output.ravel(1), axis=0)

        if get_next_buf:
            start_pos+=displace_pos

        get_next_buf=False

        if start_pos>=nsamples:
            # print ("100 %")
            break
        # sys.stdout.write("%d %% \r" % int(100.0*start_pos/nsamples))
        # sys.stdout.flush()

        if extra_onset_time_credit<=0.0:
            displace_tick+=displace_tick_increase
        else:
            credit_get=0.5*displace_tick_increase #this must be less than displace_tick_increase
            extra_onset_time_credit-=credit_get
            if extra_onset_time_credit<0:
                extra_onset_time_credit=0
            displace_tick+=displace_tick_increase-credit_get

        if displace_tick>=1.0:
            displace_tick=displace_tick % 1.0
            get_next_buf=True

    sdata = sdata * 32767.0
    sdata = sdata.astype(np.int16)
    return sdata

def pitchToNote(hz):
    note = "-"
    try:
        note = librosa.hz_to_note(hz)
    except OverflowError:
        pass
    return note

def scaleAudioData(arr):
    # get the average
    avg = np.average(arr)
    # scale from 20,20000 to 0,1
    return (avg - 20) / (20000 - 20)

def stretchSound(sound, amount=2.0, fade_out=0.8):
    channels = sound.channels
    frame_rate = sound.frame_rate
    samples = np.array(sound.get_array_of_samples())
    samples = samples.astype(np.int16)
    samples = samples * (1.0/32768.0)
    if channels > 1:
        samples = samples.reshape(channels, roundInt(1.0*len(samples)/channels), order='F')
    newData = paulStretch(frame_rate, samples, amount)
    newData = array.array(sound.array_type, newData)
    newSound = sound._spawn(newData)
    if fade_out > 0:
        fadeMs = int(round(len(newSound) * fade_out))
        newSound = newSound.fade_out(fadeMs)
    return newSound

def volumeToDb(volume):
    db = 0.0
    if 0.0 < volume < 1.0 or volume > 1.0:
        db = 10.0 * math.log(volume**2)
    return db
