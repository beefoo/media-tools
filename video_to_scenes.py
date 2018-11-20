# -*- coding: utf-8 -*-

# Looks for scenes in arbitrary video
# python -W ignore video_to_scenes.py -in media/sample/LivingSt1958.mp4 -overwrite 1 -threshold 24 -fade 1 -plot 800
# python -W ignore video_to_scenes.py -in "media/downloads/ia_politicaladarchive/*.mp4" -threshold 24 -out "tmp/ia_politicaladarchive_scenes.csv"

import argparse
import csv
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *
import matplotlib.pyplot as plt
import numpy as np
import os
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
parser.add_argument('-min', dest="MIN_SCENE_DUR", default=500, type=int, help="Minimum scene duration in milliseconds")
parser.add_argument('-fade', dest="CHECK_FOR_FADE", default=0, type=int, help="Check for crossfades?")
parser.add_argument('-stats', dest="SAVE_STATS", default=0, type=int, help="Save statistics?")
parser.add_argument('-window', dest="WINDOW_SIZE", default=60, type=int, help="For fades, this is the window size in frames")
parser.add_argument('-fthreshold', dest="FADE_THRESHOLD", default=3.0, type=float, help="Threshold for crossfade detection; lower number = more scenes")
parser.add_argument('-overwrite', dest="OVERWRITE", default=0, type=int, help="Overwrite existing data?")
parser.add_argument('-plot', dest="PLOT", default="", help="Draw plot frames (e.g. 30:90)")
args = parser.parse_args()

# Parse arguments
INPUT_FILES = args.INPUT_FILES
OUTPUT_FILE = args.OUTPUT_FILE
THRESHOLD = args.THRESHOLD
MIN_SCENE_DUR = args.MIN_SCENE_DUR
CHECK_FOR_FADE = args.CHECK_FOR_FADE > 0
SAVE_STATS = args.SAVE_STATS > 0
WINDOW_SIZE = args.WINDOW_SIZE
FADE_THRESHOLD = args.FADE_THRESHOLD
OVERWRITE = args.OVERWRITE > 0
PLOT = args.PLOT.strip()

# Determine plot frames
if ":" in PLOT:
    PLOT = tuple([int(p) for p in PLOT.split(":")])
elif len(PLOT) > 0:
    PLOT = (0, int(PLOT))
else:
    PLOT = False

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

