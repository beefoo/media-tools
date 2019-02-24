# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.clip import *
from lib.io_utils import *
from lib.math_utils import *
from lib.sampler import *

# input
parser = argparse.ArgumentParser()
parser.add_argument('-base', dest="BASE_AUDIO_FILE", default="output/ia_fedflixnara_waves.mp3", help="Base audio file")
parser.add_argument('-out', dest="OUTPUT_FILE", default="output/sampler_test.mp3", help="Base audio file")
a = parser.parse_args()

GRID_W = 256
PAD_START = 1000
PAD_END = 1000
END_GRID_W = 6
WAVE_DUR = 8000
BEAT_DUR = 6000
REVERB = 80

baseClip = Clip({"filename": a.BASE_AUDIO_FILE})
durationMs = baseClip.dur + PAD_END
baseClip.queuePlay(0)

sampler = Sampler()

ms = PAD_START
cols = GRID_W
step = 0
while True:
    zoomSteps = max(1, roundInt(1.0 * cols ** 0.5)) # zoom more steps when we're zoomed out
    cols -= (zoomSteps * 2)
    lastStep = False
    if cols <= END_GRID_W:
        cols = END_GRID_W
        lastStep = True

    waveDur = WAVE_DUR
    halfBeatDur = roundInt(BEAT_DUR * 0.5)

    # play kick
    sampler.queuePlay(ms, "kick", index=step)

    ms += halfBeatDur

    # play snare
    sampler.queuePlay(ms, "snare", index=step)

    ms += halfBeatDur
    step += 1

    if lastStep:
        break

clips = [baseClip] + sampler.getClips()
audioSequence = clipsToSequence(clips)
mixAudio(audioSequence, durationMs, a.OUTPUT_FILE)
