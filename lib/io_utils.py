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
    pass
    # print("reload operation not supported, skipping...")

def appendToBasename(fn, appendString):
    extLen = len(getFileExt(fn))
    i = len(fn) - extLen
    return fn[:i] + appendString + fn[i:]

def downloadBinaryFile(url, filename, overwrite=False):
    if os.path.isfile(filename) and not overwrite:
        print("%s already exists." % filename)
        return True
    print("Downloading %s..." % url)
    response = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    del response

def downloadFile(url, filename, headers={}, save=True, overwrite=False):
    contents = ""

    if os.path.isfile(filename) and not overwrite:
        print("%s already exists." % filename)
        with open(filename, "r", encoding="utf8", errors="replace") as f:
            contents = f.read()
        if len(contents) > 0:
            return contents

    print("Downloading %s to %s..." % (url, filename))
    r = requests.get(url)
    contents = r.text

    if save:
        with open(filename, "w", encoding="utf8", errors="replace") as f:
            f.write(contents)

    return contents

def framesExist(filePattern, frameCount):
    padZeros = getZeroPadding(frameCount)
    exist = True
    for frame in range(frameCount):
        filename = filePattern % str(frame+1).zfill(padZeros)
        if not os.path.isfile(filename):
            exist = False
            break
    return exist

def getBasename(fn):
    return os.path.splitext(os.path.basename(fn))[0]

def getFileExt(fn):
    basename = os.path.basename(fn)
    return "." + basename.split(".")[-1]

def getFilenames(fileString, verbose=True):
    files = []
    if "*" in fileString:
        files = glob.glob(fileString)
    else:
        files = [fileString]
    fileCount = len(files)
    files = sorted(files)
    if verbose:
        print("Found %s files" % fileCount)
    return files

def getFilesFromString(a, prependKey="filename"):
    aa = vars(a)
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

    if fromManifest and "MEDIA_DIRECTORY" in aa:
        files = prependAll(files, ("filename", a.MEDIA_DIRECTORY, prependKey))

    return (fieldNames, files, fileCount)

def getFilesInDir(dirname):
    return [os.path.join(dirname, f) for f in os.listdir(dirname) if os.path.isfile(os.path.join(dirname, f))]

def getFilesizeString(fn):
    str = 'Unknown'
    if os.path.isfile(fn):
        filesize = os.path.getsize(fn)
        if filesize < 1000:
            str = '%sb' % filesize
        elif filesize < 1000000:
            str = '%skb' % roundInt(filesize/1000.0)
        elif filesize < 10000000:
            str = '%smb' % roundInt(filesize/1000000.0)
        elif filesize < 1000000000:
            str = '%smb' % round(filesize/1000000.0, 1)
        elif filesize < 10000000000:
            str = '%sgb' % round(filesize/1000000000.0, 1)
        else:
            str = '%sgb' % round(filesize/1000000000.0, 2)
    return str

def getJSONFromURL(url):
    print("Downloading %s" % url)
    data = False
    try:
        r = requests.get(url)
        data = r.json()
    except json.decoder.JSONDecodeError:
        print("Decode error for %s" % url)
        # r = requests.get(url)
        # print(r.content)
        # sys.exit()
        data = False
    return data

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
        if len(dirname) > 0 and not os.path.exists(dirname):
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
        with open(filename, encoding="utf8") as f:
            data = json.load(f)
    return data

def removeDir(path):
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)

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

def replaceFileExtension(fn, newExt):
    extLen = len(getFileExt(fn))
    i = len(fn) - extLen
    return fn[:i] + newExt

def supportsEncoding():
    return sys.version_info >= (3, 0)

def stringToFilename(string):
    string = str(string)
    # normalize whitespace
    string = string.replace('-', ' ')
    string = string.replace('_', ' ')
    string = ' '.join(string.split())

    # Replace spaces with dashes
    string = re.sub('\s+', '-', string).strip()

    # Remove invalid characters
    string = re.sub('[^0-9a-zA-Z\-]', '', string)

    # Remove leading characters until we find a letter or number
    string = re.sub('^[^0-9a-zA-Z]+', '', string)

    return string

def writeCsv(filename, arr, headings="auto", append=False, encoding="utf8"):
    if headings == "auto":
        headings = arr[0].keys() if len(arr) > 0 and type(arr[0]) is dict else None
    mode = 'w' if not append else 'a'
    canEncode = supportsEncoding()
    if not canEncode:
        mode += 'b'
    f = open(filename, mode, encoding=encoding, newline='') if canEncode else open(filename, mode)
    writer = csv.writer(f)
    if not append and headings is not None:
        writer.writerow(headings)
    for i, d in enumerate(arr):
        row = []
        if headings is not None:
            for h in headings:
                value = ""
                if h in d:
                    value = d[h]
                if isinstance(value, list):
                    value = ",".join(value)
                if not canEncode and encoding=="utf8" and isinstance(value, str):
                    value = value.encode("utf-8")
                row.append(value)
        else:
            row = d
        writer.writerow(row)
    f.close()
    print("Wrote %s rows to %s" % (len(arr), filename))

def writeJSON(filename, data, verbose=True, pretty=False):
    with open(filename, 'w') as f:
        if pretty:
            json.dump(data, f, indent=4)
        else:
            json.dump(data, f)
        if verbose:
            print("Wrote data to %s" % filename)

def writeTextFile(filename, text):
    with open(filename, "w", encoding="utf8", errors="replace") as f:
        f.write(text)

def zeroPad(value, total):
    padding = getZeroPadding(total)
    return str(value).zfill(padding)

def zipDir(filename, path):
    shutil.make_archive(filename, 'zip', path)

def zipLists(rows, cols):
    zipped = []
    for row in rows:
        item = {}
        for j, col in enumerate(cols):
            if j >= len(row):
                print("Warning: not enough values in row")
                continue
            item[col] = row[j]
        zipped.append(item)
    return zipped
