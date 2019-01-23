# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/sample/bird.wav", help="Input file pattern")
parser.add_argument('-sort', dest="SORT_BY", default="tsne=asc", help="What to sort by: tsne, hz, power, dur, clarity")
parser.add_argument('-uid', dest="UID", default="auto", help="ID used for creating temporary and output files")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/%s.mp3", help="ID used for creating temporary and output files")
parser.add_argument('-overwrite', dest="OVERWRITE", default="0", help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", default="0", help="Plot features?")
parser.add_argument('-steps', dest="STEPS", default=3, type=int, help="How many steps to complete (1-3)")
args = parser.parse_args()

INPUT_FILES = args.INPUT_FILES
SORT_BY = args.SORT_BY
UID = args.UID
OVERWRITE = args.OVERWRITE
OUTPUT_FILE = args.OUTPUT_FILE
PLOT = args.PLOT
STEPS = args.STEPS
TMP_DIR = "tmp/"

# name temporary files after the input file(s)
if UID == "auto":
    UID = os.path.splitext(os.path.basename(INPUT_FILES))[0]
    if "*" in UID:
        UID = os.path.split(os.path.dirname(INPUT_FILES))[-1]

# name the output file after the input file
if "%s" in OUTPUT_FILE:
    filename = UID + "_" + SORT_BY
    OUTPUT_FILE = OUTPUT_FILE % filename

# Create samples
samplePath = TMP_DIR + UID + "_samples.csv"
command = ['python', '-W', 'ignore', 'audio_to_samples.py', '-in', INPUT_FILES, '-out', samplePath, '-overwrite', OVERWRITE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)
if STEPS <= 1:
    sys.exit()

# Extract features out of samples
dir = os.path.dirname(INPUT_FILES) + "/"
featurePath = samplePath # simply append features to sample path
featureScript = "samples_to_tsne.py" if "tsne" in SORT_BY else "samples_to_features.py"
command = ['python', '-W', 'ignore', featureScript, '-in', samplePath, '-dir', dir, '-out', featurePath, '-plot', PLOT, '-overwrite', OVERWRITE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)
if STEPS <= 2:
    sys.exit()

# Compile features into media file
command = ['python', '-W', 'ignore', "features_to_audio.py", '-in', featurePath, '-dir', dir, '-sort', SORT_BY, '-out', OUTPUT_FILE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)
