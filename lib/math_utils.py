# -*- coding: utf-8 -*-

import math
import numpy as np
import random
import scipy
from scipy import signal
import time
import sys

# return the bounding box of a rotated rectangle
def bboxRotate(cx, cy, w, h, angle):
    distanceToCorner = distance(cx, cy, cx-w*0.5, cy-h*0.5)
    tlX, tlY = translatePoint(cx, cy, distanceToCorner, 225+angle) # top left corner
    trX, trY = translatePoint(cx, cy, distanceToCorner, 315+angle) # top right corner
    brX, brY = translatePoint(cx, cy, distanceToCorner, 45+angle) # bottom right corner
    blX, blY = translatePoint(cx, cy, distanceToCorner, 135+angle) # bottom left corner
    xs = [tlX, trX, brX, blX]
    ys = [tlY, trY, brY, blY]
    minX = min(xs)
    minY = min(ys)
    maxX = max(xs)
    maxY = max(ys)
    return (minX, minY, maxX-minX, maxY-minY)

def ceilInt(n):
    return int(math.ceil(n))

def distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)

def easeIn(n):
    return (math.sin((n+1.5)*math.pi)+1.0) / 2.0

def easeInOut(n):
    return (math.sin((2.0*n+1.5)*math.pi)+1.0) / 2.0

def findNextValue(arr, value, isSorted=True):
    nvalue = None
    if not isSorted:
        arr.sort()
    for v in arr:
        if v > value:
            nvalue = v
            break
    return nvalue

def findPeaks(data, distance=None, height=None, findMinima=True):
    values = np.array(data)
    maxima, _ = signal.find_peaks(values, distance=distance, height=height)
    if findMinima:
        ivaluses = np.negative(values) # invert values to get minima
        minima, _ = signal.find_peaks(ivaluses, distance=distance, height=height)
    # import matplotlib.pyplot as plt
    # plt.plot(values, color="blue")
    # plt.plot(maxima, values[maxima], "x", color="green")
    # plt.plot(minima, values[minima], "x", color="red")
    # plt.show()
    if findMinima:
        return (list(minima), list(maxima))
    else:
        return list(maxima)

def floorInt(n):
    return int(math.floor(n))

def formatSeconds(s):
    return time.strftime('%H:%M:%S', time.gmtime(s))

def getRandomColor(seed=None):
    c = []
    for i in range(3):
        if seed is not None:
            random.seed(seed+i)
        c.append(random.randint(0, 255))
    return tuple(c)

def getValue(d, key, default):
    return d[key] if key in d else default

def isNumber(n):
    return isinstance(n, (int, float))

def lerp(ab, amount):
    a, b = ab
    return (b-a) * amount + a

def lim(value, ab=(0, 1)):
    a, b = ab
    return max(a, min(b, value))

def logTime(startTime=None, label="Elapsed time"):
    now = time.time()
    if startTime is not None:
        secondsElapsed = now - startTime
        timeStr = formatSeconds(secondsElapsed)
        print("%s: %s" % (label, timeStr))
    return now

def norm(value, ab, limit=False):
    a, b = ab
    n = 1.0 * (value - a) / (b - a)
    if limit:
        n = lim(n)
    return n

def parseFloat(string):
    return parseNumber(string, alwaysFloat=True)

def parseNumber(string, alwaysFloat=False):
    try:
        num = float(string)
        if "." not in str(string) and not alwaysFloat:
            num = int(string)
        return num
    except ValueError:
        return string

def parseNumbers(arr):
    for i, item in enumerate(arr):
        if isinstance(item, (list,)):
            for j, v in enumerate(item):
                arr[i][j] = parseNumber(v)
        else:
            for key in item:
                arr[i][key] = parseNumber(item[key])
    return arr

def printProgress(step, total):
    sys.stdout.write('\r')
    sys.stdout.write("%s%%" % round(1.0*step/total*100,2))
    sys.stdout.flush()

def pseudoRandom(seed, range=(0, 1), isInt=False):
    random.seed(seed)
    value = random.random()
    value = lerp(range, value)
    if isInt:
        value = roundInt(value)
    return value

def roundToNearest(n, nearest):
    return 1.0 * round(1.0*n/nearest) * nearest

def roundInt(n):
    return int(round(n))

def timecodeToMs(tc):
    hours, minutes, seconds = tuple([float(v) for v in tc.split(":")])
    seconds = seconds + minutes * 60 + hours * 3600
    return roundInt(seconds*1000)

# East = 0 degrees
def translatePoint(x, y, distance, angle):
    rad = math.radians(angle)
    x2 = x + distance * math.cos(rad)
    y2 = y + distance * math.sin(rad)
    return (x2, y2)

def unique(arr):
    return list(set(arr))

def weighted_mean(values, weights=None):
    count = len(values)
    if count <= 0:
        return 0
    if weights is None:
        weights = [w**2 for w in range(count, 0, -1)]
    return np.average(values, weights=weights)
