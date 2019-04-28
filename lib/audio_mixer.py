from lib.audio_utils import *
from lib.math_utils import *
import os
from pydub import AudioSegment
import sys

def getAudioSequenceDuration(sequence):
    if len(sequence) <= 0:
        return 0
    sequence = sorted(sequence, key=lambda s: s["ms"]+s["dur"])
    lastAudioClip = sequence[-1]
    return lastAudioClip["ms"] + lastAudioClip["dur"]

def makeTrack(duration, instructions, segments, sfx=True, sampleWidth=2, sampleRate=44100, channels=2, fxPad=3000):
    # build audio
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=sampleRate)
    baseAudio = baseAudio.set_channels(channels)
    baseAudio = baseAudio.set_sample_width(sampleWidth)
    instructionCount = len(instructions)
    for index, i in enumerate(instructions):
        segment = [s for s in segments if s["id"]==(i["start"], i["dur"])].pop()
        audio = segment["audio"]
        audio = applyAudioProperties(audio, i, sfx, fxPad)
        baseAudio = baseAudio.overlay(audio, position=i["ms"])
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(index+1)/instructionCount*100,1))
        sys.stdout.flush()
    return baseAudio

def mixAudio(instructions, duration, outfilename, sfx=True, sampleWidth=2, sampleRate=44100, channels=2, fxPad=3000, masterDb=0.0):
    # remove instructions with no volume
    instructions = [i for i in instructions if "volume" not in i or i["volume"] > 0]
    audioFiles = list(set([i["filename"] for i in instructions]))
    audioFiles = [{"filename": f} for f in audioFiles]
    instructionCount = len(instructions)
    trackCount = len(audioFiles)

    # calculate db
    for i, step in enumerate(instructions):
        if "volume" in step:
            instructions[i]["db"] = volumeToDb(step["volume"])

    # create base audio
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=sampleRate)
    baseAudio = baseAudio.set_channels(channels)
    baseAudio = baseAudio.set_sample_width(sampleWidth)

    # Load sounds
    print("Adding tracks...")
    for i, af in enumerate(audioFiles):
        filename = af["filename"]
        audioFiles[i]["index"] = i

        # load audio file
        audio = getAudio(filename, sampleWidth, sampleRate, channels)
        audioDurationMs = len(audio)

        # look through instructions to find unique clips
        clips = [(ii["start"], ii["dur"]) for ii in instructions if ii["filename"]==filename]
        clips = list(set(clips))

        # make segments from clips
        segments = []
        for clipStart, clipDur in clips:
            clip = getAudioClip(audio, clipStart, clipDur, audioDurationMs)
            if clip is None:
                continue
            segments.append({
                "id": (clipStart, clipDur),
                "start": clipStart,
                "dur": clipDur,
                "audio": clip
            })

        # make the track
        trackInstructions = [ii for ii in instructions if ii["filename"]==af["filename"]]
        print("Making track %s of %s with %s segments and %s instructions..." % (i+1, trackCount, len(segments), len(trackInstructions)))
        trackAudio = makeTrack(duration, trackInstructions, segments, sfx=sfx, sampleWidth=sampleWidth, sampleRate=sampleRate, channels=channels, fxPad=fxPad)
        baseAudio = baseAudio.overlay(trackAudio)
        print("Track %s of %s complete." % (i+1, trackCount))

    print("Writing to file...")
    format = outfilename.split(".")[-1]
    # adjust master volume
    if masterDb != 0.0:
        baseAudio = baseAudio.apply_gain(masterDb)
    f = baseAudio.export(outfilename, format=format)
    print("Wrote to %s" % outfilename)

def plotAudioSequence(seq):
    import matplotlib.pyplot as plt
    filenames = unique([(s["filename"], s["start"]) for s in seq])
    xs = [s["ms"]/1000.0 for s in seq]
    ys = [filenames.index((s["filename"], s["start"]))+1 for s in seq]
    plt.scatter(xs, ys, s=4)
    plt.show()
