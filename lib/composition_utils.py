
from lib.math_utils import *
import math

def getDivisionIncrement(count):
    divisions = math.ceil(math.log(count, 2))
    increment = 1.0 / divisions / 2.0
    return increment

def getOffset(count, index):
    if count < 2 or index < 1:
        return 0

    divisions = math.ceil(math.log(count, 2))
    currentIndex = 0
    foundOffset = 0
    for i in range(divisions):
        add = 1
        offset = 0
        if i > 0:
            add = 2 ** (i-1)
            offset = 2 ** (-i)
        for j in range(add):
            offset += offset * 2 * j
            currentIndex += 1
            if index == currentIndex:
                foundOffset = offset
                break
        if foundOffset > 0:
            break
    return foundOffset

def limitAudioClips(samples, maxAudioClips, keyName, invert=False, keepFirst=64, multiplier=10000, easing="quartOut", seed=3):
    indicesToKeep = []
    shuffleSamples = samples[:]
    shuffleSampleCount = maxAudioClips
    if maxAudioClips > keepFirst:
        shuffleSampleCount -= keepFirst
        keepSamples = samples[:keepFirst]
        indicesToKeep = [s["index"] for s in keepSamples]
        shuffleSamples = shuffleSamples[keepFirst:]
    samplesToPlay = weightedShuffle(shuffleSamples, [ease((1.0 - s[keyName] if invert else s[keyName]) * multiplier, easing) for s in shuffleSamples], count=shuffleSampleCount, seed=seed)
    indicesToKeep = set(indicesToKeep + [s["index"] for s in samplesToPlay])
    for i, s in enumerate(samples):
        samples[i]["playAudio"] = (s["index"] in indicesToKeep)
    return samples
