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

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-pfile', dest="PATTERN_FILE", default="projects/citizen_dj/data/drum_patterns.csv", help="Input pattern csv file")
parser.add_argument('-pkfile', dest="PATTERN_KEY_FILE", default="projects/citizen_dj/data/drum_pattern_key.csv", help="Input pattern key csv file")
parser.add_argument('-sfile', dest="SAMPLE_FILE", default="projects/citizen_dj/data/drum_machines.csv", help="Input samples csv file")
parser.add_argument('-dir', dest="MEDIA_DIR", default="path/to/media/", help="Input collection csv file")
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

# group drumkits by drumkit name
rows = prependAll(rows, ("filename", a.MEDIA_DIR, "filepath"))
drumGroups = groupList(rows, "drumkit")

# group pattern key
patternKey = filterWhere(patternKey, ("active", 0, ">"))
patternKeyGroups = groupList(patternKey, "type")
patternKeyLookup = createLookup(patternKeyGroups, "type")
instrumentSymbols = sorted([i["symbol"] for i in patternKeyLookup["instrument"]["items"]], key=lambda s: -len(s))
styleSymbols = [i["symbol"] for i in patternKeyLookup["style"]["items"]]

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
            print(fname)
            modifiers.append({
                "source": baseInstrument,
                "modifiers": d["modifiers"],
                "filepath": fname
            })
    print("=====")

# print("Generating %s files" % len(modifiers))
# addRows = []
# for m in modifiers:
#     print(m["filepath"])

# writeCsv(OUTPUT_FILE, rows, headings=fieldNames)
