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

from lib.io_utils import *
from lib.math_utils import *

parser = argparse.ArgumentParser()
parser.add_argument('-max', dest="MAX_ITERATIONS", default=1000, type=int, help="Maximum times to iterate (otherwise will crash at some point)")
parser.add_argument('-mat', dest="MATRIX_D", default=1000, type=int, help="Dimension of the matrix to be squared")
a = parser.parse_args()

MATRIX_W = a.MATRIX_D
MATRIX_H = a.MATRIX_D
FILL_COLOR = (255,0,0)
MATRIX_C = len(FILL_COLOR)

# pprint(samples[0])

data = []
i = 0
while i < a.MAX_ITERATIONS:
    pixels = np.zeros((MATRIX_W, MATRIX_H, 1, MATRIX_C), dtype=np.uint8)
    pixels[:,:,:] = FILL_COLOR
    data.append(pixels)
    flatPixelData = np.array(data)
    dataGb = flatPixelData.nbytes / 1000000000.0
    i += 1
    sys.stdout.write('\r')
    sys.stdout.write("%s: %sGB" % (i, round(dataGb, 2)))
    sys.stdout.flush()

print("Done.")
