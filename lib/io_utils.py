# -*- coding: utf-8 -*-

import csv
import os

def filterByQueryString(arr, queryString):
    return filterWhere(arr, parseQueryString(queryString))

def filterWhere(arr, filters):
    if isinstance(filters, tuple):
        filters = [filters]

    if len(arr) <= 0:
        return arr

    # Filter array
    for f in filters:
        key, value, mode = f
        if mode == "<=":
            arr = [a for a in arr if a[key] <= value]
        elif mode == ">=":
            arr = [a for a in arr if a[key] >= value]
        elif mode == "<":
            arr = [a for a in arr if a[key] < value]
        elif mode == ">":
            arr = [a for a in arr if a[key] > value]
        elif mode == "~=":
            arr = [a for a in arr if value in a[key]]
        else:
            arr = [a for a in arr if a[key] == value]

    return arr

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

def parseNumber(string):
    try:
        num = float(string)
        if "." not in string:
            num = int(string)
        return num
    except ValueError:
        return string

def parseNumbers(arr):
    for i, item in enumerate(arr):
        for key in item:
            arr[i][key] = parseNumber(item[key])
    return arr

def parseQueryString(str):
    conditionStrings = str.split("&")
    conditions = []
    modes = ["<=", ">=", "~=", ">", "<", "="]
    for cs in conditionStrings:
        for mode in modes:
            if mode in cs:
                parts = cs.split(mode)
                parts.append(mode)
                conditions.append(tuple(parts))
                break
    return conditions

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

def sortBy(arr, sorters):
    if isinstance(sorters, tuple):
        sorters = [sorters]

    if len(arr) <= 0:
        return arr

    # Sort array
    for key, direction in sorters:
        reversed = (direction == "desc")
        arr = sorted(arr, key=lambda k: k[key], reverse=reversed)

    return arr

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
