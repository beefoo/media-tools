# -*- coding: utf-8 -*-

import argparse
import os
from PIL import Image
from pprint import pprint
import sys

from lib.image_utils import *
from lib.io_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/*.jpg", help="Input file pattern; can be a single file or a glob string")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/segments/", help="Segment data output directory")
a = parser.parse_args()

# Read files
files = getFilenames(a.INPUT_FILE)
filecount = len(files)

# Make sure output dirs exist
makeDirectories(a.OUTPUT_DIR)

for i, fn in enumerate(files):
    basename = os.path.basename(fn)
    fnOut = a.OUTPUT_DIR + basename
    toEightBit(fn, fnOut)
    printProgress(i+1, filecount)
