
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
        if mode == "!=":
            arr = [a for a in arr if a[key] != value]
        if mode == "!~=":
            arr = [a for a in arr if value not in a[key]]
        else:
            arr = [a for a in arr if a[key] == value]

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

def sortAndTrim(arr, sorters):
    if isinstance(sorters, tuple):
        sorters = [sorters]

    if len(arr) <= 0:
        return arr

    for s in sorters:
        key, direction, trim = s
        arr = sortBy(arr, (key, direction))
        count = int(round(len(arr) * trim))
        arr = arr[:count]

    return arr

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
