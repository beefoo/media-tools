# -*- coding: utf-8 -*-

import argparse
import inspect
import math
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image
from pprint import pprint
import random
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.math_utils import *
from lib.cache_utils import *
from lib.processing_utils import *

video = VideoFileClip("media/sample/LivingSt1958.mp4", audio=False)
videoDur = video.duration

data = []
count = 100
for i in range(count):
    t = max(1.0, 1.0 * i / (count-1) * 0.9 * videoDur)
    videoPixels = video.get_frame(t)
    im = Image.fromarray(videoPixels, mode="RGB")
    w, h = im.size
    scale = random.uniform(0.5, 2.0)
    w = roundInt(w * scale)
    h = roundInt(h * scale)
    im = im.resize((w, h))
    data.append(np.array(im))
    printProgress(i+1, count)
data = np.array(data)

video.reader.close()
del video

saveCacheFile("tmp/cacheTest.p", data)
loaded, loadedData = loadCacheFile("tmp/cacheTest.p")
print(type(loadedData))
print(len(loadedData))
