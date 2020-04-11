# -*- coding: utf-8 -*-

# python3 projects/citizen_dj/composition_permutations.py -config "projects/citizen_dj/config/cal-91.json"

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

from djlib import *

parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="projects/citizen_dj/config/patterns/edison-intro.json", help="Input json config file")
a = parser.parse_args()

config = readJSON(a.CONFIG_FILE)

makeDirectories([config["outFile"], config["stemFiles"]])

sectionSequence = loadSamplePatterns(config)
totalMeasures = sum([s["count"] for s in sectionSequence])
drumPatterns = loadDrumPatterns(config)

def addSampleMeasure(startMs, section, sectionProgress, progress, config):
    # section -> bars -> notes
    c = config
    instructions = []
    bars = section["bars"]
    bar = bars[0]
    secondaryBars = [] if len(bars) <= 1 else bars[1:]

    # Logic for choosing another bar
    if sectionProgress > 0:
        seed = startMs + config["sampleSeed"]
        chance = pseudoRandom(seed)
        if chance > 0.5:
            barIndex = pseudoRandom(seed, range=(0, len(secondaryBars)-1), isInt=True)
            bar = secondaryBars[barIndex]

    divisions = 16
    beatMs = 60.0 / c["bpm"] * 1000
    barMs = beatMs * c["beatsPerMeasure"]
    noteMs = 1.0 * barMs / divisions
    swingMs = noteMs * config["swing"]
    maxSDur = roundInt(noteMs * 2)
    for i, sample in enumerate(bar["items"]):
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
            sVolume = 1.0 if "nvol" not in sample or sample["nvol"]=="" else sample["nvol"]
            instructions.append({
                "ms": roundInt(startMs + j * noteMs + sSwingMs),
                "filename": config["sampleMediaDir"] + sample["filename"],
                "start": sample["start"],
                "dur": min(sample["dur"], maxSDur),
                "volume": volume * sVolume * config["samplesVolume"]
            })

    return (instructions, barMs)

instructions = []
ms = 0
measure = 0
for i, s in enumerate(sectionSequence):

    for j in range(s["count"]):
        sectionProgress = 1.0 * j / (s["count"]-1) if s["count"] > 1 else 0
        progress = 1.0 * measure / (totalMeasures-1)

        sampleInstructions, measureDur = addSampleMeasure(ms, s["section"], sectionProgress, progress, config)
        instructions += sampleInstructions
        # instructions += addDrumMeasure(ms, drumPatterns, sectionProgress, progress, config)

        measure += 1
        ms += measureDur

for i, step in enumerate(instructions):
    instructions[i]["endMs"] = step["ms"] + step["dur"]
instructions = sorted(instructions, key=lambda step: step["endMs"])
totalDuration = instructions[-1]["endMs"]

mixAudio(instructions, totalDuration, config["outFile"], masterDb=config["masterDb"])
