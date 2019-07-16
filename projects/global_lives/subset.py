# -*- coding: utf-8 -*-

import argparse
import inspect
import os
from pprint import pprint
import re
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
parser.add_argument('-in', dest="INPUT_FILE", default="projects/global_lives/data/ia_globallives_all.csv", help="Input video csv file")
parser.add_argument('-co', dest="COLLECTION_FILE", default="projects/global_lives/data/ia_globallives_collections.csv", help="Input collection csv file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="projects/global_lives/data/ia_globallives_subset.csv", help="Output video csv file")
a = parser.parse_args()

vFieldNames, videos = readCsv(a.INPUT_FILE)
cFieldNames, collections = readCsv(a.COLLECTION_FILE)
vFieldNames = unionLists(vFieldNames, ["start", "end"])
# cFieldNames = unionLists(cFieldNames, ["count"])
collectionLookup = createLookup(collections, "id")

videos = [v for v in videos if v["hh0"]!=""]
print("%s videos after filtering non-footage" % len(videos))

for i, v in enumerate(videos):
    cid = v["collection"].split(",")[0]
    vcollection = collectionLookup[cid]
    videos[i]["collection"] = cid
    videos[i]["active"] = vcollection["active"] > 0 and "life_story" not in v["filename"] and "behind_the_scene" not in v["filename"]
    videos[i]["start"] = roundInt(v["hh0"] * 3600 + v["mm0"] * 60 + v["ss0"])
    videos[i]["end"] = roundInt(v["hh1"] * 3600 + v["mm1"] * 60 + v["ss1"])

videos = [v for v in videos if v["active"]]
print("%s videos after filtering inactive" % len(videos))

# Intelligently remove duplicates
pattern = re.compile(".*([0-2]\d):?([0-5]\d):?([0-5]\d)[ \-_]+([0-2]\d):?([0-5]\d):?([0-5]\d).*")
pkeys = ["hh0","mm0","ss0","hh1","mm1","ss1"]
videos = addIndices(videos)
filenames = groupList(videos, "filename")
for f in filenames:
    fvideos = f["items"]
    if len(fvideos) > 1:
        for j, v in enumerate(fvideos):
            weight = 1
            matches = pattern.match(v["identifier"])
            if matches:
                for k, key in enumerate(pkeys):
                    val = int(matches.group(k+1))
                    if val != v[key]:
                        print("Mismatch id (%s) with filename (%s)" % (v["identifier"], f["filename"]))
                        weight = 0
                        break
            fvideos[j]["weight"] = weight
        fvideos = sorted(fvideos, key=lambda v: v["weight"], reverse=True)
        for j, v in enumerate(fvideos):
            if j > 0:
                videos[v["index"]]["active"] = False
videos = [v for v in videos if v["active"]]
print("%s videos after filtering duplicates" % len(videos))

writeCsv(a.OUTPUT_FILE, videos, headings=vFieldNames)
