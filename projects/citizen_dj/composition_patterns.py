# -*- coding: utf-8 -*-

# python3 projects/citizen_dj/composition_patterns.py -tracks
# python3 projects/citizen_dj/composition_patterns.py -config "projects/citizen_dj/config/patterns/edison-old-pal.json" -tracks
# python3 projects/citizen_dj/composition_patterns.py -config "projects/citizen_dj/config/patterns/edison-southern-airs.json" -tracks
# python3 projects/citizen_dj/composition_patterns.py -config "projects/citizen_dj/config/patterns/edison-onward.json" -tracks
# python3 projects/citizen_dj/composition_patterns.py -config "projects/citizen_dj/config/patterns/edison-bubbles.json" -tracks

import argparse
import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

from djlib import *

parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="projects/citizen_dj/config/patterns/edison-intro.json", help="Input json config file")
parser.add_argument('-tracks', dest="TRACKS", action="store_true", help="Also output tracks?")
parser.add_argument('-debug', dest="DEBUG", action="store_true", help="Just display the info?")
a = parser.parse_args()

config = readJSON(a.CONFIG_FILE)

makeDirectories([config["outFile"], config["stemFiles"]])

sequence = loadSampleSequence(config)
sequenceCount = len(sequence)

def addSequenceStep(startMs, step, progress, config):
    # section -> bars -> notes
    c = config
    instructions = []
    patterns = step["patterns"]
    speed = step["speed"]

    divisions = c["notesPerMeasure"]
    beatMs = 60.0 / c["bpm"] * 1000
    beatMs = beatMs / speed
    barMs = beatMs * c["beatsPerMeasure"]
    noteMs = 1.0 * barMs / divisions
    swingMs = noteMs * config["swing"]
    maxSDur = roundInt(noteMs * 2)

    for i, sample in enumerate(patterns):
        # if sample["type"] != "drum":
        #     continue
        for j, note in enumerate(sample["notes"]):
            if note == "" or note == 0:
                continue
            sSwingMs = 0 if j % 2 < 1 else swingMs
            volume = 1.0
            if j % 8 < 1:
                volume = 1.0
            elif j % 4 < 1:
                volume = 0.9
            else:
                volume = 0.8
            dur = sample["dur"]
            if note > 1 or note > 0 and dur <= 0:
                dur = roundInt(note * noteMs)
            # fadeIn = min(60, roundInt(dur*0.5))
            # fadeOut = min(100, roundInt(dur*0.5))
            step = {
                "ms": roundInt(startMs + j * noteMs + sSwingMs),
                "filename": sample["filename"],
                "start": sample["start"],
                # "dur": min(sample["dur"], maxSDur),
                # "fadeIn": fadeIn,
                # "fadeOut": fadeOut,
                "dur": dur,
                "volume": volume * sample["volume"]
            }
            if "tempo" in sample:
                step["tempo"] = sample["tempo"]
            instructions.append(step)

    return (instructions, barMs)

instructions = []
ms = 0
for i, step in enumerate(sequence):
    progress = 1.0 * i / (sequenceCount-1) if sequenceCount > 1 else 0
    stepInstructions, stepDur = addSequenceStep(ms, step, progress, config)
    instructions += stepInstructions
    ms += stepDur

for i, step in enumerate(instructions):
    instructions[i]["endMs"] = step["ms"] + step["dur"]
instructions = sorted(instructions, key=lambda step: step["endMs"])
totalDuration = instructions[-1]["endMs"]

if a.DEBUG:

    drums = []
    for step in sequence:
        if "drums" in step["groups"]:
            drums += [item["instrument"] for item in step["groups"]["drums"]["patterns"]]
    drums = unique(drums)
    print("Drums:")
    pprint(drums)

    sys.exit()

mixAudio(instructions, totalDuration, config["outFile"], masterDb=config["masterDb"], outputTracks=a.TRACKS, tracksDir=config["stemFiles"])

beep()
