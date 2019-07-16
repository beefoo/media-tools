
import inspect
import numpy as np
import os
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.math_utils import *

def addCellsToCollections(collections, videos, cellsPerCollection):
    for i, c in enumerate(collections):
        cVideos = [v for v in videos if v["collection"] == c["id"]]
        cVideos = sorted(cVideos, key=lambda v: v["start"])
        cTotalDur = sum([v["duration"] for v in cVideos])
        durPerCell = roundInt(1.0 * cTotalDur / cellsPerCollection)
        print("%s has %s duration per cell" % (c["name"], formatSeconds(durPerCell)))
        cCells = []
        currentVideoIndex = 0
        currentVideoOffset = 0
        for j in range(cellsPerCollection):
            cellSamples = []
            cellDur = 0
            while cellDur < durPerCell and currentVideoIndex < len(cVideos):
                currentVideo = cVideos[currentVideoIndex]
                durLeftInVideo = currentVideo["duration"] - currentVideoOffset
                # Not enough time left in current video
                if durLeftInVideo < 1:
                    currentVideoIndex += 1
                    currentVideoOffset = 0
                    currentVideo = cVideos[currentVideoIndex]
                    durLeftInVideo = currentVideo["duration"]
                durLeftInCell = durPerCell - cellDur
                # we can finish the cell with the current video
                if durLeftInVideo > durLeftInCell:
                    cellSamples.append({
                        "filename": currentVideo["filename"],
                        "start": roundInt(currentVideoOffset * 1000),
                        "dur": int(durLeftInCell * 1000),
                        "row": c["row"],
                        "col": j
                    })
                    currentVideoOffset += durLeftInCell
                    cellDur += durLeftInCell
                    break
                # otherwise, we need to add the rest of video and go to the next video
                else:
                    cellSamples.append({
                        "filename": currentVideo["filename"],
                        "start": roundInt(currentVideoOffset * 1000),
                        "dur": int(durLeftInVideo * 1000),
                        "row": c["row"],
                        "col": j
                    })
                    currentVideoIndex += 1
                    currentVideoOffset = 0
                    cellDur += durLeftInVideo
            if cellDur < durPerCell * 0.9:
                print("   Warning: Cell %s of %s is too small (%s)" % (j+1, cellsPerCollection, formatSeconds(cellDur)))
            cCells.append({
                "row": c["row"],
                "col": j,
                "samples": cellSamples,
                "dur": sum([cs["cellSamples"] for cs in cellSamples])
            })
        collections[i]["cells"] = cCells
    return collections
