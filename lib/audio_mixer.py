from audio_utils import *
from math_utils import *
import os
from pydub import AudioSegment
import sys

def getAudioSequenceDuration(sequence):
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
        if "matchDb" in i:
            audio = matchDb(audio, i["matchDb"])
        if "reverse" in i and i["reverse"]:
            audio = audio.reverse()
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
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*(index+1)/instructionCount*100,1))
        sys.stdout.flush()
    return baseAudio

def mixAudio(instructions, duration, outfilename, sfx=True, sampleWidth=2, sampleRate=44100, channels=2, clipFadeIn=10, clipFadeOut=10, fxPad=3000):
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
        audiofilename = getAudioFile(filename)
        audioFiles[i]["index"] = i
        # load audio file
        fformat = audiofilename.split(".")[-1].lower()
        audio = AudioSegment.from_file(audiofilename, format=fformat)
        audioDurationMs = len(audio)
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
            else:
                clipEnd = audioDurationMs

            # check bounds
            clipStart = lim(clipStart, (0, audioDurationMs))
            clipEnd = lim(clipEnd, (0, audioDurationMs))
            if clipStart >= clipEnd:
                continue
            newClipDur = clipEnd - clipStart

            clip = audio[clipStart:clipEnd]

            # add a fade in/out to avoid clicking
            fadeInDur = min(clipFadeIn, newClipDur)
            fadeOutDur = min(clipFadeOut, newClipDur)
            clip = clip.fade_in(fadeInDur).fade_out(fadeOutDur)

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
    f = baseAudio.export(outfilename, format=format)
    print("Wrote to %s" % outfilename)
