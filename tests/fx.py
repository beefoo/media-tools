# -*- coding: utf-8 -*-

# python fx.py -pad 3000
# python fx.py -effect distortion -amounts "1,2,4,8,16,24,32,48" -out ../output/distortion_test.mp3
# python fx.py -effect lowpass -amounts "50,100,200,400,800,1600,3200,6400" -out ../output/lowpass_test.mp3
# python fx.py -effect bass -amounts " -20,-10,-5,5,10,20" -out ../output/bass_test.mp3
# python fx.py -effect echo -amounts "10,50,100,500,1000" -out ../output/echo_test.mp3

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
from lib import addFx

parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="../media/downloads/vivaldi/01_-_Vivaldi_Spring_mvt_1_Allegro.mp3", help="Input file")
parser.add_argument('-start', dest="CLIP_START", default=0, type=int, help="Clip start in ms")
parser.add_argument('-dur', dest="CLIP_DUR", default=3100, type=int, help="Clip duration in ms")
parser.add_argument('-effect', dest="EFFECT", default="reverb", help="Effect name")
parser.add_argument('-amounts', dest="AMOUNTS", default="20,40,60,80,100", help="Effect amounts")
parser.add_argument('-pad', dest="PAD", default=1000, type=int, help="Amount to pad in ms")
parser.add_argument('-out', dest="OUTPUT_FILE", default="../output/reverb_test.mp3", help="Output media file")
args = parser.parse_args()

# Parse arguments
filename = args.INPUT_FILE
clipStart = args.CLIP_START
clipDur = args.CLIP_DUR
effect = args.EFFECT
amounts = [float(amt) for amt in args.AMOUNTS.strip().split(",")]
pad = args.PAD
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

for amount in amounts:
    audio += addFx(clip, [(effect, amount)], pad=pad)
    print("Processed %s %s" % (effect, amount))

fformat = outputFile.split(".")[-1]
audio.export(outputFile, format=fformat)
print("Created %s" % outputFile)
