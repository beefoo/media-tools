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
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/drum_patterns.json", help="Output json file")
a = parser.parse_args()

_, patterns = readCsv(a.PATTERN_FILE)
_, patternKey = readCsv(a.PATTERN_KEY_FILE)

patternKey = filterWhere(patternKey, ("active", 0, ">"))
patternKeyGroups = groupList(patternKey, "type")
patternKeyLookup = createLookup(patternKeyGroups, "type")
instrumentSymbols = sorted([i["symbol"] for i in patternKeyLookup["instrument"]["items"]], key=lambda s: -len(s))
instrumentLookup = createLookup(patternKeyLookup["instrument"]["items"], "symbol")
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

for i, r in enumerate(patterns):
    # patterns[i]["groupId"] = (r["artist"], r["title"], r["year"], r["category"])
     patterns[i]["groupId"] = (r["label"], r["category"])

groupMeta = sorted(unique([r["groupId"] for r in patterns]))
# pprint(groupMeta)
patternGroups = groupList(patterns, "groupId")

patternData = []
for group in patternGroups:
    index = groupMeta.index(group["groupId"])
    bars = sorted(group["items"], key=lambda g: g["bar"])
    barsData = []
    for b in bars:
        barData = []
        for n in range(16):
            key = str(n+1)
            value = b[key]
            instruments = []
            if len(value) > 0:
                for symbol in value.split(","):
                    if symbol in validSymbols:
                        instruments.append(symbol)
            barData.append(instruments)
        barsData.append(barData)
    row = list(groupMeta[index])
    row.append(bars[0]["bpm"])
    row.append(barsData)
    patternData.append(row)

patternKeyData = {}
for s in validSymbols:
    label = ""
    for ss in instrumentSymbols:
        if ss == s:
            label = instrumentLookup[s]["name"]
            break
        elif ss != s and s.startswith(ss):
            label = instrumentLookup[ss]["name"]
            mparts = s[len(ss):].split()
            styleStrings = []
            for part in mparts:
                if part in styleSymbols:
                    styleString = styleLookup[part]["name"]
                    styleStrings.append(styleString)
            if len(styleStrings) > 0:
                label += " (%s)" % ", ".join(styleStrings)
            break
    patternKeyData[s] = label
# pprint(patternKeyData)
# sys.exit()

jsonOut = {
    "patterns": patternData,
    "patternKey": patternKeyData,
    # "itemHeadings": ["artist", "title", "year", "category", "bpm", "bars"]
    "itemHeadings": ["label", "category", "bpm", "bars"]
}

makeDirectories(a.OUTPUT_FILE)
writeJSON(a.OUTPUT_FILE, jsonOut)