def getScenes(video_path, threshold=30.0, minSceneDur=500, windowSize=50, fadeThreshold=3.0):
    global progress
    global fileCount

    basename = os.path.basename(video_path)
    doStats = CHECK_FOR_FADE or PLOT or SAVE_STATS

    # type: (str) -> List[Tuple[FrameTimecode, FrameTimecode]]
    video_manager = VideoManager([video_path])
    stats_manager = StatsManager()
    # Construct our SceneManager and pass it our StatsManager.
    scene_manager = SceneManager(stats_manager)

    base_timecode = video_manager.get_base_timecode()
    framerate = video_manager.get_framerate()

    # Add ContentDetector algorithm (each detector's constructor
    # takes detector options, e.g. threshold).
    min_scene_len = roundInt(minSceneDur / 1000.0 * framerate)
    scene_manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))

    # We save our stats file to {VIDEO_PATH}.stats.csv.
    stats_file_path = OUTPUT_FILE.replace(".csv", "%s.csv")
    stats_file_path = stats_file_path % ("_" + basename + "_stats")

    scene_list = []

    print("Looking for scenes in %s" % video_path)
    try:
        # If stats file exists, load it.
        if doStats and os.path.exists(stats_file_path):
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

        for i, scene in enumerate(scenes):
            start = roundInt(scene[0].get_seconds()*1000)
            end = roundInt(scene[1].get_seconds()*1000)
            scene_list.append({
                "filename": basename,
                "index": i,
                "start": start,
                "end": end,
                "dur": end - start,
                "frameStart": scene[0].get_frames(),
                "frameEnd": scene[1].get_frames()
            })

        # We only write to the stats file if a save is required:
        if SAVE_STATS and stats_manager.is_save_required():
            with open(stats_file_path, 'w') as stats_file:
                stats_manager.save_to_csv(stats_file, base_timecode)

        # Retrieve raw data for plotting and additional analysis
        fieldNames, sceneData = readCsv(stats_file_path, skipLines=1)
        dlen = len(sceneData)

        # Add smoothed data
        windowLeft = int(windowSize/2)
        windowRight = windowSize - windowLeft
        for i, d in enumerate(sceneData):
            i0 = max(i - windowLeft, 0)
            i1 = min(i + windowRight, dlen-1)
            sceneData[i]["smoothed"] = np.mean([d["content_val"] for d in sceneData[i0:i1]])
            sceneData[i]["ms"] = timecodeToMs(d["Timecode"])

        # Add crossfade cuts
        if CHECK_FOR_FADE:
            for i, d in enumerate(sceneData):
                ms = d["ms"]
                value = d["smoothed"]
                frame = d["Frame Number"]
                neighboringCuts = [s for s in scene_list if abs(frame-s["frameStart"]) <= windowSize or abs(frame-s["frameEnd"]) <= windowSize]

                # if there's no nearby cuts and we've reached the fade threshold
                if len(neighboringCuts) <= 0 and value >= fadeThreshold:
                    # retrieve the scene right before this one
                    sortedList = sorted(scene_list, key=lambda k: k['frameStart'])
                    prev = [s for s in sortedList if s["frameStart"] < frame]
                    if len(prev) > 0:
                        prev = prev[-1]
                    else:
                        prev = sortedList[0]

                    # Find local minimums to determine fade start/end
                    leftWindow = sorted([d for d in sceneData if frame-windowSize < d["Frame Number"] < frame], key=lambda k: k['smoothed'])
                    rightWindow = sorted([d for d in sceneData if frame < d["Frame Number"] < frame+windowSize], key=lambda k: k['smoothed'])
                    fadeStart = leftWindow[0]
                    fadeEnd = rightWindow[0]

                    # Add new cut if we're not too close to the edges
                    if fadeStart["ms"]-prev["start"] >= minSceneDur and prev["end"] - fadeEnd["ms"] >= minSceneDur:
                        # Add the new scene
                        scene_list.append({
                            "filename": basename,
                            "index": prev["index"]+1,
                            "frameStart": fadeEnd["Frame Number"],
                            "frameEnd": prev["frameEnd"],
                            "start": fadeEnd["ms"],
                            "end": prev["end"],
                            "dur": prev["end"] - fadeEnd["ms"]
                        })

                        # Update the previous scene
                        scene_list[prev["index"]]["end"] = fadeStart["ms"]
                        scene_list[prev["index"]]["dur"] = fadeStart["ms"] - prev["start"]
                        scene_list[prev["index"]]["frameEnd"] = fadeStart["Frame Number"]

                        # Sort and update indices
                        scene_list = sorted(scene_list, key=lambda k: k['frameStart'])
                        for j, s in enumerate(scene_list):
                            scene_list[j]["index"] = j

        if PLOT:
            f0, f1 = PLOT
            # add raw data
            xs = [d["Frame Number"]-1 for d in sceneData if f0 <= d["Frame Number"] <= f1]
            ys = [d["content_val"] for d in sceneData if f0 <= d["Frame Number"] <= f1]
            plt.plot(xs, ys)

            # add smoothed data
            ys = [d["smoothed"] for d in sceneData if f0 <= d["Frame Number"] <= f1]
            plt.plot(xs, ys, "c")

            # add horizontal line for threshold
            plt.plot([xs[0], xs[-1]], [threshold, threshold], "g--")

            # add scenes as plot data
            xs = [d["frameEnd"]-1 for d in scene_list if f0 <= d["frameEnd"] <= f1]
            ys = [sceneData[d["frameEnd"]-1]["content_val"] for d in scene_list if f0 <= d["frameEnd"] <= f1]
            plt.scatter(xs, ys, c="red")
            plt.show()

    finally:
        video_manager.release()

    progress += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*progress/fileCount*100,1))
    sys.stdout.flush()

    return scene_list

scenes = []
for fn in files:
    scenes += getScenes(fn, threshold=THRESHOLD, minSceneDur=MIN_SCENE_DUR, windowSize=WINDOW_SIZE, fadeThreshold=FADE_THRESHOLD)

headings = ["filename", "index", "start", "dur"]
writeCsv(OUTPUT_FILE, scenes, headings)
