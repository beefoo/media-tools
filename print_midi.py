# -*- coding: utf-8 -*-

import argparse
import os
from pprint import pprint
import sys

from lib.midi_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/midi.md", help="Input file")
a = parser.parse_args()

printMidi(a.INPUT_FILE, verbose=True)