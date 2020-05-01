import copy
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

def applyStepOptions(step, index, sequence, config):
    newStep = copy.deepcopy(step)

    for key, group in step["groups"].items():
        opt = group["options"]

        if opt is False:
            continue

        # filter by category
        if "only" in opt:
            only = opt["only"]
            if "," in only:
                only = only.split(",")
            newStep["groups"][key]["patterns"] = [item for item in newStep["groups"][key]["patterns"] if item["category"] in only]

        # drop specific notes
        if "drop" in opt:
            dropNotes = []
            if isInt(opt["drop"]):
                dropNotes = [opt["drop"]-1]
            else:
                dropNotes = [parseNumber(n.strip())-1 for n in opt["drop"].split(",")]
            for j, item in enumerate(newStep["groups"][key]["patterns"]):
                for noteIndex in dropNotes:
                    newStep["groups"][key]["patterns"][j]["notes"][noteIndex] = 0

        # volume adjustments
        if "volume" in opt:
            for j, item in enumerate(newStep["groups"][key]["patterns"]):
                newStep["groups"][key]["patterns"][j]["volume"] *= opt["volume"]

        # adjust speed of drums if necessary
        speed = 1
        if key == "drums":
            if "drumSpeed" in config and config["drumSpeed"] < 1:
                speed = config["drumSpeed"]
            if "speed" in opt and opt["speed"] < 1:
                speed = opt["speed"]
        if speed < 1:
            magnitude = int(1.0 / speed)
            if magnitude in set([2, 4, 8]) and index % magnitude == 0:
                basePatterns = newStep["groups"][key]["patterns"] # this is the pattern we are going to stretch into later measures
                newNotesPerMeasure = int(config["notesPerMeasure"] / magnitude)
                # create a set of stretched patterns based on basePattern
                for i in range(magnitude):
                    indexStart = int(i * newNotesPerMeasure)
                    newPatterns = []
                    for j, bp in enumerate(basePatterns):
                        newPattern = copy.deepcopy(bp)
                        newNotes = [0 for n in range(config["notesPerMeasure"])]
                        for k in range(newNotesPerMeasure):
                            newNotes[k*magnitude] = basePatterns[j]["notes"][indexStart+k]
                        newPattern["notes"] = newNotes
                        newPatterns.append(newPattern)
                    if key not in sequence[index+i]["groups"]:
                        sequence[index+i]["groups"][key] = {
                            "options": {},
                            "patterns": []
                        }
                    sequence[index+i]["groups"][key]["patterns"] = newPatterns
                newStep["groups"][key]["patterns"] = sequence[index]["groups"][key]["patterns"]

        # overlap notes from the previous step
        # if "overlap" in opt and index > 0 and key in sequence[index-1]["groups"]:
        #     prevGroup = sequence[index-1]["groups"][key]
        #     overlapAmount = opt["overlap"]
        #     # turn off notes from overlap in previous step group
        #     for j, item in enumerate(prevGroup["patterns"]):
        #         noteCount = len(item["notes"])
        #         for noteIndex, note in enumerate(item["notes"]):
        #             if noteIndex >= (noteCount - overlapAmount):
        #                 sequence[index-1]["groups"][key]["patterns"][j]["notes"][noteIndex] = 0
        #     # add current pattern to previous step
        #     for j, item in enumerate(group["patterns"]):
        #         copiedItem = copy.deepcopy(item)
        #         for noteIndex, note in enumerate(copiedItem["notes"]):
        #             if noteIndex < overlapAmount:
        #                 copiedItem["notes"][noteIndex] = 0
        #         sequence[index-1]["groups"][key]["patterns"].append(copiedItem)

    return newStep

