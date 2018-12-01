# -*- coding: utf-8 -*-

import csv
import glob
import json
from math_utils import *
import os
from pprint import pprint
import requests
import sys

reload(sys)
sys.setdefaultencoding('utf8')

def framesExist(filePattern, frameCount):
    padZeros = getZeroPadding(frameCount)
    exist = True
    for frame in range(frameCount):
        filename = filePattern % str(frame+1).zfill(padZeros)
        if not os.path.isfile(filename):
            exist = False
            break
    return exist

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

def getJSONFromURL(url):
    print("Downloading %s" % url)
    r = requests.get(url)
    return r.json()

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
    for i, value in enumerate(arr):
        if isinstance(value, basestring) and not isinstance(value, unicode):
            arr[i] = unicode(value, "utf-8")
    return arr

def readCsv(filename, headings=False, doParseNumbers=True, skipLines=0, encoding="utf-8"):
    rows = []
    fieldnames = []
    if os.path.isfile(filename):
        with open(filename, 'rb') as f:
            lines = [line for line in f if not line.startswith("#")]
            if skipLines > 0:
                lines = lines[skipLines:]
            reader = csv.DictReader(lines, skipinitialspace=True)
            rows = list(reader)
            if headings:
                rows = parseHeadings(rows, headings)
            if doParseNumbers:
                rows = parseNumbers(rows)
            if encoding=="utf-8":
                rows = parseUnicode(rows)
            fieldnames = list(reader.fieldnames)
    return (fieldnames, rows)

def readJSON(filename):
    data = {}
    if os.path.isfile(filename):
        with open(filename) as f:
            data = json.load(f)
    return data

def writeCsv(filename, arr, headings="auto", append=False, encoding="utf-8"):
    if headings == "auto":
        headings = arr[0].keys()
    mode = 'wb' if not append else 'ab'
    with open(filename, mode) as f:
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
                if encoding and isinstance(value, basestring):
                    value = value.encode(encoding)
                row.append(value)
            writer.writerow(row)
    print("Wrote %s rows to %s" % (len(arr), filename))

def writeJSON(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)
        print("Wrote data to %s" % filename)

def zeroPad(value, total):
    padding = getZeroPadding(total)
    return str(value).zfill(padding)
