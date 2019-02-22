# Reference: https://stackoverflow.com/questions/9619199/best-way-to-preserve-numpy-arrays-on-disk

import bz2
from lib.io_utils import *
from lib.math_utils import *
import os
import pickle

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

def saveCacheFile(fn, data, overwrite=False):
    fn += ".bz2"
    if not os.path.isfile(fn) or overwrite:
        print("Saving cache file %s..." % fn)
        pickle.dump(data, bz2.open(fn, 'wb'))
    else:
        print("Already exists %s" % fn)
    return True
