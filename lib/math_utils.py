# -*- coding: utf-8 -*-

import math
import numpy as np

def lerp(ab, amount):
    a, b = ab
    return (b-a) * amount + a

def norm(value, ab):
    a, b = ab
    return 1.0 * (value - a) / (b - a)

def roundToNearest(n, nearest):
    return 1.0 * round(1.0*n/nearest) * nearest

def weighted_mean(values):
    count = len(values)
    if count <= 0:
        return 0
    weights = [w**2 for w in range(count, 0, -1)]
    return np.average(values, weights=weights)
