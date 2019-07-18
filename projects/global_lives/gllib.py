
import inspect
from moviepy.editor import VideoFileClip
import numpy as np
import os
from PIL import Image
from pprint import pprint
import sys

# add parent directory to sys path to import relative modules
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
parentdir = os.path.dirname(parentdir)
sys.path.insert(0,parentdir)

from lib.audio_utils import *
from lib.collection_utils import *
from lib.math_utils import *
from lib.processing_utils import *
from lib.video_utils import *

def addCellDataToCollections(collections, cellsPerCollection, cellFilename, updateData=False):
    cells = []
    cellFieldnames = []
    cellsByCollection = None
    cellDataLookup = None

    if not updateData:
        cellFieldnames, cells = readCsv(cellFilename)

    cellFieldnames = unionLists(cellFieldnames, ["collection", "col", "power"])

    if len(cells) > 1:
        cellsByCollection = groupList(cells, "collection")

    if cellsByCollection is not None and len(cellsByCollection) != len(collections):
        print("Collection size mismatch: resetting cell data")
        cellsByCollection = None

    if cellsByCollection is not None:
        cellDataLookup = createLookup(cellsByCollection, "collection")

    dataUpdated = False
    for i, c in enumerate(collections):
        cdata = None
        if cellDataLookup is not None:
            cdata = cellDataLookup[c["id"]]
            if len(cdata) != cellsPerCollection:
                cdata = None
            else:
                cdata = sorted(cdata, key=lambda cell: cell["col"])
        for j, cell in enumerate(c["cells"]):
            if updateData or cdata is None:
                cpower = getPowerFromSamples(cell["samples"])
                collections[i]["cells"][j]["power"] = cpower
                dataUpdated = True
            else:
                collections[i]["cells"][j]["power"] = cdata[j]["power"]
        collections[i]["cells"] = addNormalizedValues(collections[i]["cells"], "power", "npower")

    if updateData or dataUpdated:
        cellData = []
        for i, c in enumerate(collections):
            for j, cell in enumerate(c["cells"]):
                cellData.append({
                    "collection": c["id"],
                    "col": cell["col"],
                    "power": cell["power"]
                })
        writeCsv(cellFilename, cellData, cellFieldnames)

    return collections

def addCellsToCollections(collections, videos, cellsPerCollection):
    for i, c in enumerate(collections):
        cVideos = [v for v in videos if v["collection"] == c["id"]]
        cVideos = sorted(cVideos, key=lambda v: v["start"])
        cTotalDur = int(sum([v["duration"] for v in cVideos]))
        durPerCell = int(1.0 * cTotalDur / cellsPerCollection)
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
                    })
                    currentVideoIndex += 1
                    currentVideoOffset = 0
                    cellDur += durLeftInVideo
            if cellDur < durPerCell * 0.9:
                print("   Warning: Cell %s of %s is too small (%s)" % (j+1, cellsPerCollection, formatSeconds(cellDur)))
            for k, cs in enumerate(cellSamples):
                cellSamples[k]["row"] = c["row"]
                cellSamples[k]["col"] = j
            cCells.append({
                "row": c["row"],
                "col": j,
                "samples": cellSamples,
                "dur": sum([cs["dur"] for cs in cellSamples])
            })
        collections[i]["cells"] = cCells
    return collections

def collectionToImg(collections, filename, cellsPerCollection, imgH=1080, margin=1):
    cCount = len(collections)
    cellH = int(imgH / cCount)
    aspectRatio = 640.0 / 360.0
    cellW = roundInt(cellH * aspectRatio)
    imgW = cellW * cellsPerCollection
    im = Image.new(mode="RGB", size=(imgW, imgH), color=(0, 0, 0))

    # take the first sample in each cell
    clips = []
    for c in collections:
        for cell in c["cells"]:
            clips.append(cell["samples"][0])
    filenames = groupList(clips, "filename")
    filecount = len(filenames)
    for i, f in enumerate(filenames):
        video = VideoFileClip(f["filename"], audio=False)
        videoDur = video.duration
        fclips = f["items"]
        for fclip in fclips:
            t = fclip["start"] + fclip["dur"]/2
            clipImg = getVideoClipImage(video, videoDur, {"width": cellW-margin*2, "height": cellH-margin*2}, t)
            x = fclip["col"] * cellW + margin
            y = fclip["row"] * cellH + margin
            im.paste(clipImg, (x, y))
        video.reader.close()
        del video
        printProgress(i+1, filecount)
    im.save(filename)
    print("Saved %s" % filename)
