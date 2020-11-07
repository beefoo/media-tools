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

from lib.audio_utils import *
from lib.image_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="MANIFEST_FILE", default="path/to/ia_fedflixnara.txt", help="Input text file")
parser.add_argument('-fdir', dest="FRAMES_DIRECTORY", default="tmp/%s_frames/frame.*.png", help="Directory pattern for frames")
parser.add_argument('-afile', dest="AUDIO_FILE", default="output/ia_fedflixnara.mp4", help="Source audio file")
parser.add_argument('-out', dest="OUTPUT_DIR", default="output/ia_fedflixnara/dcp/", help="Media output directory")
parser.add_argument('-aout', dest="OUTPUT_AUDIO", default="audio_track.mp4", help="Audio output filename")
parser.add_argument('-fout', dest="OUTPUT_FRAMES", default="frame.%s.png", help="Frame output file pattern")
parser.add_argument('-fps', dest="FPS", default=24, type=int, help="Frame output file pattern")
parser.add_argument('-overwrite', dest="OVERWRITE", action="store_true", help="Overwrite existing?")
a = parser.parse_args()

FRAMES_OUT = a.OUTPUT_DIR + "frames/" + a.OUTPUT_FRAMES
AUDIO_OUT = a.OUTPUT_DIR + "audio/" + a.OUTPUT_AUDIO
makeDirectories([FRAMES_OUT, AUDIO_OUT])

manifestLines = []
if os.path.isfile(a.MANIFEST_FILE):
    with open(a.MANIFEST_FILE) as f:
        manifestLines = [l.strip() for l in f.readlines()]

if len(manifestLines) <= 0:
    print("Could not find instructions in %s" % a.MANIFEST_FILE)
    sys.exit()

# retrieve frame file names
framefiles = []
for i, line in enumerate(manifestLines):
    if line.startswith("file"):
        fn = line.split()[-1]
        fn = fn.strip("\"'")
        basename = getBasename(fn)
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


# convert audio file
print("Converting audio...")
if not os.path.isfile(AUDIO_OUT) or a.OVERWRITE:
    command = ['ffmpeg',
        '-y',
        '-i', a.AUDIO_FILE,
        '-c', 'copy',
        '-map', '0:a',
        AUDIO_OUT
    ]
    print(" ".join(command))
    finished = subprocess.check_call(command)

# remove existing files
if a.OVERWRITE:
    removeFiles(FRAMES_OUT % "*")

# copy frames over
frameCount = len(framefiles)
print("Copying %s frames..." % frameCount)
for i, srcName in enumerate(framefiles):
    destName = FRAMES_OUT % zeroPad(i+1, frameCount)
    if not os.path.isfile(destName) or a.OVERWRITE:
        shutil.copyfile(srcName, destName)
    printProgress(i+1, frameCount)

print("Audio duration: %s" % formatSeconds(getDurationFromAudioFile(AUDIO_OUT)/1000.0))
print("Video duration: %s" % formatSeconds(frameToMs(frameCount, a.FPS)/1000.0))
