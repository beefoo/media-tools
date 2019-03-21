# -*- coding: utf-8 -*-

import csv
import glob
import json
from lib.collection_utils import *
from lib.math_utils import *
import os
from pprint import pprint
import re
import shutil
import sys

try:
    import requests
except ImportError:
    print("Warning: requests module not found, so can't make remote json requests")

try:
    reload(sys)
    sys.setdefaultencoding('utf8')
except:
    print("reload operation not supported, skipping...")

def downloadBinaryFile(url, filename, overwrite=False):
    if os.path.isfile(filename) and not overwrite:
        print("%s already exists." % filename)
        return True
    print("Downloading %s..." % url)
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    del response

def framesExist(filePattern, frameCount):
    padZeros = getZeroPadding(frameCount)
    exist = True
    for frame in range(frameCount):
        filename = filePattern % str(frame+1).zfill(padZeros)
        if not os.path.isfile(filename):
            exist = False
            break
    return exist

def getFileExt(fn):
    basename = os.path.basename(fn)
    return "." + basename.split(".")[-1]

def getFilenames(fileString):
    files = []
    if "*" in fileString:
        files = glob.glob(fileString)
    else:
        files = [fileString]
    fileCount = len(files)
    files = sorted(files)
    print("Found %s files" % fileCount)
    return files

def getFilesFromString(a):
    # Read files
    files = []
    fieldNames = []
    fromManifest = a.INPUT_FILE.endswith(".csv")
    if fromManifest:
        fieldNames, files = readCsv(a.INPUT_FILE)
    else:
        fieldNames = ["filename"]
        files = [{"filename": f} for f in getFilenames(a.INPUT_FILE)]
    fileCount = len(files)

    # Filter out files with no filename, duration, or audio
    if fromManifest:
        files = prependAll(files, ("filename", a.MEDIA_DIRECTORY))
    else:
        files = [{"filename": f} for f in files]

    return (fieldNames, files, fileCount)

def getFilesInDir(dirname):
    return [os.path.join(dirname, f) for f in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, f))]

def getJSONFromURL(url):
    print("Downloading %s" % url)
    r = requests.get(url)
    return r.json()

def getNestedValue(d, string):
    parts = string.split(".")
    value = None
    for p in parts:
        if p in d:
            value = d[p]
            d = value
    return value

def getZeroPadding(count):
    return len(str(count))

def makeDirectories(filenames):
    if not isinstance(filenames, list):
        filenames = [filenames]
    for filename in filenames:
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

def parseHeadings(arr, headings):
    newArr = []
    headingKeys = [key for key in headings]
    for i, item in enumerate(arr):
        newItem = {}
        for key in item:
            if key in headingKeys:
                newItem[headings[key]] = item[key]
        newArr.append(newItem)
    return newArr

def parseUnicode(arr):
    for i, item in enumerate(arr):
        if isinstance(item, (list,)):
            for j, value in enumerate(item):
                try:
                    if isinstance(value, basestring) and not isinstance(value, unicode):
                        arr[i][j] = unicode(value, "utf-8")
                except NameError:
                    pass
        else:
            for key in item:
                try:
                    value = item[key]
                    if isinstance(value, basestring) and not isinstance(value, unicode):
                        arr[i][key] = unicode(value, "utf-8")
                except NameError:
                    pass
    return arr

def readCsv(filename, headings=False, doParseNumbers=True, skipLines=0, encoding="utf8", readDict=True, verbose=True):
    rows = []
    fieldnames = []
    canEncode = supportsEncoding()
    if os.path.isfile(filename):
        lines = []
        f = open(filename, 'r', encoding=encoding) if canEncode else open(filename, 'r')
        lines = list(f)
        f.close()
        if skipLines > 0:
            lines = lines[skipLines:]
        if readDict:
            reader = csv.DictReader(lines, skipinitialspace=True)
            fieldnames = list(reader.fieldnames)
        else:
            reader = csv.reader(lines, skipinitialspace=True)
        rows = list(reader)
        if headings:
            rows = parseHeadings(rows, headings)
        if doParseNumbers:
            rows = parseNumbers(rows)
        if not canEncode and encoding=="utf8":
            rows = parseUnicode(rows)
        if verbose:
            print("Read %s rows from %s" % (len(rows), filename))
    return (fieldnames, rows)

def readJSON(filename):
    data = {}
    if os.path.isfile(filename):
        with open(filename) as f:
            data = json.load(f)
    return data

def removeFiles(listOrString):
    filenames = listOrString
    if not isinstance(listOrString, list) and "*" in listOrString:
        filenames = glob.glob(listOrString)
    elif not isinstance(listOrString, list):
        filenames = [listOrString]
    print("Removing %s files" % len(filenames))
    for fn in filenames:
        if os.path.isfile(fn):
            os.remove(fn)

def replaceWhitespace(string, replaceWith=" "):
    return re.sub('\s+', replaceWith, string).strip() if isinstance(string, str) else string

def supportsEncoding():
    return sys.version_info >= (3, 0)

def writeCsv(filename, arr, headings="auto", append=False, encoding="utf8"):
    if headings == "auto":
        headings = arr[0].keys()
    mode = 'w' if not append else 'a'
    canEncode = supportsEncoding()
    if not canEncode:
        mode += 'b'
    f = open(filename, mode, encoding=encoding, newline='') if canEncode else open(filename, mode)
    writer = csv.writer(f)
    if not append:
        writer.writerow(headings)
    for i, d in enumerate(arr):
        row = []
        for h in headings:
            value = ""
            if h in d:
                value = d[h]
            if isinstance(value, list):
                value = ",".join(value)
            if not canEncode and encoding=="utf8" and isinstance(value, str):
                value = value.encode("utf-8")
            row.append(value)
        writer.writerow(row)
    f.close()
    print("Wrote %s rows to %s" % (len(arr), filename))

def writeJSON(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)
        print("Wrote data to %s" % filename)

def zeroPad(value, total):
    padding = getZeroPadding(total)
    return str(value).zfill(padding)
