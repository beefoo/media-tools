import numpy as np

def getGaps(items):
    seconds = np.zeros(24*3600, dtype=int)
    for item in items:
        seconds[item["start"]:item["end"]] = 1
    gapStart = gapEnd = None
    gaps = []
    for i, s in enumerate(seconds):
        if s < 1:
            if gapStart is None:
                gapStart = i
                gapEnd = i
            else:
                gapEnd = i
        elif s > 0 and gapEnd is not None:
            gapDur = gapEnd - gapStart
            if gapDur > 0:
                gaps.append((gapStart, gapEnd, gapDur))
            gapStart = gapEnd = None
    return gaps
