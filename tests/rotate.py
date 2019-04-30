# -*- coding: utf-8 -*-

import argparse
import inspect
import numpy as np
import os
from pprint import pprint
import sys

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.cache_utils import *
from lib.composition_utils import *
from lib.math_utils import *
from lib.video_utils import *

loaded, fileCacheData = loadCacheFile("tmp/rotate_test_cache/gov.archives.arc.96004_512kb.mp4.p")

pixelData = []
tn = 0.772
start = 844626
dur = 1425
end = start + dur * tn
ms = start
msStep = frameToMs(1, 30, False)
t = start
while ms < end:
    t = roundInt(ms)
    ms += msStep
index = fileCacheData[0].index(t)
pixelData = fileCacheData[1][index]
print("Pixel shape: %s x %s x %s" % pixelData.shape)
clipsPixelData = [[pixelData]]

im = Image.fromarray(pixelData, mode="RGB")
im.save("output/rotate_source_test.png")

clipArr = np.array([[783195, 480334,  56000,  29750,   1000,    772,   8125,     79, 0,    598]], dtype=np.int32)
im = clipsToFrameGPU(clipArr, 1920, 1080, clipsPixelData, precision=3, globalArgs={"colors": 4})
im = im.convert("RGB")
im.save("output/rotate_test.png")
print("Done")
