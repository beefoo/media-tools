# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import os
from pprint import pprint
from pydub import AudioSegment
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.math_utils import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-in', dest="INPUT_FILE", default="media/downloads/ia_globallives/globallivesproject_Basak_Taner_2013_tur_Istanbul_TR-34-040000-042959.mp4", help="Input file")
parser.add_argument('-start', dest="CLIP_START", default="18:31", help="Clip start timecode")
parser.add_argument('-dur', dest="CLIP_DUR", default="0:10", help="Clip duration timecode")
parser.add_argument('-tdb', dest="TARGET_DB", default=-16, type=int, help="Target Db")
parser.add_argument('-volume', dest="VOLUME", default=0.667, type=float, help="Volume adjust")
a = parser.parse_args()

targetDb = a.TARGET_DB
audio = getAudio(a.INPUT_FILE)
clip = getAudioClip(audio, timecodeToMs(a.CLIP_START), timecodeToMs(a.CLIP_DUR))

deltaDb = targetDb - clip.dBFS
print("Delta: %s" % deltaDb)
clip = clip.apply_gain(deltaDb)
# clip = clip.apply_gain(6.0)
clip = clip.apply_gain(volumeToDb(a.VOLUME))
clip.export("output/matchDbTest.mp3", format="mp3")
print("Created matchDbTest.mp3")