def loadBassPatterns(config):
    _, bassPatterns = readCsv(config["bassPatternsFile"])
    if "bassPatternsQuery" in config:
        bassPatterns = filterByQueryString(bassPatterns, config["bassPatternsQuery"])
    bassPatternCount = len(bassPatterns)
    print("%s bass patterns after filtering" % bassPatternCount)

    # parse notes
    parsedPatterns = []
    for i, item in enumerate(bassPatterns):
        instrumentLookup = {}
        notes = [item["s"+str(j+1)] for j in range(config["notesPerMeasure"])]
        for j, note in enumerate(notes):
            if len(note) < 1:
                continue
            instruments = [note]
            if "," in note:
                instruments = note.split(",")
            for instrument in instruments:
                if instrument in instrumentLookup:
                    instrumentLookup[instrument]["notes"][j] = 1
                else:
                    instrumentNotes = [0 for n in range(config["notesPerMeasure"])]
                    instrumentNotes[j] = 1
                    instrumentLookup[instrument] = {
                        "id": item["id"],
                        "type": "bass",
                        "filename": config["bassAudioDir"] % instrument,
                        "notes": instrumentNotes,
                        "volume": config["bassVolume"],
                        "start": 0,
                        "dur": 0
                    }
        parsedPatterns += [instrumentLookup[key] for key in instrumentLookup]

    # adjust note durations
    for i, item in enumerate(parsedPatterns):
        count = 1
        notes = item["notes"]
        for j in range(config["notesPerMeasure"]):
            index = config["notesPerMeasure"]-j-1
            if notes[index] > 0:
                parsedPatterns[i]["notes"][index] = count
                count = 1
            else:
                count += 1

    return parsedPatterns

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
                    item = copy.deepcopy(instrument)
                    item["id"] = dp["id"]
                    item["category"] = item["instrument"]
                    item["type"] = "drum"
                    item["notes"] = notes
                    item["volume"] = config["drumsVolume"]
                    itemLookup[fn] = item
        drumPatternsN += [itemLookup[key] for key in itemLookup]

    return drumPatternsN

def loadSamplePatterns(config):
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
        if "nstretch" in s and s["nstretch"] != "":
            samplePatterns[i]["tempo"] = s["nstretch"]

    return samplePatterns

def loadSampleSequence(config):
    # load sample patterns
    samplePatterns = loadSamplePatterns(config)
    samplePatternsById = groupList(samplePatterns, "id")
    samplePatternLookup = createLookup(samplePatternsById, "id")

    # read drum patterns
    drumPatterns = loadDrumPatterns(config)
    drumPatternsById = groupList(drumPatterns, "id")
    drumPatternLookup = createLookup(drumPatternsById, "id")

    # read bass patterns
    # bassPatterns = loadBassPatterns(config)
    # bassPatternsById = groupList(bassPatterns, "id")
    # bassPatternLookup = createLookup(bassPatternsById, "id")

    sequence = loadSequenceFile(config)
    expandedSequence = []
    for i, step in enumerate(sequence):
        groups = {}
        if step["id"] != "" and step["id"] in samplePatternLookup:
            groups["samples"] = {
                "patterns": samplePatternLookup[step["id"]]["items"],
                "options": step["options"]
            }
        if step["drumId"] != "" and step["drumId"] in drumPatternLookup:
            groups["drums"] = {
                "patterns": drumPatternLookup[step["drumId"]]["items"],
                "options": step["drumOptions"]
            }
        # if step["bassId"] != "" and step["bassId"] in bassPatternLookup:
        #     groups["bass"] = {
        #         "patterns": bassPatternLookup[step["bassId"]]["items"],
        #         "options": step["bassOptions"]
        #     }
        step["groups"] = groups
        for j in range(step["count"]):
            expandedSequence.append(copy.deepcopy(step))

    # apply options
    for i in range(len(expandedSequence)):
        step = expandedSequence[i]
        step = applyStepOptions(step, i, expandedSequence, config)
        expandedSequence[i] = step

    # flatten groups
    flattenedSequence = []
    for step in expandedSequence:
        stepPatterns = []
        for key, group in step["groups"].items():
            stepPatterns += group["patterns"]
        copiedStep = copy.deepcopy(step)
        copiedStep["patterns"] = stepPatterns
        flattenedSequence.append(copiedStep)

    return flattenedSequence

def loadSequenceFile(config):
    _, sequence = readCsv(config["sequenceFile"])
    if "sequenceQuery" in config:
        sequence = filterByQueryString(sequence, config["sequenceQuery"])
    seqCount = len(sequence)
    print("%s sequence steps after filtering" % seqCount)

    for i, step in enumerate(sequence):
        sequence[i]["options"] = parseQueryString(step["options"], doParseNumbers=True) if step["options"] != "" else False
        sequence[i]["drumOptions"] = parseQueryString(step["drumOptions"], doParseNumbers=True) if "drumOptions" in step and step["drumOptions"] != "" else False
        sequence[i]["bassOptions"] = parseQueryString(step["bassOptions"], doParseNumbers=True) if "baseOptions" in step and step["bassOptions"] != "" else False

    return sequence
