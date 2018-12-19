# -*- coding: utf-8 -*-

import math
import numpy as np
import time

def ceilInt(n):
    return int(math.ceil(n))

def easeIn(n):
    return (math.sin((n+1.5)*math.pi)+1.0) / 2.0

def easeInOut(n):
    return (math.sin((2.0*n+1.5)*math.pi)+1.0) / 2.0

def floorInt(n):
    return int(math.floor(n))

def formatSeconds(s):
    return time.strftime('%H:%M:%S', time.gmtime(s))

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
        for key in item:
            arr[i][key] = parseNumber(item[key])
    return arr

def roundToNearest(n, nearest):
    return 1.0 * round(1.0*n/nearest) * nearest

def roundInt(n):
    return int(round(n))

def timecodeToMs(tc):
    hours, minutes, seconds = tuple([float(v) for v in tc.split(":")])
    seconds = seconds + minutes * 60 + hours * 3600
    return roundInt(seconds*1000)

def unique(arr):
    return list(set(arr))

def weighted_mean(values):
    count = len(values)
    if count <= 0:
        return 0
    weights = [w**2 for w in range(count, 0, -1)]
    return np.average(values, weights=weights)
