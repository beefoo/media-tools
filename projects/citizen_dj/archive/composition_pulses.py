# -*- coding: utf-8 -*-

# python3 projects/citizen_dj/composition_pulses.py

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
parser.add_argument('-config', dest="CONFIG_FILE", default="projects/citizen_dj/config/pulses/edison.json", help="Input json config file")
a = parser.parse_args()

config = readJSON(a.CONFIG_FILE)

_, samples = readCsv(config["samplesFile"])
if "samplesQuery" in config:
    samples = filterByQueryString(samples, config["samplesQuery"])
sampleCount = len(samples)
print("%s samples after filtering" % sampleCount)

samples = addIndices(samples)
if len(samples) > 100:
    samples = samples[:100]

makeDirectories([config["outFile"]])

def drumPatternsToInstructions(drumPatterns, startMs, endMs, config, baseVolume):
    instructions = []
    beatMs = 60.0 / config["drumsBpm"] * 1000
    measureMs = beatMs * config["beatsPerMeasure"]
    swingMs = beatMs / 4.0 * config["swing"]
    # measures = flattenList([pattern["bars"] for pattern in drumPatterns])
    totalMs = startMs
    while totalMs < endMs:
        for i, pattern in enumerate(drumPatterns):
            notes = pattern["notes"]
            divisions = len(notes)
            divisionMs = 1.0 * measureMs / divisions
            for j, note in enumerate(notes):
                sSwingMs = 0 if j % 2 < 1 else swingMs
                ms = roundInt(startMs + i * measureMs + j * divisionMs + sSwingMs)
                volume = 1.0
                if j % 8 < 1:
                    volume = 1.0
                elif j % 4 < 1:
                    volume = 0.8
                else:
                    volume = 0.6
                for k, instrument in enumerate(note):
                    instructions.append({
                        "ms": ms,
                        "filename": instrument["filename"],
                        "start": 0,
                        "dur": -1,
                        "volume": baseVolume * volume
                    })
            totalMs += measureMs
            if totalMs >= endMs:
                 break
        startMs = totalMs
    instructions = [i for i in instructions if i["ms"] < endMs]
    return instructions

def getSampleInstructions(sample, startMs):
    global config
    s = sample

    sPattern = []
    for i in range(16):
        r = pseudoRandom(s["index"]*1000+i)
        value = 0
        if i % 8 < 1:
            value = 1
        elif i % 4 < 1 and r > 0.25:
            value = 1
        elif i % 2 < 1 and r > 0.5:
            value = 1
        sPattern.append(value)

    instructions = []
    beatMs = roundInt(60.0 / config["bpm"] * 1000)
    measureMs = beatMs * config["beatsPerMeasure"]
    swingMs = roundInt(beatMs / 4.0 * config["swing"])
    divisions = len(sPattern)
    divisionMs = 1.0 * measureMs / divisions
    maxSDur = roundInt(divisionMs * 2)
    repeatPhrases = config["repeatPhrases"]
    volumeUnit = 1.0 / repeatPhrases

    for i in range(repeatPhrases):
        phraseStartMs = i * measureMs
        for j, p in enumerate(sPattern):
            if p < 1:
                continue
            sSwingMs = 0 if j % 2 < 1 else swingMs
            volume = 1.0
            if j % 8 < 1:
                volume = 1.0
            elif j % 4 < 1:
                volume = 0.75
            else:
                volume = 0.5
            sProgress = (1.0 * i * divisions + j) / (divisions * repeatPhrases - 1)
            sProgress = easeSinInOutBell(sProgress)
            baseVolume = lerp((0.2, 1.0), sProgress)
            instructions.append({
                "ms": roundInt(startMs + phraseStartMs + j * divisionMs + sSwingMs),
                "filename": config["sampleMediaDir"] + s["filename"],
                "start": s["start"],
                "dur": min(s["dur"], maxSDur),
                "volume": baseVolume * volume
            })

    return (instructions, measureMs * repeatPhrases)


instructions = []
beatMs = roundInt(60.0 / config["bpm"] * 1000)

ms = 0
for i, s in enumerate(samples):
    sInstructions, duration = getSampleInstructions(s, ms)
    instructions += sInstructions
    ms += roundInt(duration / 2)

totalDuration = instructions[-1]["ms"] + instructions[-1]["dur"]

drumPatterns = loadDrumPatterns(config)
instructions += drumPatternsToInstructions(drumPatterns, 0, totalDuration, config, baseVolume=0.25)

mixAudio(instructions, totalDuration, config["outFile"], masterDb=config["masterDb"])
