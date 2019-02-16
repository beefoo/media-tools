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
            if index == currentIndex
                foundOffset = offset
                break
        if foundOffset > 0:
            break
    return foundOffset
