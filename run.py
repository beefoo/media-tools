# -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="audio/sample/bird.wav", help="Input file pattern")
parser.add_argument('-sort', dest="SORT_BY", default="tsne", help="What to sort by: tsne, hz, power")
parser.add_argument('-uid', dest="UID", default="sort_tsne", help="ID used for creating temporary and output files")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sort_tsne.mp3", help="ID used for creating temporary and output files")
parser.add_argument('-overwrite', dest="OVERWRITE", default="0", help="Overwrite existing data?")
args = parser.parse_args()

INPUT_FILES = args.INPUT_FILES
SORT_BY = args.SORT_BY
UID = args.UID
TMP_DIR = "tmp/"

# Create samples
samplePath = TMP_DIR + UID + "_samples.csv"
command = ['python', '-W', 'ignore', 'media_to_samples.py', '-in', INPUT_FILES, '-out', samplePath, '-overwrite', args.OVERWRITE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)

# Extract features out of samples
featurePath = TMP_DIR + UID + "_features.csv"
featureScript = "samples_to_tsne.py" if SORT_BY == "tsne" else "samples_to_features.py"
command = ['python', '-W', 'ignore', featureScript, '-in', samplePath, '-out', featurePath, '-overwrite', args.OVERWRITE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)

# Compile features into media file
dir = os.path.dirname(INPUT_FILES) + "/"
sortBy = "x" if SORT_BY == "tsne" else SORT_BY
command = ['python', '-W', 'ignore', "features_to_media.py", '-in', featurePath, '-dir', dir, '-sort', sortBy, '-out', args.OUTPUT_FILE]
print("------")
print(" ".join(command))
finished = subprocess.check_call(command)
