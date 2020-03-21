# -*- coding: utf-8 -*-

# python3 projects/citizen_dj/instruments_to_csv.py -in "E:/Dropbox/citizen_dj/music_production/audio/instruments/**/*.mp3"

import argparse
import inspect
import glob
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
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/instruments/**/*.mp3", help="Path to instruments")
parser.add_argument('-out', dest="OUTPUT_FILE", default="projects/citizen_dj/data/instruments.csv", help="Output csv file")

a = parser.parse_args()
makeDirectories(a.OUTPUT_FILE)

filenames = glob.glob(a.INPUT_FILE, recursive=True)
notePattern = re.compile("([A-G]b?)([0-9])\.mp3")

rows = []
for fn in filenames:
    row = {}
    fn = fn.replace("\\","/")
    parts = fn.split("/")
    basename = parts[-1]
    row["filepath"] = parts[-3] + "/" + parts[-2] + "/" + parts[-1]
    row["instrument"] = parts[-2].replace("-mp3", "")
    row["source"] = parts[-3]

    matches = notePattern.match(basename)
    if not matches:
        print("Could not match %s" % fn)
        continue

    row["note"] = matches.group(1)
    row["octave"] = int(matches.group(2))

    rows.append(row)

writeCsv(a.OUTPUT_FILE, rows, ["filepath", "instrument", "source", "note", "octave"])
