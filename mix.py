# -*- coding: utf-8 -*-

# python -W ignore mix.py -in "../latitude/output/mix.csv" -inaudio "../latitude/output/mix_audio.csv" -dir "audio/downloads/vivaldi/" -sd 60

import argparse
import math
from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool
import os
from pprint import pprint
from pydub import AudioSegment
import sys
from lib import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="data/mix.csv", help="Input sequence csv file")
parser.add_argument('-inaudio', dest="INPUT_AUDIO_FILE", default="data/mix_audio.csv", help="Input audio csv file")
parser.add_argument('-dir', dest="AUDIO_DIR", default="audio/sample/", help="Input audio directory")
parser.add_argument('-left', dest="PAD_LEFT", default=1000, type=int, help="Pad left in milliseconds")
parser.add_argument('-right', dest="PAD_RIGHT", default=3000, type=int, help="Pad right in milliseconds")
parser.add_argument('-ss', dest="EXCERPT_START", default=0, type=float, help="Slice start in seconds")
parser.add_argument('-sd', dest="EXCERPT_DUR", default=-1, type=float, help="Slice duration in seconds")
parser.add_argument('-fx', dest="SOUND_FX", default=1, type=int, help="Apply sound effects? (takes longer)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sample_mix.mp3", help="Output audio file")
parser.add_argument('-overwrite', dest="OVERWRITE", default=1, type=int, help="Overwrite existing audio?")
args = parser.parse_args()

INPUT_FILE = args.INPUT_FILE
INPUT_AUDIO_FILE = args.INPUT_AUDIO_FILE
AUDIO_DIR = args.AUDIO_DIR
PAD_LEFT = args.PAD_LEFT
PAD_RIGHT = args.PAD_RIGHT
EXCERPT_START = int(round(args.EXCERPT_START * 1000))
EXCERPT_DUR = int(round(args.EXCERPT_DUR * 1000))
SOUND_FX = (args.SOUND_FX > 0)
OUTPUT_FILE = args.OUTPUT_FILE
OVERWRITE = (args.OVERWRITE > 0)

MIN_VOLUME = 0.01
MAX_VOLUME = 10.0
CLIP_FADE_IN_DUR = 100
CLIP_FADE_OUT_DUR = 100
FX_PAD = 3000
SAMPLE_WIDTH = 2
FRAME_RATE = 44100
CHANNELS = 2

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

# Read input file
fieldnames, audioFiles = readCsv(INPUT_AUDIO_FILE)
fieldnames, instructions = readCsv(INPUT_FILE)
print("%s audio files found" % len(audioFiles))
print("%s instructions found" % len(instructions))

# Make excerpt
instructions = [i for i in instructions if i["ms"] >= EXCERPT_START]
if EXCERPT_DUR > 0:
    EXCERPT_END = EXCERPT_START + EXCERPT_DUR
    instructions = [i for i in instructions if i["ms"] <= EXCERPT_END]

instructions = sorted(instructions, key=lambda k: k['ms'])
INSTRUCTION_COUNT = len(instructions)

# Add features
for i, step in enumerate(instructions):
    instructions[i]["filename"] = AUDIO_DIR + audioFiles[step["ifilename"]]["filename"]
    instructions[i]["volume"] = 1.0 if "volume" not in step else lim(step["volume"], (MIN_VOLUME, MAX_VOLUME))
    instructions[i]["db"] = volumeToDb(instructions[i]["volume"])
    instructions[i]["ms"] = step["ms"] - EXCERPT_START + PAD_LEFT
audioFiles = list(set([i["filename"] for i in instructions]))

