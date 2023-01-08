# -*- coding: utf-8 -*-

import argparse
import inspect
import mido
import os
from pprint import pprint
import subprocess
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.io_utils import *
from lib.math_utils import *
from lib.midi_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="C:/Users/brian/Dropbox/djphonetic/mid/APS_Fill_The_Trap_2/*.mid", help="Input midi files")
parser.add_argument('-bpm', dest="BPM", default=120, type=int, help="Output BPM")
parser.add_argument('-out', dest="OUTPUT_FILE", default="C:/Users/brian/apps/dj-phonetic/public/mid/drums.mid", help="Midi output file")
a = parser.parse_args()

files = getFilenames(a.INPUT_FILES)
defaultTempo = mido.bpm2tempo(a.BPM)

mid = mido.MidiFile(type=2)
for fn in files:
    tracks = readMidiTracks(fn, newTempo=defaultTempo)
    for track in tracks:
        mid.tracks.append(track)
mid.save(a.OUTPUT_FILE)
print('Done. Created midi file with tracks:')
printMidi(a.OUTPUT_FILE, verbose=False)