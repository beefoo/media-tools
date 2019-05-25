# -*- coding: utf-8 -*-

import argparse
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.audio.fx import volumex
import os
from pprint import pprint
import subprocess
import sys

from lib.collection_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="path/to/manifest.csv", help="Input csv instruction file")
parser.add_argument('-dir', dest="MEDIA_DIRECTORY", default="output/", help="Input markdown file")
parser.add_argument('-pad0', dest="PAD_START", default=1.0, type=float, help="Padding at start in s")
parser.add_argument('-pad1', dest="PAD_END", default=1.0, type=float, help="Padding at end in s")
parser.add_argument('-volume', dest="VOLUME", type=float, default=1.5, help="Adjust volume")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/trailer.mp4", help="Output media file")
parser.add_argument('-probe', dest="PROBE", action="store_true", help="Just view statistics")
a = parser.parse_args()
aa = vars(a)

fieldNames, instructions = readCsv(a.INPUT_FILE)
makeDirectories([a.OUTPUT_FILE])

if len(instructions) <= 0:
    print("No instructions in %s" % a.INPUT_FILE)
    sys.exit()

instructions = prependAll(instructions, ("filename", a.MEDIA_DIRECTORY))

instructions = instructions[:4]

# load videos
sequenceDur = 0
for i, step in enumerate(instructions):
    prev = False if i < 1 else instructions[i-1]

    # get duration from file
    if step["clip_dur"] < 0:
        instructions[i]["clip_dur"] = getDurationFromFile(step["filename"], accurate=True)
        step = instructions[i]

    # offset start if we are crossfading
    if step["crossfade"] > 0:
        instructions[i]["offset_start"] = -step["fade_in"]
        step = instructions[i]

    # inherit start from previous if not defined
    if step["clip_start"] < 0 and prev:
        instructions[i]["clip_start"] = prev["clip_start"] + prev["clip_dur"] + step["offset_start"]
        step = instructions[i]

    instructions[i]["start"] = a.PAD_START + sequenceDur + step["offset_start"]

    sequenceDur += step["offset_start"] + step["clip_dur"]

duration = a.PAD_START + sequenceDur + a.PAD_END
print("Total time: %s" % formatSeconds(duration))

# determine video properties from the first clip
testClip = VideoFileClip(instructions[0]["filename"])
width, height = testClip.size
fps = testClip.fps
# testClip = testClip.subclip(20, 6)
# testClip.reader.close()
# del testClip
print("Creating movie at %s x %s with %s fps" % (width, height, fps))

if a.PROBE:
    sys.exit()

clips = []
time = a.PAD_START
steps = len(instructions)
for i, step in enumerate(instructions):
    clip = VideoFileClip(step["filename"])
    vdur = clip.duration
    cstart = step["clip_start"]
    cdur = step["clip_dur"]
    if (cstart + cdur) > vdur:
        print("%s not long enough: %s > %s" % (step["filename"], (cstart + cdur), vdur))
        sys.exit()
    # make a clip if we are not taking the whole thing
    # print("%s, %s" % (step["clip_start"], step["clip_dur"]))
    if cstart > 0 or cdur < vdur:
        clip = clip.subclip(step["clip_start"], step["clip_start"]+step["clip_dur"])
    clip = clip.set_position((0, 0))
    clip = clip.set_start(step["start"])
    nextStep = False if i >= steps-1 else instructions[i+1]
    # cross fade in
    if step["crossfade"] > 0 and step["fade_in"] > 0:
        clip = clip.crossfadein(step["fade_in"])
    elif step["fade_in"] > 0:
        clip = clip.fadein(step["fade_in"])

    # cross fade out if next clip is cross fading in
    if nextStep and nextStep["crossfade"] > 0 and nextStep["fade_in"] > 0:
        clip = clip.crossfadeout(nextStep["fade_in"])
    elif step["fade_out"] > 0:
        clip = clip.fadeout(step["fade_out"])

    # fade in/out audio
    if step["fade_in"] > 0:
        clip = clip.audio_fadein(step["fade_in"])
    if step["fade_out"] > 0:
        clip = clip.audio_fadeout(step["fade_out"])

    clips.append(clip)
    printProgress(i+1, steps)

video = CompositeVideoClip(clips, size=(width, height))
video = video.set_duration(duration)
if a.VOLUME != 1.0:
    video = video.volumex(a.VOLUME)
video.write_videofile(a.OUTPUT_FILE)
print("Wrote %s to file" % a.OUTPUT_FILE)
