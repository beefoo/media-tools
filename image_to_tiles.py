# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import sys

import lib.deepzoom as dz
from lib.io_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/large.jpg", help="File for input")
parser.add_argument('-tsize', dest="TILE_SIZE", default=256, type=int, help="Tile size in pixels")
parser.add_argument('-tformat', dest="TILE_FORMAT", default="jpg", help="Tile image format")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/large_tiles.dzi", help="File for output")
a = parser.parse_args()

makeDirectories(a.OUTPUT_FILE)
creator = dz.ImageCreator(tile_size=a.TILE_SIZE, tile_format="jpg")
creator.create(a.INPUT_FILE, a.OUTPUT_FILE)
print("Done.")
