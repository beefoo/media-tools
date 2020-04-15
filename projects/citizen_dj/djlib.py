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
        for j in range(config["notesPerMeasure"]):
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

def loadSampleSequence(config):
    _, samplePatterns = readCsv(config["samplesFile"])
    if "samplesQuery" in config:
        samplePatterns = filterByQueryString(samplePatterns, config["samplesQuery"])
    samplePatternCount = len(samplePatterns)
    print("%s sample patterns after filtering" % samplePatternCount)

    # parse notes
    for i, s in enumerate(samplePatterns):
        notes = [s["s"+str(j+1)] for j in range(config["notesPerMeasure"])]
        samplePatterns[i]["notes"] = notes
        samplePatterns[i]["filename"] = config["sampleMediaDir"] + s["filename"]
        nvol = 1.0 if "nvol" not in s or s["nvol"]=="" else s["nvol"]
        samplePatterns[i]["volume"] = config["samplesVolume"] * nvol

    # group samples by id
    samplePatternsById = groupList(samplePatterns, "id")
    samplePatternLookup = createLookup(samplePatternsById, "id")

    # read drum patterns
    drumPatterns = loadDrumPatterns(config)
    # normalize drum patterns
    drumPatternsN = []
    for i, dp in enumerate(drumPatterns):
        itemLookup = {}
        for j, note in enumerate(dp["notes"]):
            for instrument in note:
                fn = instrument["filename"]
                if fn in itemLookup:
                    itemLookup[fn]["notes"][j] = 1
                else:
                    notes = [0 for n in range(config["notesPerMeasure"])]
                    notes[j] = 1
                    item = instrument.copy()
                    item["id"] = dp["id"]
                    item["type"] = "drum"
                    item["notes"] = notes
                    item["volume"] = config["drumsVolume"]
                    itemLookup[fn] = item
        drumPatternsN += [itemLookup[key] for key in itemLookup]

    drumPatternsById = groupList(drumPatternsN, "id")
    drumPatternLookup = createLookup(drumPatternsById, "id")

    sequence = loadSequenceFile(config)
    flattenedSequence = []
    for i, step in enumerate(sequence):
        patterns = []
        if step["id"] != "" and step["id"] in samplePatternLookup:
            patterns += samplePatternLookup[step["id"]]["items"]
        if step["drumId"] != "" and step["drumId"] in drumPatternLookup:
            patterns += drumPatternLookup[step["drumId"]]["items"]
        step["patterns"] = patterns
        for j in range(step["count"]):
            flattenedSequence.append(step.copy())

    return flattenedSequence

def loadSequenceFile(config):
    _, sequence = readCsv(config["sequenceFile"])
    if "sequenceQuery" in config:
        sequence = filterByQueryString(sequence, config["sequenceQuery"])
    seqCount = len(sequence)
    print("%s sequence steps after filtering" % seqCount)

    for i, step in enumerate(sequence):
        sequence[i]["options"] = parseQueryString(step["options"], doParseNumbers=True) if step["options"] != "" else False
        sequence[i]["drumOptions"] = parseQueryString(step["drumOptions"], doParseNumbers=True) if step["drumOptions"] != "" else False

    return sequence
