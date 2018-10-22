# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from pprint import pprint
from pydub import AudioSegment
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)
from lib import stretchSound

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="../audio/downloads/vivaldi/01_-_Vivaldi_Spring_mvt_1_Allegro.mp3", help="Input file")
parser.add_argument('-start', dest="CLIP_START", default=0, type=int, help="Clip start in ms")
parser.add_argument('-dur', dest="CLIP_DUR", default=3100, type=int, help="Clip duration in ms")
parser.add_argument('-stretch', dest="STRETCH_AMOUNTS", default="1.5,2,4,8", help="Amounts to stretch (1 = no stretch)")
parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/stretch_test.mp3", help="Output media file")
args = parser.parse_args()

# Parse arguments
filename = args.INPUT_FILE
clipStart = args.CLIP_START
clipDur = args.CLIP_DUR
stretchAmounts = [float(amt) for amt in args.STRETCH_AMOUNTS.split(",")]
outputFile = args.OUTPUT_FILE

# Make sure output dir exist
outDir = os.path.dirname(outputFile)
if not os.path.exists(outDir):
    os.makedirs(outDir)

fformat = filename.split(".")[-1]
clip = AudioSegment.from_file(filename, format=fformat)
clip = clip[clipStart:(clipStart+clipDur)]
clip = clip.fade_out(min(100, clipDur))

audio = AudioSegment.empty()
audio.set_channels(clip.channels)
audio.set_sample_width(clip.sample_width)
audio.set_frame_rate(clip.frame_rate)
audio += clip

for amount in stretchAmounts:
    audio += stretchSound(clip, amount)
    print("Processed %sx" % amount)

fformat = outputFile.split(".")[-1]
audio.export(outputFile, format=fformat)
print("Created %s" % outputFile)
