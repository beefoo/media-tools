# -*- coding: utf-8 -*-

# python features_to_audio.py -in tmp/samples_features.csv -sort hz -out output/sort_hz.mp3

import argparse
import csv
from lib import *
import os
from moviepy.editor import VideoFileClip, concatenate_videoclips
import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="tmp/scenes.csv", help="Input file")
parser.add_argument('-dir', dest="VIDEO_DIRECTORY", default="media/sample/", help="Input file")
parser.add_argument('-sep', dest="SCENE_SEPARATOR", default="media/sample/SMPTE_bars_and_tone.mp4", help="Video file for padding")
parser.add_argument('-pad', dest="SCENE_PAD", default=500, type=int, help="Padding between scenes in milliseconds")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/scenes.mp4", help="Output media file")
args = parser.parse_args()

# Parse arguments
INPUT_FILE = args.INPUT_FILE
VIDEO_DIRECTORY = args.VIDEO_DIRECTORY
SCENE_SEPARATOR = args.SCENE_SEPARATOR
SCENE_PAD = args.SCENE_PAD
OUTPUT_FILE = args.OUTPUT_FILE

# get unique video files
fieldNames, rows = readCsv(INPUT_FILE)
filenames = list(set([f["filename"] for f in rows]))
videos = [{
        "filename": fn,
        "video": VideoFileClip(VIDEO_DIRECTORY + fn)
} for fn in filenames]

separator = False
if SCENE_PAD > 0:
    separator = VideoFileClip(SCENE_SEPARATOR).subclip(0, SCENE_PAD / 1000.0)

clips = []
for row in rows:
    video = [v["video"] for v in videos if v["filename"]==row["filename"]].pop(0)
    start = row["start"]/1000.0
    end = start + row["dur"]/1000.0
    clips.append(video.subclip(start, end))
    if separator:
        clips.append(separator)
combinedClips = concatenate_videoclips(clips)

print("Writing video...")
combinedClips.write_videofile(OUTPUT_FILE)
print("Wrote video to %s" % OUTPUT_FILE)
