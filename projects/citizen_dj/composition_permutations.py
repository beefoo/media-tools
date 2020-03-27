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

parser = argparse.ArgumentParser()
parser.add_argument('-config', dest="CONFIG_FILE", default="projects/citizen_dj/config/study-of-mimicry.json", help="Input json config file")
a = parser.parse_args()

config = readJSON(a.CONFIG_FILE)

_, samples = readCsv(config["samplesFile"])
if "samplesQuery" in config:
    samples = filterByQueryString(samples, config["samplesQuery"])
sampleCount = len(samples)
print("%s samples after filtering" % sampleCount)

makeDirectories([config["outFile"], config["stemFiles"]])

samplesPerPhrase = config["samplesPerPhrase"]
phrase = samples[:samplesPerPhrase]

instructions = []
roundToNth = [-1, 4]
times = config["repeatPhrases"]
ms = 0
padMs = 0

if len(config["phrasePattern"]) < samplesPerPhrase:
    print("Not enough rows in the pattern; need %s" % samplesPerPhrase)
    sys.exit()

if len(samples) < samplesPerPhrase:
    print("Not enough samples; need %s" % samplesPerPhrase)
    sys.exit()

def phraseToInstructions(phrase, pattern, startMs, beatMs, baseVolume, config):
    instructions = []
    measureMs = beatMs * config["beatsPerMeasure"]
    swingMs = roundInt(beatMs / 4.0 * config["swing"])

    for i, s in enumerate(phrase):
        sPattern = pattern[i]
        divisions = len(sPattern)
        divisionMs = 1.0 * measureMs / divisions
        maxSDur = roundInt(divisionMs * 2)
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
            instructions.append({
                "ms": roundInt(startMs + j * divisionMs + sSwingMs),
                "filename": config["sampleMediaDir"] + s["filename"],
                "start": s["start"],
                "dur": min(s["dur"], maxSDur),
                "volume": volume * baseVolume
            })
    return instructions

instructions = []
phrase = samples[:samplesPerPhrase]
ms = 0
totalPhraseCount = sampleCount-samplesPerPhrase+1
for i in range(totalPhraseCount):
    progress = 1.0 * i / (totalPhraseCount-1)
    beatMs = roundInt(60.0 / config["bpm"] * 1000)
    for j in range(times):
        baseVolume = lerp((1.0, 0.33), j/(times-1)) if times > 1 else 1.0
        if 0.25 <= progress < 0.75 and i % 2 > 0:
            baseVolume = lerp((0.33, 1.0), j/(times-1)) if times > 1 else 1.0
        instructions += phraseToInstructions(phrase, config["phrasePattern"], ms, beatMs, baseVolume, config)
        ms += (beatMs * config["beatsPerMeasure"])
    phrase = samples[i+1:i+1+samplesPerPhrase]

totalDuration = instructions[-1]["ms"] + instructions[-1]["dur"]
mixAudio(instructions, totalDuration, config["outFile"], masterDb=config["masterDb"])
