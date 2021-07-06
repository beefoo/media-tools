# -*- coding: utf-8 -*-

import argparse
import os
import sys

from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/*.bz2", help="Input files")
parser.add_argument('-out', dest="OUT_DIR", default="output/unzipped/", help="Output directory")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just output details?")
a = parser.parse_args()

# get files
filenames = getFilenames(a.INPUT_FILE)
makeDirectories([a.OUT_DIR])

for fn in filenames:
    unzipFile(fn)

print("Done.")
