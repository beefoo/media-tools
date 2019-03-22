# -*- coding: utf-8 -*-

import argparse
import inspect
import math
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.audio_mixer import *
from lib.audio_utils import *
from lib.cache_utils import *
from lib.clip import *
from lib.collection_utils import *
from lib.composition_utils import *
from lib.io_utils import *
from lib.math_utils import *
from lib.sampler import *
from lib.statistics_utils import *
from lib.video_utils import *

# input
parser = argparse.ArgumentParser()
addVideoArgs(parser)
parser.add_argument('-data', dest="WIND_DATA", default="data/wind/wnd10m.gdas.2004-01-01*.p.bz2", help="Wind data files")
parser.add_argument('-grid', dest="GRID", default="128x128", help="Size of grid")
parser.add_argument('-grid0', dest="START_GRID", default="64x64", help="Start size of grid")
parser.add_argument('-grid1', dest="END_GRID", default="128x128", help="End size of grid")
parser.add_argument('-volr', dest="VOLUME_RANGE", default="0.3,0.6", help="Volume range")
parser.add_argument('-dur', dest="DURATION_MS", default=60000, type=int, help="Target duration in seconds")
parser.add_argument('-windd', dest="WIND_DURATION_MS", default=6000, type=int, help="Wind duration in seconds")
parser.add_argument('-bounds', dest="DATA_BOUNDS", default="0.0,0.0,1.0,1.0", help="Bounds x,y,w,h as a percentage")
a = parser.parse_args()
parseVideoArgs(a)
aa = vars(a)
aa["DATA_BOUNDS"] = tuple([float(v) for v in a.DATA_BOUNDS.strip().split(",")])

# Get video data
startTime = logTime()
stepTime = startTime
samples, sampleCount, container, sampler, stepTime, cCol, cRow, gridW, gridH, startGridW, startGridH, endGridW, endGridH = initGridComposition(a, stepTime)

# set clip alpha to min by default
for i, s in enumerate(samples):
    samples[i]["alpha"] = a.ALPHA_RANGE[0]

clips = samplesToClips(samples)
stepTime = logTime(stepTime, "Samples to clips")

for i, clip in enumerate(clips):
    clip.vector.setParent(container.vector)

dataFiles = getFilenames(a.WIND_DATA)
windData = []
for fn in dataFiles:
    _, d =loadCacheFile(fn)
    windData.append(d)
stepTime = logTime(stepTime, "Read data files")
windDataCount = len(windData)
windData = np.array(windData)
print("Wind data shape = %s x %s x %s x %s" % windData.shape)

# windData /= np.max(np.abs(windData), axis=0)
print("Wind data shape = %s x %s x %s x %s" % windData.shape)
print("Wind range [%s, %s]" % (windData.min(), windData.max()))
stepTime = logTime(stepTime, "Normalize data")

# Write wind data to image
# u = windData[0][:,:,0]
# v = windData[0][:,:,1]
# mag = np.sqrt(u * u + v * v)
# mag /= np.max(mag, axis=0)
# mag = mag * 255.0
# pixels = mag.astype(np.uint8)
# from PIL import Image
# im = Image.fromarray(pixels, mode="L")
# im.save("output/wind_debug.png")

# plot data
# from matplotlib import pyplot as plt
# plt.hist(windData.reshape(-1), bins=100)
# plt.show()
# sys.exit()

ms = a.PAD_START + a.DURATION_MS + a.WIND_DURATION_MS

# sort frames
container.vector.sortFrames()

# custom clip to numpy array function to override default tweening logic
def clipToNpArrWind(clip, ms, containerW, containerH, precision, parent):
    customProps = None
    precisionMultiplier = int(10 ** precision)
    props = clip.toDict(ms, containerW, containerH, parent, customProps=customProps)

    return np.array([
        roundInt(props["x"] * precisionMultiplier),
        roundInt(props["y"] * precisionMultiplier),
        roundInt(props["width"] * precisionMultiplier),
        roundInt(props["height"] * precisionMultiplier),
        roundInt(props["alpha"] * precisionMultiplier),
        roundInt(props["tn"] * precisionMultiplier),
        roundInt(props["zindex"])
    ], dtype=np.int32)

processComposition(a, clips, ms, sampler, stepTime, startTime, customClipToArrFunction=clipToNpArrFalling)
