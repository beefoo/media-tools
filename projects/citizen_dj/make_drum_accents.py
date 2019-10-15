# -*- coding: utf-8 -*-

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
parser.add_argument('-pfile', dest="PATTERN_FILE", default="projects/citizen_dj/data/drum_patterns.csv", help="Input pattern csv file")
parser.add_argument('-pkfile', dest="PATTERN_KEY_FILE", default="projects/citizen_dj/data/drum_pattern_key.csv", help="Input pattern key csv file")
parser.add_argument('-sfile', dest="SAMPLE_FILE", default="projects/citizen_dj/data/drum_machines.csv", help="Input samples csv file")
parser.add_argument('-dir', dest="MEDIA_DIR", default="path/to/media/", help="Input collection csv file")
parser.add_argument('-mindb', dest="MIN_DB", default=-22, type=float, help="Target minimum decibels")
parser.add_argument('-maxdb', dest="MAX_DB", default=-6, type=float, help="Target maximum decibels")
parser.add_argument('-out', dest="OUTPUT_FILE", default="", help="Output samples csv file; leave blank if same as input file")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing media files?")
a = parser.parse_args()

OUTPUT_FILE = a.OUTPUT_FILE if len(a.OUTPUT_FILE) > 0 else a.SAMPLE_FILE

_, patterns = readCsv(a.PATTERN_FILE)
_, patternKey = readCsv(a.PATTERN_KEY_FILE)
fieldNames, rows = readCsv(a.SAMPLE_FILE)

if "auto" not in fieldNames:
    fieldNames.append("auto")
    for i, row in enumerate(rows):
        rows[i]["auto"] = 0

rows = addIndices(rows)

# group drumkits by drumkit name
rows = prependAll(rows, ("filename", a.MEDIA_DIR, "filepath"))
drumGroups = groupList(rows, "drumkit")

# group pattern key
patternKey = filterWhere(patternKey, ("active", 0, ">"))
patternKeyGroups = groupList(patternKey, "type")
patternKeyLookup = createLookup(patternKeyGroups, "type")
instrumentSymbols = sorted([i["symbol"] for i in patternKeyLookup["instrument"]["items"]], key=lambda s: -len(s))
styleSymbols = [i["symbol"] for i in patternKeyLookup["style"]["items"]]
styleLookup = createLookup(patternKeyLookup["style"]["items"], "symbol")

# retrieve all unique instruments
symbols = []
for r in patterns:
    for n in range(16):
        key = str(n+1)
        value = r[key]
        if len(value):
            symbols += value.split(",")
symbols = sorted(unique(symbols))
# pprint(symbols)
# sys.exit()

# remove any invalid symbols
validSymbols = []
for s in symbols:
    for ss in instrumentSymbols:
        if ss==s:
            validSymbols.append(ss)
            break
        elif s.startswith(ss):
            vs = ss
            mparts = s[len(ss):].split()
            for part in mparts:
                if part in styleSymbols:
                    vs += part
            validSymbols.append(vs)
            break
validSymbols = sorted(unique(validSymbols))
# pprint(validSymbols)
# sys.exit()

# prep which accents to generate
symbolAccentData = []
for s in validSymbols:
    for ss in instrumentSymbols:
        if ss != s and s.startswith(ss):
            mparts = s[len(ss):].split()
            mods = []
            for part in mparts:
                if part in styleSymbols:
                    mods.append(part)
            if len(mods) > 0:
                symbolAccentData.append({
                    "instrument": ss,
                    "symbol": s,
                    "modifiers": mods
                })
            break
# pprint(symbolAccentData)
# sys.exit()

modifiers = []
for drum in drumGroups:
    ditems = [i for i in drum["items"] if len(i["instrument"]) > 0]
    dgroups = groupList(ditems, "instrument")
    dlookup = {}
    for g in dgroups:
        gitems = sorted(g["items"], key=lambda item: item["priority"] if item["priority"] != "" else 9999)
        dlookup[g["instrument"]] = gitems[0]
    dsymbols = unique([i["instrument"] for i in ditems])
    for d in symbolAccentData:
        if d["instrument"] not in dlookup:
            print("%s not in %s" % (d["instrument"], drum["drumkit"]))
            continue
        baseInstrument = dlookup[d["instrument"]]
        fname = appendToBasename(baseInstrument["filepath"], "_"+d["symbol"])
        # check if we need to generate a new file
        if (d["symbol"] not in dsymbols or dlookup[d["symbol"]]["auto"] > 0) and (a.OVERWRITE or not os.path.isfile(fname)):
            # print(fname)
            updateIndex = -1
            if d["symbol"] in dsymbols and dlookup[d["symbol"]]["auto"] > 0:
                updateIndex = dlookup[d["symbol"]]["index"]
            modifiers.append({
                "instrument": d["symbol"],
                "source": baseInstrument,
                "modifiers": d["modifiers"],
                "filepath": fname,
                "updateIndex": updateIndex
            })
    # print("=====")

print("Generating %s files" % len(modifiers))
addRows = []
for m in modifiers:
    sourceAudio = getAudio(m["source"]["filepath"], verbose=False)
    destAudio = m["filepath"]
    updateIndex = m["updateIndex"]

    for mod in m["modifiers"]:
        if mod in styleLookup:
            style = styleLookup[mod]
            # adjusting volume
            if style["volume"] > 1 or style["volume"] < 1:
                targetDb = lim(sourceAudio.dBFS + volumeToDb(style["volume"]), (a.MIN_DB, a.MAX_DB))
                if targetDb > 0.0 or targetDb < 0.0:
                    sourceAudio = matchDb(sourceAudio, targetDb)

            # create multiples (e.g. buzz or triples)
            elif style["count"] > 1 and style["offset"] > 0:
                clipDur = m["source"]["dur"]
                offset = style["offset"]
                newDur = clipDur + offset * (style["count"] - 1)
                clipFadeOut = clipDur - offset
                instructions = []
                ms = 0
                for i in range(style["count"]):
                    n = 1.0 * i / (style["count"] - 1)
                    volume = lerp((style["volume_from"], style["volume_to"]), n)
                    fadeOut = 0
                    if n < 1.0 and clipFadeOut > 0.0:
                        fadeOut = clipFadeOut
                    instructions.append({
                        "ms": ms,
                        "start": 0,
                        "dur": clipDur,
                        "db": volumeToDb(volume),
                        "fadeOut": fadeOut
                    })
                    ms += offset
                segments = [{
                    "id": (0, clipDur),
                    "start": 0,
                    "dur": clipDur,
                    "audio": sourceAudio
                }]
                sourceAudio = makeTrack(newDur, instructions, segments)

            else:
                print("Warning: nothing to modify for %s" % mod)

        else:
            print("Error: %s modifier not found" % mod)

    format = destAudio.split(".")[-1]
    sourceAudio.export(destAudio, format=format)
    print("Created %s" % destAudio)
    # sys.exit()

    # get new duration and power
    dur = getDurationFromAudioFile(destAudio)
    features = getFeaturesFromSamples(destAudio, [{"start": 0, "dur": dur}])
    power = features[0]["power"]

    # add new row if necessary
    if updateIndex < 0:
        row = m["source"].copy()
        row["filename"] = os.path.basename(destAudio)
        row["dur"] = dur
        row["power"] = power
        row["instrument"] = m["instrument"]
        row["auto"] = 1
        rows.append(row)

    else:
        rows[updateIndex]["dur"] = dur
        rows[updateIndex]["power"] = power

    # print(m["filepath"])

writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
