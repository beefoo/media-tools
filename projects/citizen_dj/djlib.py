import inspect
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

def drumPatternsToInstructions(drumPatterns, startMs, endMs, config, baseVolume):
    instructions = []
    beatMs = roundInt(60.0 / config["drumsBpm"] * 1000)
    measureMs = beatMs * config["beatsPerMeasure"]
    swingMs = roundInt(beatMs / 4.0 * config["swing"])
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

def loadDrumPatterns(config):
    c = config

    # read drums
    _, drums = readCsv(c["drumsFile"])
    if "drumsQuery" in config:
        drums = filterByQueryString(drums, config["drumsQuery"])
    drumCount = len(drums)
    print("%s drums after filtering" % drumCount)

    # read drum patterns
    _, drumPatterns = readCsv(c["drumPatternsFile"])
    if "drumPatternsQuery" in config:
        drumPatterns = filterByQueryString(drumPatterns, config["drumPatternsQuery"])
    drumPatternCount = len(drumPatterns)
    print("%s drum patterns after filtering" % drumPatternCount)

    for i, drum in enumerate(drums):
        drums[i]["filename"] = c["drumsAudioDir"] + drum["filename"]
        if drum["priority"] == "":
            drums[i]["priority"] = 9999

    drumsByInstrument = groupList(drums, "instrument")
    for i, group in enumerate(drumsByInstrument):
        instruments = sorted(group["items"], key=lambda item: item["priority"])
        drumsByInstrument[i]["prioritizedDrum"] = instruments[0]

    drumLookup = createLookup(drumsByInstrument, "instrument")
    for i, pattern in enumerate(drumPatterns):
        notes = []
        for j in range(16):
            key = str(j+1)
            value = pattern[key]
            instruments = []
            if len(value) > 0:
                for symbol in value.split(","):
                    if symbol in drumLookup:
                        instruments.append(drumLookup[symbol]["prioritizedDrum"])
                    else:
                        print("Could not find '%s' in drums" % symbol)
            notes.append(instruments)
        drumPatterns[i]["notes"] = notes

    return drumPatterns

def loadSamplePatterns(config):
    _, samples = readCsv(config["samplesFile"])
    if "samplesQuery" in config:
        samples = filterByQueryString(samples, config["samplesQuery"])
    sampleCount = len(samples)
    print("%s samples after filtering" % sampleCount)

    divisions = 16
    beatMs = 60.0 / config["bpm"] * 1000
    barMs = beatMs * config["beatsPerMeasure"]
    noteMs = 1.0 * barMs / divisions

    for i, s in enumerate(samples):
        notes = [s["s"+str(j+1)] for j in range(16)]
        samples[i]["notes"] = notes
        isEmpty = True
        for n in notes:
            if n != "":
                isEmpty = False
                break
        samples[i]["isEmpty"] = isEmpty

    defaultBarPatterns = [
      [1,0,0,0, 0,0,0,0, 0,0,1,0, 0,0,0,0],
      [0,0,0,0, 1,0,0,0, 0,0,0,0, 0,0,1,0],
      [0,0,1,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
      [0,0,0,0, 0,0,1,0, 0,0,0,0, 1,0,0,0]
    ]

    # group samples by section and bar
    samplesBySection = groupList(samples, "section")
    samplesBySection = sorted(samplesBySection, key=lambda k: k["section"])
    for i, section in enumerate(samplesBySection):
        sectionsByBar = groupList(section["items"], "bar")

        # fill in bars if empty
        for j, bar in enumerate(sectionsByBar):

            barPattern = [p[:] for p in defaultBarPatterns]
            # // manually uncheck pattern columns if previous beat is too long
            for k, row in enumerate(bar["items"]):
                nearestNoteDur = 1.0 * row["dur"] / noteMs
                if nearestNoteDur >= 3.5:
                    if k==0:
                        barPattern[2][2] = 0
                    elif k==1:
                        barPattern[3][6] = 0
                    elif k==2:
                        barPattern[0][10] = 0
                    elif k==3:
                        barPattern[1][14] = 0
            # assign auto-patterns if empty
            for k, row in enumerate(bar["items"]):
                if not row["isEmpty"]:
                    continue
                if k >= len(barPattern):
                    continue
                notes = barPattern[k]
                sectionsByBar[j]["items"][k]["notes"] = notes

        samplesBySection[i]["bars"] = sectionsByBar

    for i, s in enumerate(samplesBySection):
        samplesBySection[i]["sectionKey"] = str(s["section"])
    sectionLookup = createLookup(samplesBySection, "sectionKey")

    sectionSequence = []
    for s in config["sectionSequence"]:
        section, count = tuple(s)
        sectionSequence.append({
            "section": sectionLookup[str(section)],
            "count": count
        })

    return sectionSequence
