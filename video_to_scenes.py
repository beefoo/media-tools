# -*- coding: utf-8 -*-

# Looks for scenes in arbitrary video
# python -W ignore video_to_scenes.py -in media/sample/LivingSt1958.mp4 -overwrite 1 -threshold 24

import argparse
import csv
from lib import *
import os
import numpy as np
from pprint import pprint
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors.content_detector import ContentDetector

import sys

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILES", default="media/sample/moonlight.mp4", help="Input file pattern")
parser.add_argument('-out', dest="OUTPUT_FILE", default="tmp/scenes.csv", help="CSV output file")
parser.add_argument('-threshold', dest="THRESHOLD", default=30.0, type=float, help="Threshold for scene detection; lower number = more scenes")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", default=0, type=int, help="Draw plot?")
args = parser.parse_args()

# Parse arguments
INPUT_FILES = args.INPUT_FILES
OUTPUT_FILE = args.OUTPUT_FILE
THRESHOLD = args.THRESHOLD
OVERWRITE = args.OVERWRITE > 0
PLOT = args.PLOT > 0

# Check if file exists already
if os.path.isfile(OUTPUT_FILE) and not OVERWRITE:
    print("%s already exists. Skipping." % OUTPUT_FILE)
    sys.exit()

# Read files
files = getFilenames(INPUT_FILES)
fileCount = len(files)

# Make sure output dirs exist
makeDirectories(OUTPUT_FILE)

progress = 0

def getScenes(video_path, threshold=30.0, min_scene_len=15):
    global progress
    global fileCount

    basename = os.path.basename(video_path)

    # type: (str) -> List[Tuple[FrameTimecode, FrameTimecode]]
    video_manager = VideoManager([video_path])
    stats_manager = StatsManager()
    # Construct our SceneManager and pass it our StatsManager.
    scene_manager = SceneManager(stats_manager)

    # Add ContentDetector algorithm (each detector's constructor
    # takes detector options, e.g. threshold).
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    base_timecode = video_manager.get_base_timecode()

    # We save our stats file to {VIDEO_PATH}.stats.csv.
    stats_file_path = OUTPUT_FILE.replace(".csv", "%s.csv")
    stats_file_path = stats_file_path % ("_" + basename + "_stats")

    scene_list = []

    print("Looking for scenes in %s" % video_path)
    try:
        # If stats file exists, load it.
        if os.path.exists(stats_file_path):
            # Read stats from CSV file opened in read mode:
            with open(stats_file_path, 'r') as stats_file:
                stats_manager.load_from_csv(stats_file, base_timecode)

        # Set downscale factor to improve processing speed.
        video_manager.set_downscale_factor()

        # Start video_manager.
        video_manager.start()

        # Perform scene detection on video_manager.
        scene_manager.detect_scenes(frame_source=video_manager)

        # Obtain list of detected scenes.
        scenes = scene_manager.get_scene_list(base_timecode)
        # Each scene is a tuple of (start, end) FrameTimecodes.

        # We only write to the stats file if a save is required:
        if stats_manager.is_save_required():
            with open(stats_file_path, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)

        # Manually determine scenes from raw data (for greater control over thresholds)
        fieldNames, sceneData = readCsv(stats_file_path, skipLines=1)
        sceneIndex = 0
        start = 0
        dlen = len(sceneData)
        lastFrameScene = 0
        for i, d in enumerate(sceneData):
            if i > 0:
                ms = timecodeToMs(d["Timecode"])
                value = d["content_val"]
                frame = d["Frame Number"]
                prev = sceneData[i-1]["content_val"]
                delta = abs(value-prev)

                if (delta >= threshold or i >= dlen-1) and (frame-lastFrameScene+1) >= min_scene_len:
                    end = ms
                    scene_list.append({
                        "filename": basename,
                        "index": sceneIndex,
                        "start": start,
                        "dur": end - start
                    })
                    sceneIndex += 1
                    start = end
                    lastFrameScene = frame

    finally:
        video_manager.release()

    progress += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/fileCount*100,1))
    sys.stdout.flush()

    return scene_list

scenes = []
for fn in files:
    scenes += getScenes(fn, threshold=THRESHOLD)

headings = ["filename", "index", "start", "dur"]
writeCsv(OUTPUT_FILE, scenes, headings)
