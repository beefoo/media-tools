# Reference: https://stackoverflow.com/questions/9619199/best-way-to-preserve-numpy-arrays-on-disk

import bz2
from lib.io_utils import *
from lib.math_utils import *
import os
import pickle

def addEntryToCacheArr(filename, arr, count, countPerFile, entryIndex, entryValue, autoSave=True):
    fileIndex = int(entryIndex / countPerFile)
    arrIndex = int(entryIndex % countPerFile)
    fileArr = arr[fileIndex]
    fileArr[arrIndex] = entryValue

    # check to see if we can save this file
    if autoSave:
        hasNone = [entry for entry in fileArr if entry is None]
        if len(hasNone) <= 0:
            fileCount = ceilInt(1.0 * count / countPerFile)
            fnPart = getCacheFilePartName(filename, fileCount, fileIndex)
            saveCacheFile(fnPart, fileArr)

    return arr


def getCacheFilePartName(fn, count, index):
    fileExt = getFileExt(fn)
    fileExtLen = len(fileExt)
    return fn[:-fileExtLen] + "." + zeroPad(index, count) + fileExt

def getEmptyCacheDataArr(count, countPerFile):
    arr = []
    fileCount = ceilInt(1.0 * count / countPerFile)
    for i in range(fileCount):
        arrCount = countPerFile if i < (fileCount-1) else int(count-(fileCount-1)*countPerFile)
        arr.append([None for j in range(arrCount)])
    return arr

def loadCacheFile(fn):
    loaded = False
    result = []
    fn += ".bz2"
    if fn and os.path.isfile(fn):
        print("Loading cache file %s..." % fn)
        with bz2.open(fn, "rb") as f:
            result = pickle.load(f)
            loaded = True
            print("Loaded cache file %s" % fn)
    return (loaded, result)

def loadCacheFiles(fn, count, countPerFile=1000):
    fileCount = ceilInt(1.0 * count / countPerFile)
    results = []
    loaded = True
    for i in range(fileCount):
        partFn = getCacheFilePartName(fn, fileCount, i)
        partLoaded, result = loadCacheFile(partFn)
        if not partLoaded:
            results = []
            loaded = False
            break
        results += result
    return (loaded, results)

def saveCacheFile(fn, data, overwrite=False):
    fn += ".bz2"
    if not os.path.isfile(fn) or overwrite:
        print("Saving cache file %s..." % fn)
        pickle.dump(data, bz2.open(fn, 'wb'))
    else:
        print("Already exists %s" % fn)
    return True