audioFiles = [{"filename": f} for f in audioFiles]
# Load sounds
print("Loading audio...")
for i, af in enumerate(audioFiles):
    filename = af["filename"]
    audioFiles[i]["index"] = i
    # load audio file
    fformat = filename.split(".")[-1].lower()
    audio = AudioSegment.from_file(filename, format=fformat)
    # convert to stereo
    if audio.channels != CHANNELS:
        print("Warning: channels changed to %s from %s in %s" % (CHANNELS, audio.channels, filename))
        audio = audio.set_channels(CHANNELS)
    # convert sample width
    if audio.sample_width != SAMPLE_WIDTH:
        print("Warning: sample width changed to %s from %s in %s" % (SAMPLE_WIDTH, audio.sample_width, filename))
        audio = audio.set_sample_width(SAMPLE_WIDTH)
    # convert sample rate
    if audio.frame_rate != FRAME_RATE:
        print("Warning: frame rate changed to %s from %s in %s" % (FRAME_RATE, audio.frame_rate, filename))
        audio = audio.set_frame_rate(FRAME_RATE)

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
        fadeInDur = CLIP_FADE_IN_DUR if clipDur <= 0 else min(CLIP_FADE_IN_DUR, clipDur)
        fadeOutDur = CLIP_FADE_OUT_DUR if clipDur <= 0 else min(CLIP_FADE_OUT_DUR, clipDur)
        clip = clip.fade_in(fadeInDur).fade_out(fadeOutDur)

        segments.append({
            "id": (clipStart, clipDur),
            "start": clipStart,
            "dur": clipDur,
            "audio": clip
        })
    audioFiles[i]["segments"] = segments

print("Loaded %s audio files" % len(audioFiles))

if INSTRUCTION_COUNT <= 0 or len(audioFiles) <= 0:
    print("No instructions or audio files")
    sys.exit()

# determine duration
last = instructions[-1]
duration = last["ms"] + last["dur"] + PAD_RIGHT
print("Creating audio file with duration %ss" % formatSeconds(duration/1000))

progress = 0
def makeTrack(p):
    global progress

    duration = p["duration"]
    instructions = p["instructions"]
    audiofile = p["audiofile"]
    segments = audiofile["segments"]

    # build audio
    baseAudio = AudioSegment.silent(duration=duration, frame_rate=FRAME_RATE)
    baseAudio = baseAudio.set_channels(CHANNELS)
    baseAudio = baseAudio.set_sample_width(SAMPLE_WIDTH)
    for index, i in enumerate(instructions):
        segment = [s for s in segments if s["id"]==(i["start"], i["dur"])].pop()
        audio = segment["audio"]
        if i["db"] != 0.0:
            audio = audio.apply_gain(i["db"])
        if "pan" in i and i["pan"] != 0.0:
            audio = audio.pan(i["pan"])
        if "fadeIn" in i and i["fadeIn"] > 0:
            audio = audio.fade_in(i["fadeIn"])
        if "fadeOut" in i and i["fadeOut"] > 0:
            audio = audio.fade_out(i["fadeOut"])
        if SOUND_FX:
            if "stretch" in i and i["stretch"] > 1.0:
                audio = stretchSound(audio, i["stretch"])
            effects = []
            for effect in ["reverb", "distortion", "highpass", "lowpass"]:
                if effect in i and i[effect] > 0:
                    effects.append((effect, i[effect]))
            if len(effects) > 0:
                audio = addFx(audio, effects, pad=FX_PAD)
        baseAudio = baseAudio.overlay(audio, position=i["ms"])
        progress += 1
        sys.stdout.write('\r')
        sys.stdout.write("%s%%" % round(1.0*progress/INSTRUCTION_COUNT*100,1))
        sys.stdout.flush()

    return baseAudio

# Build track parameters
trackParams = [{
    "duration": duration,
    "instructions": [i for i in instructions if i["filename"]==af["filename"]],
    "audiofile": af
} for af in audioFiles]

print("Building %s tracks..." % len(trackParams))
# pool = ThreadPool()
# tracks = pool.map(makeTrack, trackParams)
# pool.close()
# pool.join()
tracks = []
for p in trackParams:
    tracks.append(makeTrack(p))

print("Combining tracks...")
baseAudio = AudioSegment.silent(duration=duration, frame_rate=FRAME_RATE)
baseAudio = baseAudio.set_channels(CHANNELS)
baseAudio = baseAudio.set_sample_width(SAMPLE_WIDTH)
for track in tracks:
    baseAudio = baseAudio.overlay(track)

print("Writing to file...")
format = OUTPUT_FILE.split(".")[-1]
f = baseAudio.export(OUTPUT_FILE, format=format)
print("Wrote to %s" % OUTPUT_FILE)
