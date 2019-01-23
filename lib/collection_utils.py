from pprint import pprint
from lib.math_utils import *

def addIndices(arr, keyName="index"):
    for i, item in enumerate(arr):
        arr[i][keyName] = i
    return arr

def containsList(bucketList, needleList):
    return set(needleList).issubset(set(bucketList))

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
        value = parseNumber(value)
        if mode == "<=":
            arr = [a for a in arr if key not in a or a[key] <= value]
        elif mode == ">=":
            arr = [a for a in arr if key not in a or a[key] >= value]
        elif mode == "<":
            arr = [a for a in arr if key not in a or a[key] < value]
        elif mode == ">":
            arr = [a for a in arr if key not in a or a[key] > value]
        elif mode == "~=":
            arr = [a for a in arr if key not in a or value in a[key]]
        elif mode == "!=":
            arr = [a for a in arr if key not in a or a[key] != value]
        elif mode == "!~=":
            arr = [a for a in arr if key not in a or value not in a[key]]
        else:
            arr = [a for a in arr if key not in a or a[key] == value]

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

def parseSortString(str):
    conditionStrings = str.split("&")
    conditions = []
    for cs in conditionStrings:
        if "=" in cs:
            parts = cs.split("=")
            conditions.append(tuple(parts))
        else:
            conditions.append((cs, "asc"))
    return conditions

def prependAll(arr, prepends):
    if isinstance(prepends, tuple):
        prepends = [prepends]

    for i, item in enumerate(arr):
        for p in prepends:
            key, value = p
            arr[i][key] = value + item[key]

    return arr

def sortBy(arr, sorters):
    if isinstance(sorters, tuple):
        sorters = [sorters]

    if len(arr) <= 0:
        return arr

    # Sort array
    for s in sorters:
        trim = 1.0
        if len(s) > 2:
            key, direction, trim = s
            trim = float(trim)
        else:
            key, direction = s
        reversed = (direction == "desc")

        arr = sorted(arr, key=lambda k: k[key], reverse=reversed)

        if 0.0 < trim < 1.0:
            count = int(round(len(arr) * trim))
            arr = arr[:count]

    return arr

def sortByQueryString(arr, sortString):
    sorters = parseSortString(sortString)

    if len(sorters) <= 0:
        return arr

    return sortBy(arr, sorters)

def sortMatrix(arr, sortY, sortX, rowCount):
    count = len(arr)
    cols = ceilInt(1.0 * count / rowCount)
    arr = sortBy(arr, sortY)
    arrSorted = []
    for col in range(cols):
        i0 = col * rowCount
        i1 = min(i0 + rowCount, count)
        row = sortBy(arr[i0:i1], sortX)
        arrSorted += row
    return arrSorted

def updateAll(arr, updates):
    if isinstance(updates, tuple):
        updates = [updates]

    for i, item in enumerate(arr):
        for u in updates:
            key, value = u
            arr[i][key] = value

    return arr

def unionLists(arr1, arr2):
    if containsList(arr1, arr2):
        return arr1

    elif containsList(arr2, arr1):
        return arr2

    else:
        set1 = set(arr1)
        for v in arr2:
            if v not in set1:
                arr1.append(v)
        return arr1
