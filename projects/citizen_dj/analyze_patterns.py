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
