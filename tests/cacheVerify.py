# -*- coding: utf-8 -*-

import argparse
import inspect
import math
from matplotlib import pyplot as plt
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from lib.cache_utils import *
from lib.clip import *
from lib.io_utils import *
from lib.math_utils import *
from lib.video_utils import *

# CACHE_FILE = "tmp/waves_cache/clip_cache.p"
# loaded, data = loadCacheFile(CACHE_FILE)
# plt.figure(figsize = (10,10))
# x = [d[0] for d in data]
# y = [d[1] for d in data]
# plt.scatter(x, y, s=4)
# plt.show()

# CACHE_FILE = "tmp/wavestest.p"
# loaded, data = loadCacheFile(CACHE_FILE)
# pprint(data[0])
# print(len(data[0]["framePixelData"]))
# sys.exit()

CACHE_FILE = "tmp/waves_cache/gov.epa.744-v99-001_512kb.mp4.p"
loaded, data = loadCacheFile(CACHE_FILE)

# index = data[0].index(899100)
# print(data[1][index].shape)
# sys.exit()

# plt.figure(figsize = (10,10))
# x = [d.shape[1] for d in data[1]]
# y = [d.shape[0] for d in data[1]]
# plt.scatter(x, y, s=4)
# plt.show()

sortedData = sorted(data[1], key=lambda k:k.shape[0])
largest = sortedData[-1]
im = Image.fromarray(largest, mode="RGB")
plt.imshow(np.asarray(im))
plt.show()
