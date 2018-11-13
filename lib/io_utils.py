# -*- coding: utf-8 -*-

import csv
import glob
from math_utils import *
import os

def getFilenames(fileString):
    files = []
    if "*" in fileString:
        files = glob.glob(fileString)
    else:
        files = [fileString]
    fileCount = len(files)
    print("Found %s files" % fileCount)
    return files

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

def readCsv(filename, headings=False, doParseNumbers=True):
    rows = []
    fieldnames = []
    if os.path.isfile(filename):
        with open(filename, 'rb') as f:
            lines = [line for line in f if not line.startswith("#")]
            reader = csv.DictReader(lines, skipinitialspace=True)
            rows = list(reader)
            if headings:
                rows = parseHeadings(rows, headings)
            if doParseNumbers:
                rows = parseNumbers(rows)
            fieldnames = list(reader.fieldnames)
    return (fieldnames, rows)

def writeCsv(filename, arr, headings="auto"):
    if headings == "auto":
        headings = arr[0].keys()
    with open(filename, 'wb') as f:
        writer = csv.writer(f)
        writer.writerow(headings)
        for i, d in enumerate(arr):
            row = []
            for h in headings:
                row.append(d[h])
            writer.writerow(row)
    print("Wrote %s rows to %s" % (len(arr), filename))
