from audio_utils import *
from math_utils import *
import os
from pydub import AudioSegment
import sys

def makeTrack(p, sfx=True, sampleWidth=2, sampleRate=44100, channels=2, fxPad=3000):
    duration = p["duration"]
    instructions = p["instructions"]
    audiofile = p["audiofile"]
    segments = audiofile["segments"]

    # build audio
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=sampleRate)
    baseAudio = baseAudio.set_channels(channels)
    baseAudio = baseAudio.set_sample_width(sampleWidth)
    for index, i in enumerate(instructions):
        segment = [s for s in segments if s["id"]==(i["start"], i["dur"])].pop()
        audio = segment["audio"]
        if "db" in i and i["db"] != 0.0:
            audio = audio.apply_gain(i["db"])
        if "pan" in i and i["pan"] != 0.0:
            audio = audio.pan(i["pan"])
        if "fadeIn" in i and i["fadeIn"] > 0:
            audio = audio.fade_in(i["fadeIn"])
        if "fadeOut" in i and i["fadeOut"] > 0:
            audio = audio.fade_out(i["fadeOut"])
        if sfx:
            if "stretch" in i and i["stretch"] > 1.0:
                audio = stretchSound(audio, i["stretch"])
            effects = []
            for effect in ["reverb", "distortion", "highpass", "lowpass"]:
                if effect in i and i[effect] > 0:
                    effects.append((effect, i[effect]))
            if len(effects) > 0:
                audio = addFx(audio, effects, pad=fxPad)
        baseAudio = baseAudio.overlay(audio, position=i["ms"])
    return baseAudio

def mixAudio(instructions, duration, outfilename, sfx=True, sampleWidth=2, sampleRate=44100, channels=2, clipFadeIn=100, clipFadeOut=100, fxPad=3000):
    audioFiles = list(set([i["filename"] for i in instructions]))
    audioFiles = [{"filename": f} for f in audioFiles]
    instructionCount = len(instructions)

    # calculate db
    for i, step in enumerate(instructions):
        if "volume" in step:
            instructions[i]["db"] = volumeToDb(step["volume"])

    # Load sounds
    print("Loading audio...")
    for i, af in enumerate(audioFiles):
        filename = af["filename"]
        audioFiles[i]["index"] = i
        # load audio file
        fformat = filename.split(".")[-1].lower()
        audio = AudioSegment.from_file(filename, format=fformat)
        # convert to stereo
        if audio.channels != channels:
            print("Warning: channels changed to %s from %s in %s" % (channels, audio.channels, filename))
            audio = audio.set_channels(channels)
        # convert sample width
        if audio.sample_width != sampleWidth:
            print("Warning: sample width changed to %s from %s in %s" % (sampleWidth, audio.sample_width, filename))
            audio = audio.set_sample_width(sampleWidth)
        # convert sample rate
        if audio.frame_rate != sampleRate:
            print("Warning: frame rate changed to %s from %s in %s" % (sampleRate, audio.frame_rate, filename))
            audio = audio.set_frame_rate(sampleRate)

        # look through instructions to find unique clips
        clips = [(ii["start"], ii["dur"]) for ii in instructions if ii["filename"]==filename]
        clips = list(set(clips))

        # make segments from clips
        segments = []
        for clipStart, clipDur in clips:
            clipEnd = None
            if clipDur > 0:
                clipEnd = clipStart + clipDur
            clip = audio[clipStart:clipEnd]
            if clipEnd is None:
                clip = audio[clipStart:]

            # add a fade in/out to avoid clicking
            fadeInDur = clipFadeIn if clipDur <= 0 else min(clipFadeIn, clipDur)
            fadeOutDur = clipFadeOut if clipDur <= 0 else min(clipFadeOut, clipDur)
            clip = clip.fade_in(fadeInDur).fade_out(fadeOutDur)

            segments.append({
                "id": (clipStart, clipDur),
                "start": clipStart,
                "dur": clipDur,
                "audio": clip
            })
        audioFiles[i]["segments"] = segments

    print("Loaded %s audio files" % len(audioFiles))

    if instructionCount <= 0 or len(audioFiles) <= 0:
        print("No instructions or audio files")
        sys.exit()

    # Build track parameters
    trackParams = [{
        "duration": duration,
        "instructions": [i for i in instructions if i["filename"]==af["filename"]],
        "audiofile": af
    } for af in audioFiles]

    trackCount = len(trackParams)
    print("Building %s tracks..." % trackCount)

    tracks = []
    for i, p in enumerate(trackParams):
        tracks.append(makeTrack(p, sfx=sfx, sampleWidth=sampleWidth, sampleRate=sampleRate, channels=channels, fxPad=fxPad))
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(i+1)/trackCount*100,1))
        sys.stdout.flush()

    print("Combining tracks...")
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=sampleRate)
    baseAudio = baseAudio.set_channels(channels)
    baseAudio = baseAudio.set_sample_width(sampleWidth)
    for track in tracks:
        baseAudio = baseAudio.overlay(track)

    print("Writing to file...")
    format = outfilename.split(".")[-1]
    f = baseAudio.export(outfilename, format=format)
    print("Wrote to %s" % outfilename)
