# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
import sys
import yaml

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/file.yml", help="Input yml file")
parser.add_argument('-props', dest="PROPS", default="", help="Comma-separated list of properties to output; leave empty for all")
parser.add_argument('-replace', dest="REPLACE_STRING", default="", help="Query string of keys to rename, e.g. keyFind=keyReplace&key2Find=key2Replace")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/yml.csv", help="Output csv file")
a = parser.parse_args()
# Parse arguments

props = [p for p in a.PROPS.strip().split(",")]

yamlData = False
with open(a.INPUT_FILE, 'r', encoding="utf8") as f:
    lines = f.read().splitlines()[1:-1]
    contents = "\n".join(lines)
    yamlData = yaml.load(contents, Loader=yaml.FullLoader)

if not yamlData:
    print("Could not load yml file: %s" % a.INPUT_FILE)
    sys.exit()

# Read files
fieldNames = list(yamlData.keys())
if len(props) < 1:
    props = fieldNames

replaceKeys = {}
if len(a.REPLACE_STRING) > 0:
    replaceKeys = parseQueryString(a.REPLACE_STRING, doParseNumbers=False)

item = {}
for p in props:
    pnew = p
    if p in replaceKeys:
        pnew = replaceKeys[p]
    item[pnew] = yamlData[p]
items = [item]

for i, p in enumerate(props):
    if p in replaceKeys:
        props[i] = replaceKeys[p]

makeDirectories(a.OUTPUT_FILE)
writeCsv(a.OUTPUT_FILE, items, headings=props)
