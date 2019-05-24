# -*- coding: utf-8 -*-

# Attempt to create a single frames directory and a single audio file from a manifest file
    # [basename].mp4 must match [basename].mp3 and [basename]_frames/
    # Will attempt to remove numbers in basename of frames, e.g. basename_01_somthing.mp4 -> basename_something_frames/
    # Assumes all frames are the same size/format and audio files are the same bitrate/samplerate etc

import argparse
import os
from pprint import pprint
import shutil
import subprocess
import sys

from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="MANIFEST_FILE", default="path/to/ia_fedflixnara.txt", help="Input text file")
parser.add_argument('-fdir', dest="FRAMES_DIRECTORY", default="tmp/%s_frames/frame.*.png", help="Directory pattern for frames")
parser.add_argument('-adir', dest="AUDIO_DIRECTORY", default="output/%s.mp3", help="Directory pattern for audio files")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/ia_fedflixnara/dcp/", help="Media output directory")
parser.add_argument('-aout', dest="OUTPUT_AUDIO", default="audio_track.mp3", help="Audio output filename")
parser.add_argument('-fout', dest="OUTPUT_FRAMES", default="frame.%s.png", help="Frame output file pattern")
parser.add_argument('-pyv', dest="PYTHON_NAME", default="python3", help="Name of python command")
a = parser.parse_args()

FRAMES_OUT = a.OUTPUT_DIR + "frames/"
AUDIO_OUT = a.OUTPUT_DIR + "audio/"
makeDirectories([FRAMES_OUT, AUDIO_OUT])

manifestLines = []
if os.path.isfile(a.MANIFEST_FILE):
    with open(a.MANIFEST_FILE) as f:
        manifestLines = [l.strip() for l in f.readlines()]

if len(manifestLines) <= 0:
    print("Could not find instructions in %s" % a.MANIFEST_FILE)
    sys.exit()

# retrieve media file names
audiofiles = []
framefiles = []
for i, line in enumerate(manifestLines):
    if line.startswith("file"):
        fn = line.split()[-1]
        fn = fn.strip("\"'")
        basename = getBasename(fn)
        audiofile = a.AUDIO_DIRECTORY % basename
        if not os.path.isfile(audiofile):
            print("Could not find %s" % audiofile)
            sys.exit()
        audiofiles.append(audiofile)
        # remove numbers from basename
        fbasename = "_".join([p for p in basename.split("_") if not isInt(p)])
        framefile = a.FRAMES_DIRECTORY % fbasename
        # print(audiofile)
        # print(framefile)
        # print("-")
        # continue
        lineframefiles = getFilenames(framefile)
        if len(lineframefiles) <= 0:
            print("No frames found in %s" % framefile)
            sys.exit()
        framefiles += lineframefiles

# Write to temporary file for combining audio files
audioManifestFile = a.OUTPUT_DIR + "audiofiles_manifest.txt"
with open(audioManifestFile, 'w') as f:
    for fn in audiofiles:
        basename = os.path.basename(fn)
        f.write("file '%s'\n" % basename)

# combine audio file
audioOutFile = a.OUTPUT_DIR + a.OUTPUT_AUDIO
command = [a.PYTHON_NAME, 'combine_media.py',
    '-in', audioManifestFile,
    '-dir', os.path.dirname(a.AUDIO_DIRECTORY) + "/",
    '-out', audioOutFile
]
print(" ".join(command))
finished = subprocess.check_call(command)

# copy frames over
frameCount = len(framefiles)
print("Copying %s frames..." % frameCount)
for i, srcName in enumerate(framefiles):
    destName = a.OUTPUT_DIR + a.OUTPUT_FRAMES % zeroPad(i+1, frameCount)
    shutil.copyfile(srcName, destName)
    printProgress(i+1, frameCount)
