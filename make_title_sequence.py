# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import subprocess
import sys

from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="MANIFEST_FILE", default="path/to/titles_manifest.txt", help="Input text file")
parser.add_argument('-dir', dest="TITLES_DIR", default="titles/%s.md", help="Directory with titles")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/%s.mp4", help="Media output file pattern")
parser.add_argument('-pyv', dest="PYTHON_NAME", default="python3", help="Name of python command")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing frames?")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just spit out commands?")
a = parser.parse_args()

makeDirectories([a.OUTPUT_DIR])

manifestLines = []
if os.path.isfile(a.MANIFEST_FILE):
    with open(a.MANIFEST_FILE) as f:
        manifestLines = [l.strip() for l in f.readlines()]

if len(manifestLines) <= 0:
    print("Could not find instructions in %s" % a.MANIFEST_FILE)
    sys.exit()

# build commands
commands = []
for i, line in enumerate(manifestLines):
    command = [a.PYTHON_NAME]
    parts = line.split()
    basename = parts.pop(0)
    isCredits = basename.startswith("credits")
    script = "make_credits.py" if isCredits else "make_title.py"
    prepend = "" if isCredits else "title_"
    command.append(script)
    titleFile = a.TITLES_DIR % basename
    if not os.path.isfile(titleFile):
        print("Could not find title file: %s" % titleFile)
        sys.exit()
    command += [
        "-in", titleFile,
        "-out", a.OUTPUT_DIR % (prepend+basename)
    ]
    command += parts
    if isCredits:
        command += ["-rr", "2.0"]
    if a.OVERWRITE:
        command.append("-overwrite")
    commands.append(command)

for command in commands:
    printCommand(command)
    if not a.PROBE:
        finished = subprocess.check_call(command)

print("Done.")
